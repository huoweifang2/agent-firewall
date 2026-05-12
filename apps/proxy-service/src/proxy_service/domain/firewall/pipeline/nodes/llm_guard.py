"""LLM Guard scanner node — runs 5 input scanners against user prompts.

Scanners:
- PromptInjection: injection / jailbreak attempts
- Toxicity: toxic, hateful, violent language
- Secrets: API keys, passwords, tokens
- BanSubstrings: dangerous substrings (system prompt markers)
- InvisibleText: zero-width Unicode characters

Scanners are lazy-initialized on first call (loads ML models ~500MB).
When policy thresholds change the scanners are rebuilt automatically
(hot-reload — no restart required).

Each scanner runs via ``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import re

import structlog

from proxy_service.domain.firewall.pipeline.nodes import timed_node
from proxy_service.domain.firewall.pipeline.state import PipelineState
from proxy_service.infrastructure.config import get_settings

logger = structlog.get_logger()

# ── Lazy-initialized scanner singleton with threshold tracking ────────

_scanners: list | None = None
_active_thresholds: tuple[float, float] | None = None

# Keys that affect scanner construction — trigger rebuild when changed.
_DEFAULT_INJECTION = 0.5
_DEFAULT_TOXICITY = 0.7


class _FallbackScanner:
    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold


class PromptInjection(_FallbackScanner):
    _PATTERNS = (
        r"\bignore\b.{0,80}\b(instructions?|rules?|policy|policies)\b",
        r"\b(disregard|override|bypass)\b.{0,80}\b(instructions?|rules?|policy|policies|safety)\b",
        r"\b(system|developer)\s+(prompt|message|instructions?)\b",
        r"\b(jailbreak|dan mode|developer mode|confused deputy)\b",
        r"\b(without restrictions|no restrictions|unfiltered|respond freely|safety filters? (disabled|off))\b",
        r"\b(read this backwards|decode this|decode and execute|follow the instruction|combine parts|combine steps)\b",
        r"\b(reveal|show|print|dump|leak)\b.{0,80}\b(password|secret|api key|token|credential|system prompt)\b",
        r"\badmin\b.{0,80}\b(override|bypass|emergency|access|password)\b",
        r"\bstore\b.{0,80}\b(memory|future conversations?)\b.{0,80}\b(admin|ignore|never verify)\b",
    )

    def scan(self, text: str) -> tuple[str, bool, float]:
        lowered = text.lower()
        matched = any(re.search(pattern, lowered, re.IGNORECASE | re.DOTALL) for pattern in self._PATTERNS)
        score = 0.9 if matched else 0.0
        return text, score < self._threshold, score


class Toxicity(_FallbackScanner):
    _KEYWORDS = ("kill", "harm", "hate", "violent", "weapon", "threat")

    def scan(self, text: str) -> tuple[str, bool, float]:
        matched = any(keyword in text.lower() for keyword in self._KEYWORDS)
        score = 0.8 if matched else 0.0
        return text, score < self._threshold, score


class Secrets(_FallbackScanner):
    _PATTERNS = (
        re.compile(r"sk_(live|test)_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}|SG\.[A-Za-z0-9_.-]{20,}", re.IGNORECASE),
        re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/_-]+", re.IGNORECASE),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
        re.compile(r'"type"\s*:\s*"service_account"|private_key', re.IGNORECASE),
        re.compile(
            r"(database password|jwt signing secret|api[_ -]?key|token|password|secret|ssn)\s*(=|:|is)\s*\S+",
            re.IGNORECASE,
        ),
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        re.compile(r"\bfingerprint hash:\s*[a-f0-9]{24,}\b", re.IGNORECASE),
    )

    def scan(self, text: str) -> tuple[str, bool, float]:
        matched = any(pattern.search(text) for pattern in self._PATTERNS)
        return text, not matched, 0.95 if matched else 0.0


class BanSubstrings(_FallbackScanner):
    def __init__(self, substrings: list[str], threshold: float = 0.5) -> None:
        super().__init__(threshold)
        self._substrings = tuple(s.lower() for s in substrings)

    def scan(self, text: str) -> tuple[str, bool, float]:
        matched = any(substring in text.lower() for substring in self._substrings)
        return text, not matched, 1.0 if matched else 0.0


class InvisibleText(_FallbackScanner):
    _INVISIBLE = ("\u200b", "\u200c", "\u200d", "\ufeff")

    def scan(self, text: str) -> tuple[str, bool, float]:
        matched = any(char in text for char in self._INVISIBLE)
        return text, not matched, 1.0 if matched else 0.0


def _extract_threshold_key(thresholds: dict) -> tuple[float, float]:
    """Return the threshold values that affect scanner construction."""
    return (
        float(thresholds.get("injection_threshold", _DEFAULT_INJECTION)),
        float(thresholds.get("toxicity_threshold", _DEFAULT_TOXICITY)),
    )


def _build_scanners(thresholds: dict) -> list:
    """Construct scanners with policy-driven thresholds."""
    try:
        from llm_guard.input_scanners import (
            BanSubstrings as LLMBanSubstrings,
        )
        from llm_guard.input_scanners import (
            InvisibleText as LLMInvisibleText,
        )
        from llm_guard.input_scanners import (
            PromptInjection as LLMPromptInjection,
        )
        from llm_guard.input_scanners import (
            Secrets as LLMSecrets,
        )
        from llm_guard.input_scanners import (
            Toxicity as LLMToxicity,
        )
        from llm_guard.input_scanners.prompt_injection import (
            MatchType as PIMatchType,
        )

        return [
            LLMPromptInjection(
                threshold=thresholds.get("injection_threshold", _DEFAULT_INJECTION),
                match_type=PIMatchType.FULL,
            ),
            LLMToxicity(threshold=thresholds.get("toxicity_threshold", _DEFAULT_TOXICITY)),
            LLMSecrets(),
            LLMBanSubstrings(
                substrings=["SYSTEM:", "```system", "<|im_start|>system"],
                match_type="str",
                case_sensitive=False,
            ),
            LLMInvisibleText(),
        ]
    except ModuleNotFoundError:
        logger.warning("llm_guard_unavailable", msg="Using local fallback scanners")

    return [
        PromptInjection(
            threshold=thresholds.get("injection_threshold", _DEFAULT_INJECTION),
        ),
        Toxicity(threshold=thresholds.get("toxicity_threshold", _DEFAULT_TOXICITY)),
        Secrets(),
        BanSubstrings(substrings=["SYSTEM:", "```system", "<|im_start|>system"]),
        InvisibleText(),
    ]


def get_scanners(thresholds: dict) -> list:
    """Return scanners, rebuilding when thresholds change (hot-reload).

    On first call: loads ML models (~35 s).
    On subsequent calls with same thresholds: instant (returns cached).
    On threshold change: rebuilds scanners (~2-3 s, models already in
    memory so only the scanner objects are recreated).
    """
    global _scanners, _active_thresholds  # noqa: PLW0603
    requested = _extract_threshold_key(thresholds)

    if _scanners is None:
        logger.info("llm_guard_init", msg="Loading LLM Guard scanners (first call)")
        _scanners = _build_scanners(thresholds)
        _active_thresholds = requested
        logger.info("llm_guard_ready", scanner_count=len(_scanners))
    elif requested != _active_thresholds:
        logger.info(
            "llm_guard_threshold_change",
            old=_active_thresholds,
            new=requested,
            msg="Rebuilding scanners with new thresholds",
        )
        _scanners = _build_scanners(thresholds)
        _active_thresholds = requested
        logger.info("llm_guard_rebuilt", scanner_count=len(_scanners))

    return _scanners


def reset_scanners() -> None:
    """Reset scanner singleton (for testing)."""
    global _scanners, _active_thresholds  # noqa: PLW0603
    _scanners = None
    _active_thresholds = None


# ── Node ──────────────────────────────────────────────────────────────


@timed_node("llm_guard")
async def llm_guard_node(state: PipelineState) -> PipelineState:
    """Run LLM Guard scanners against the user message.

    Each scanner is executed in a thread pool via ``asyncio.to_thread()``.
    Results are written to ``risk_flags`` (failed scanners) and
    ``scanner_results["llm_guard"]``.
    """
    settings = get_settings()

    # Global kill switch
    if not settings.enable_llm_guard:
        return state

    text = state.get("user_message", "")
    if not text:
        return state

    thresholds = state.get("policy_config", {}).get("thresholds", {})
    scanners = get_scanners(thresholds)

    results: dict[str, dict] = {}
    risk_flags: dict = {**state.get("risk_flags", {})}
    errors: list[str] = list(state.get("errors", []))
    timeout = settings.scanner_timeout

    for scanner in scanners:
        scanner_name = type(scanner).__name__
        try:
            sanitized, is_valid, score = await asyncio.wait_for(
                asyncio.to_thread(scanner.scan, text),
                timeout=timeout,
            )
            results[scanner_name] = {
                "is_valid": is_valid,
                "score": round(score, 4),
            }
            if not is_valid:
                flag_key = scanner_name.lower()
                risk_flags[flag_key] = round(score, 4)
                logger.warning(
                    "llm_guard_flag",
                    scanner=scanner_name,
                    score=round(score, 4),
                    request_id=state.get("request_id"),
                )
        except TimeoutError:
            results[scanner_name] = {"error": f"Timeout after {timeout}s"}
            errors.append(f"llm_guard.{scanner_name}: timeout after {timeout}s")
            logger.error("llm_guard_timeout", scanner=scanner_name, timeout=timeout)
        except Exception as exc:
            results[scanner_name] = {"error": str(exc)}
            errors.append(f"llm_guard.{scanner_name}: {exc}")
            logger.error("llm_guard_error", scanner=scanner_name, error_type=type(exc).__name__)

    return {
        **state,
        "risk_flags": risk_flags,
        "errors": errors,
        "scanner_results": {
            **state.get("scanner_results", {}),
            "llm_guard": results,
        },
    }
