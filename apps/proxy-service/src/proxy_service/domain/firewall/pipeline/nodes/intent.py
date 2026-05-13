"""IntentNode — keyword-based intent classifier with custom rule overlay."""

from __future__ import annotations

from proxy_service.application.services.denylist import DenylistHit, check_denylist
from proxy_service.domain.firewall.pipeline.nodes import timed_node
from proxy_service.domain.firewall.pipeline.nodes.intent_patterns import (
    AGENT_EXFILTRATION_PATTERNS,
    AGENT_ROLE_BYPASS_PATTERNS,
    AGENT_SOCIAL_ENGINEERING_PATTERNS,
    AGENT_TOOL_ABUSE_PATTERNS,
    CODE_PATTERNS,
    CONFUSED_DEPUTY_PATTERNS,
    CRESCENDO_PATTERNS,
    EXTRACTION_PATTERNS,
    GREETING_PATTERNS,
    HARMFUL_CONTENT_PATTERNS,
    JAILBREAK_PATTERNS,
    MISINFORMATION_PATTERNS,
    PII_REQUEST_PATTERNS,
    RAG_POISONING_PATTERNS,
    RESOURCE_EXHAUSTION_PATTERNS,
    SUPPLY_CHAIN_PATTERNS,
    TEMPLATE_INJECTION_PATTERNS,
    TOOL_PATTERNS,
    VIRTUAL_CONTEXT_PATTERNS,
)
from proxy_service.domain.firewall.pipeline.state import PipelineState


def classify_intent(text: str) -> tuple[str, float]:
    """Classify text into an intent category using keyword heuristics.

    Returns ``(intent, confidence)`` tuple.
    """
    if any(p in text for p in JAILBREAK_PATTERNS):
        return "jailbreak", 0.8
    if any(p in text for p in EXTRACTION_PATTERNS):
        return "system_prompt_extract", 0.7

    # Agent-specific intents (higher priority than generic code_gen / tool_call)
    if any(p in text for p in AGENT_ROLE_BYPASS_PATTERNS):
        return "role_bypass", 0.75
    if any(p in text for p in AGENT_TOOL_ABUSE_PATTERNS):
        return "tool_abuse", 0.7
    if any(p in text for p in AGENT_EXFILTRATION_PATTERNS):
        return "agent_exfiltration", 0.7
    if any(p in text for p in AGENT_SOCIAL_ENGINEERING_PATTERNS):
        return "social_engineering", 0.65

    # Content policy / safety intents
    if any(p in text for p in HARMFUL_CONTENT_PATTERNS):
        return "harmful_content", 0.8
    if any(p in text for p in MISINFORMATION_PATTERNS):
        return "misinformation", 0.75
    if any(p in text for p in TEMPLATE_INJECTION_PATTERNS):
        return "template_injection", 0.8

    # Operational risk intents
    if any(p in text for p in RESOURCE_EXHAUSTION_PATTERNS):
        return "resource_exhaustion", 0.7
    if any(p in text for p in SUPPLY_CHAIN_PATTERNS):
        return "supply_chain", 0.75
    if any(p in text for p in RAG_POISONING_PATTERNS):
        return "rag_poisoning", 0.7
    if any(p in text for p in PII_REQUEST_PATTERNS):
        return "pii_request", 0.7
    if any(p in text for p in CONFUSED_DEPUTY_PATTERNS):
        return "confused_deputy", 0.7
    if any(p in text for p in VIRTUAL_CONTEXT_PATTERNS):
        return "virtual_context", 0.7
    if any(p in text for p in CRESCENDO_PATTERNS):
        return "crescendo", 0.7

    if any(p in text for p in CODE_PATTERNS):
        return "code_gen", 0.6
    if any(p in text for p in TOOL_PATTERNS):
        return "tool_call", 0.5
    if any(p in text for p in GREETING_PATTERNS):
        return "chitchat", 0.9
    return "qa", 0.5


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def _denylist_hits_for_state(state: PipelineState) -> list[DenylistHit]:
    cached = state.get("denylist_hits")
    if isinstance(cached, list):
        return [hit for hit in cached if isinstance(hit, DenylistHit)]
    return await check_denylist(state.get("user_message", "").lower(), state.get("policy_name", "balanced"))


def _custom_intent_rules_from_hits(hits: list[DenylistHit]) -> list[DenylistHit]:
    """Return only intent:* rules that match the text, sorted by severity (critical first)."""
    intent_hits = [h for h in hits if h.category.startswith("intent:")]
    intent_hits.sort(key=lambda h: SEVERITY_ORDER.get(h.severity, 99))
    return intent_hits


async def check_custom_intent_rules(text: str, policy_name: str) -> list[DenylistHit]:
    """Return only matching intent:* rules for callers outside the pipeline."""
    return _custom_intent_rules_from_hits(await check_denylist(text, policy_name))


@timed_node("intent")
async def intent_node(state: PipelineState) -> PipelineState:
    """Classify user intent and flag suspicious intents in risk_flags."""
    text = state.get("user_message", "").lower()

    # 1. Hardcoded patterns (base layer — always runs)
    intent, confidence = classify_intent(text)

    # 2. Custom intent rules from DB (overlay — can override)
    denylist_hits = await _denylist_hits_for_state(state)
    custom_intent_hits = _custom_intent_rules_from_hits(denylist_hits)
    if custom_intent_hits:
        best = custom_intent_hits[0]  # highest severity first
        intent = best.category.removeprefix("intent:")
        confidence = 0.75  # custom-rule confidence

    risk_flags = {**state.get("risk_flags", {})}
    if intent in (
        "jailbreak",
        "system_prompt_extract",
        "extraction",
        "exfiltration",
        "role_bypass",
        "tool_abuse",
        "agent_exfiltration",
        "social_engineering",
        "harmful_content",
        "misinformation",
        "resource_exhaustion",
        "supply_chain",
        "rag_poisoning",
        "pii_request",
        "confused_deputy",
        "template_injection",
        "virtual_context",
        "crescendo",
    ):
        risk_flags["suspicious_intent"] = confidence

    return {
        **state,
        "intent": intent,
        "intent_confidence": confidence,
        "denylist_hits": denylist_hits,
        "risk_flags": risk_flags,
    }
