"""Compiled pattern catalogs used by agent runtime gates."""

from __future__ import annotations

import re

PRE_TOOL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\b",
        r"new\s+system\s+prompt",
        r"reveal\s+(your\s+)?(system\s+)?prompt",
        r"disregard\s+(all\s+)?(prior|previous|above)",
        r"override\s+(all\s+)?rules",
        r"act\s+as\s+(an?\s+)?unrestricted",
        r"do\s+anything\s+now",
        r"jailbreak",
        r"<\|im_start\|>",
        r"\[INST\]",
        r"<<SYS>>",
        r"###\s*(system|assistant)\s*:",
    ]
]

EXFILTRATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(list|show|get|dump|export)\s+(all|every)\s+(user|customer|record|data|secret|key|password)",
        r"(enumerate|extract|download)\s+.*\b(database|table|record)",
        r"bulk\s+(export|download|extract)",
        r"select\s+\*\s+from",
        r"(DROP|DELETE|TRUNCATE|ALTER)\s+(TABLE|DATABASE)",
    ]
]

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)"
            r"(?:\+?1[-.\s]?)?"
            r"(?:\(?\d{3}\)?[-.\s]?)"
            r"\d{3}[-.\s]?\d{4}"
            r"(?!\d)",
        ),
    ),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "CREDIT_CARD",
        re.compile(
            r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))"
            r"[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3,4}\b"
        ),
    ),
    (
        "IP_ADDRESS",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
    ),
    (
        "IBAN",
        re.compile(
            r"\b[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}"
            r"(?:\s?[\dA-Z]{4}){0,4}\s?[\dA-Z]{1,4}\b"
        ),
    ),
]

SECRETS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "API_KEY",
        re.compile(r"\b(?:sk|pk|api|key|token|secret|access)[_-][A-Za-z0-9]{16,}\b", re.IGNORECASE),
    ),
    ("AWS_KEY", re.compile(r"\b(?:AKIA|ABIA|ACCA)[A-Z0-9]{16}\b")),
    (
        "GENERIC_SECRET",
        re.compile(
            r"(?:password|passwd|pwd|secret|token|api_key|apikey|access_key|private_key)"
            r"\s*[:=]\s*['\"]?[^\s'\"]{8,}",
            re.IGNORECASE,
        ),
    ),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("CONNECTION_STRING", re.compile(r"(?:postgres|mysql|mongodb|redis|amqp)://[^\s\"']+", re.IGNORECASE)),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN\s(?:RSA\s)?PRIVATE\sKEY-----")),
]

POST_TOOL_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE)),
    ("role_switch", re.compile(r"you\s+are\s+now\b", re.IGNORECASE)),
    ("new_system_prompt", re.compile(r"new\s+system\s+prompt", re.IGNORECASE)),
    ("reveal_prompt", re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE)),
    ("disregard", re.compile(r"disregard\s+(all\s+)?(prior|previous|above)", re.IGNORECASE)),
    ("override_rules", re.compile(r"override\s+(all\s+)?rules", re.IGNORECASE)),
    ("act_as_unrestricted", re.compile(r"act\s+as\s+(an?\s+)?unrestricted", re.IGNORECASE)),
    ("do_anything_now", re.compile(r"do\s+anything\s+now", re.IGNORECASE)),
    ("jailbreak", re.compile(r"\bjailbreak\b", re.IGNORECASE)),
    ("special_token_im", re.compile(r"<\|im_start\|>")),
    ("special_token_inst", re.compile(r"\[INST\]")),
    ("special_token_sys", re.compile(r"<<SYS>>")),
    ("role_header", re.compile(r"###\s*(system|assistant)\s*:", re.IGNORECASE)),
    ("pretend_to_be", re.compile(r"pretend\s+to\s+be\b", re.IGNORECASE)),
    ("do_not_follow", re.compile(r"do\s+not\s+follow\s+(your\s+)?instructions", re.IGNORECASE)),
]
