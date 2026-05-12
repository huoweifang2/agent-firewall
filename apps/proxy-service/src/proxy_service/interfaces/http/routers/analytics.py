"""Analytics aggregation endpoints.

All endpoints query the ``requests`` table with a configurable lookback
window (``hours`` query parameter, default 24, range 1–720).
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from proxy_service.infrastructure.persistence.models.policy import Policy
from proxy_service.infrastructure.persistence.models.request import Request
from proxy_service.infrastructure.persistence.session import get_db
from proxy_service.interfaces.http.schemas.analytics import (
    AnalyticsSummary,
    IntentCount,
    PolicyStats,
    RiskFlagCount,
    TimelineBucket,
)

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cutoff(hours: float) -> datetime:
    """Return the UTC cutoff timestamp for *hours* ago."""
    return datetime.now(UTC) - timedelta(hours=hours)


BUCKET_MAP: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
}


def _auto_bucket_seconds(hours: float) -> int:
    """Pick a reasonable bucket size in seconds for a given lookback window."""
    if hours <= 0.25:  # ≤ 15 min  → 1-minute buckets
        return 60
    if hours <= 1:  # ≤ 1 h     → 2-minute buckets
        return 120
    if hours <= 6:  # ≤ 6 h     → 5-minute buckets
        return 300
    if hours <= 24:  # ≤ 24 h    → 15-minute buckets
        return 900
    if hours <= 72:  # ≤ 3 d     → 1-hour buckets
        return 3600
    if hours <= 336:  # ≤ 14 d    → 6-hour buckets
        return 21600
    return 86400  # else      → 1-day buckets


def _bucket_datetime(value: datetime, seconds: int) -> datetime:
    """Return an epoch-aligned bucket timestamp without dialect-specific SQL."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    epoch = int(value.timestamp())
    return datetime.fromtimestamp((epoch // seconds) * seconds, UTC)


def _is_truthy_flag(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "0.0", "false", "null"}
    return True


# ---------------------------------------------------------------------------
# 1. Summary KPIs
# ---------------------------------------------------------------------------


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_summary(
    hours: float = Query(24, ge=0.05, le=720),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    cutoff = _cutoff(hours)

    q = select(
        func.count().label("total"),
        func.count().filter(Request.decision == "BLOCK").label("blocked"),
        func.count().filter(Request.decision == "MODIFY").label("modified"),
        func.count().filter(Request.decision == "ALLOW").label("allowed"),
        func.coalesce(func.avg(Request.risk_score), 0).label("avg_risk"),
        func.coalesce(func.avg(Request.latency_ms), 0).label("avg_latency"),
    ).where(Request.created_at >= cutoff)
    row = (await db.execute(q)).one()

    total = row.total or 0

    # Top intent
    top_intent_q = (
        select(Request.intent, func.count().label("cnt"))
        .where(Request.created_at >= cutoff, Request.intent.isnot(None))
        .group_by(Request.intent)
        .order_by(func.count().desc())
        .limit(1)
    )
    top_row = (await db.execute(top_intent_q)).first()

    return AnalyticsSummary(
        total_requests=total,
        blocked=row.blocked or 0,
        modified=row.modified or 0,
        allowed=row.allowed or 0,
        block_rate=round((row.blocked or 0) / total, 4) if total else 0.0,
        avg_risk=round(float(row.avg_risk), 4),
        avg_latency_ms=round(float(row.avg_latency), 1),
        top_intent=top_row.intent if top_row else None,
    )


# ---------------------------------------------------------------------------
# 2. Timeline (zero-filled buckets)
# ---------------------------------------------------------------------------


@router.get("/analytics/timeline", response_model=list[TimelineBucket])
async def get_timeline(
    hours: float = Query(24, ge=0.05, le=720),
    bucket: str = Query("auto"),
    db: AsyncSession = Depends(get_db),
) -> list[TimelineBucket]:
    bucket_secs = BUCKET_MAP.get(bucket, _auto_bucket_seconds(hours))
    cutoff = _cutoff(hours)

    q = select(Request.created_at, Request.decision).where(Request.created_at >= cutoff)
    rows = (await db.execute(q)).all()

    buckets: dict[datetime, dict[str, int]] = {}
    for created_at, decision in rows:
        bucket_time = _bucket_datetime(created_at, bucket_secs)
        counts = buckets.setdefault(
            bucket_time,
            {"total": 0, "blocked": 0, "modified": 0, "allowed": 0},
        )
        counts["total"] += 1
        if decision == "BLOCK":
            counts["blocked"] += 1
        elif decision == "MODIFY":
            counts["modified"] += 1
        elif decision == "ALLOW":
            counts["allowed"] += 1

    return [
        TimelineBucket(
            time=bucket_time,
            total=counts["total"],
            blocked=counts["blocked"],
            modified=counts["modified"],
            allowed=counts["allowed"],
        )
        for bucket_time, counts in sorted(buckets.items())
    ]


# ---------------------------------------------------------------------------
# 3. By-policy breakdown
# ---------------------------------------------------------------------------


@router.get("/analytics/by-policy", response_model=list[PolicyStats])
async def get_by_policy(
    hours: float = Query(24, ge=0.05, le=720),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyStats]:
    cutoff = _cutoff(hours)

    q = (
        select(
            Request.policy_id,
            Policy.name.label("policy_name"),
            func.count().label("total"),
            func.count().filter(Request.decision == "BLOCK").label("blocked"),
            func.count().filter(Request.decision == "MODIFY").label("modified"),
            func.count().filter(Request.decision == "ALLOW").label("allowed"),
            func.coalesce(func.avg(Request.risk_score), 0).label("avg_risk"),
        )
        .join(Policy, Request.policy_id == Policy.id)
        .where(Request.created_at >= cutoff)
        .group_by(Request.policy_id, Policy.name)
        .order_by(func.count().desc())
    )

    rows = (await db.execute(q)).fetchall()

    return [
        PolicyStats(
            policy_id=r.policy_id,
            policy_name=r.policy_name,
            total=r.total,
            blocked=r.blocked,
            modified=r.modified,
            allowed=r.allowed,
            block_rate=round(r.blocked / r.total, 4) if r.total else 0.0,
            avg_risk=round(float(r.avg_risk), 4),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 4. Top risk flags
# ---------------------------------------------------------------------------


@router.get("/analytics/top-flags", response_model=list[RiskFlagCount])
async def get_top_flags(
    hours: float = Query(24, ge=0.05, le=720),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[RiskFlagCount]:
    cutoff = _cutoff(hours)

    # Count total requests for pct calculation
    total_q = select(func.count()).where(Request.created_at >= cutoff)
    total = (await db.execute(total_q)).scalar() or 1

    rows = (await db.execute(select(Request.risk_flags).where(Request.created_at >= cutoff))).scalars().all()
    flags: Counter[str] = Counter()
    for risk_flags in rows:
        if not isinstance(risk_flags, dict):
            continue
        flags.update(flag for flag, value in risk_flags.items() if _is_truthy_flag(value))

    return [
        RiskFlagCount(
            flag=flag,
            count=count,
            pct=round(count / total, 4),
        )
        for flag, count in flags.most_common(limit)
    ]


# ---------------------------------------------------------------------------
# 5. Intent distribution
# ---------------------------------------------------------------------------


@router.get("/analytics/intents", response_model=list[IntentCount])
async def get_intents(
    hours: float = Query(24, ge=0.05, le=720),
    db: AsyncSession = Depends(get_db),
) -> list[IntentCount]:
    cutoff = _cutoff(hours)

    total_q = select(func.count()).where(Request.created_at >= cutoff)
    total = (await db.execute(total_q)).scalar() or 1

    q = (
        select(Request.intent, func.count().label("cnt"))
        .where(Request.created_at >= cutoff, Request.intent.isnot(None))
        .group_by(Request.intent)
        .order_by(func.count().desc())
    )
    rows = (await db.execute(q)).fetchall()

    return [
        IntentCount(
            intent=r.intent,
            count=r.cnt,
            pct=round(r.cnt / total, 4),
        )
        for r in rows
    ]
