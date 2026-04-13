"""
Input / output security guardrails for underage (teen) learners.

Functions
---------
classify_and_sanitize_student_input  — blocks prompt injection & kid-unsafe input
validate_and_sanitize_model_output   — blocks secret leakage & kid-unsafe output
build_security_fallback              — safe student-facing error message
"""

import re

# ── Injection patterns ─────────────────────────────────────────────────────────
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+message", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now|\bdan\b", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(prompt|instructions)", re.IGNORECASE),
    re.compile(r"bypass\s+(safety|policy|guardrails)", re.IGNORECASE),
]

# ── Secret-leak patterns (output) ──────────────────────────────────────────────
UNSAFE_OUTPUT_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
]

# ── Kid-safety patterns ────────────────────────────────────────────────────────
KID_UNSAFE_INPUT_PATTERNS = [
    re.compile(r"\b(fuck|shit|bitch|asshole|bastard|damn)\b", re.IGNORECASE),
    re.compile(r"\b(sex|sexy|porn|nude|naked|blowjob|handjob|intercourse|fetish)\b", re.IGNORECASE),
    re.compile(r"\b(kill|suicide|self[- ]?harm|cut myself|hurt myself)\b", re.IGNORECASE),
    re.compile(r"\b(hate|racist|slur|nazi)\b", re.IGNORECASE),
]

KID_UNSAFE_OUTPUT_PATTERNS = [
    re.compile(r"\b(fuck|shit|bitch|asshole|bastard)\b", re.IGNORECASE),
    re.compile(r"\b(sex|porn|nude|naked|fetish|explicit)\b", re.IGNORECASE),
    re.compile(r"\b(kill yourself|self[- ]?harm|suicide)\b", re.IGNORECASE),
    re.compile(r"\b(hate|racist|slur)\b", re.IGNORECASE),
]

KID_SAFE_APPENDIX = """

KID SAFETY RULES — mandatory:
────────────────────────────
• Audience includes underage students. Keep language school-safe and PG.
• Do NOT include profanity, insults, sexual content, or graphic/violent wording.
• Do NOT provide harmful instructions (self-harm, hate, abuse, illegal wrongdoing).
• If a user asks unsafe content, refuse briefly and redirect to a safe coding-focused question.
• Keep tone supportive, respectful, and age-appropriate.
""".strip()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _normalize_text(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.replace("\x00", " ").replace("\r", "\n").strip()[:max_chars]


def build_security_fallback(reason: str) -> str:
    return (
        "🔍 **Mistake Type**: Safety Check Triggered\n"
        "💡 **Hint 1**: I could not safely process this request in its current form.\n"
        "🤔 **Guiding Question**: Can you rephrase your question only in terms of "
        "your code behavior and expected output?\n"
        "📚 **Curriculum Reference**: Please ask using class topics/functions only, "
        "and I will cite the matching reference passage.\n\n"
        f"(Reason: {reason})"
    )


# ── Public API ─────────────────────────────────────────────────────────────────
def classify_and_sanitize_student_input(student_code: str, question: str) -> dict:
    """
    Gate on student input.

    Returns
    -------
    dict with keys: allowed (bool), risk_level (str), reasons (list),
                    student_code (str), question (str)
    """
    clean_code     = _normalize_text(student_code, 12_000)
    clean_question = _normalize_text(question,      1_200)
    combined       = f"{clean_code}\n{clean_question}"

    reasons, hits = [], 0
    for pat in INJECTION_PATTERNS:
        if pat.search(combined):
            hits += 1
            reasons.append(f"Injection signal: {pat.pattern}")
    for pat in KID_UNSAFE_INPUT_PATTERNS:
        if pat.search(combined):
            hits += 2
            reasons.append(f"Kid-unsafe content: {pat.pattern}")

    return {
        "allowed":      hits < 2,
        "risk_level":   "high" if hits >= 2 else ("medium" if hits == 1 else "low"),
        "reasons":      reasons,
        "student_code": clean_code,
        "question":     clean_question,
    }


def validate_and_sanitize_model_output(response: str) -> dict:
    """
    Gate on LLM output.

    Returns
    -------
    dict with keys: safe (bool), issues (list[str]), response (str)
    """
    text   = _normalize_text(response, 8_000)
    issues = []

    for pat in UNSAFE_OUTPUT_PATTERNS:
        if pat.search(text):
            issues.append(f"Sensitive token pattern detected: {pat.pattern}")
    for pat in KID_UNSAFE_OUTPUT_PATTERNS:
        if pat.search(text):
            issues.append(f"Kid-unsafe output detected: {pat.pattern}")

    for marker in ["Mistake Type", "Hint", "Guiding Question", "Curriculum Reference"]:
        if marker.lower() not in text.lower():
            issues.append(f"Missing expected section: {marker}")

    if not re.search(r"\[\d+\]", text):
        issues.append("No context citation found (e.g., [1]).")

    return {"safe": len(issues) == 0, "issues": issues, "response": text}
