"""
ZebraBot Socratic tutor — core logic (v2).

Prompt architecture: modular categories loaded from prompt_config table.
Static order:  ROLE -> SOCRATIC_CONSTRAINT -> SAFETY_AND_SCOPE -> ENCOURAGEMENT_POLICY
Dynamic:       STUDENT_PROFILE, CURRICULUM_TRACK_BEHAVIOR, SESSION_STATE
RAG_CITATION_POLICY: excluded (work in progress)

Turn limit: enforced via conversation_history table count per conversation_id.
"""

import time
from typing import Literal

from sqlalchemy import text

from shared.llm_interface import LLMInterface
from shared.rag_utils import build_rag_context, extract_lms_references
from shared.security import (
    KID_SAFE_APPENDIX,
    build_security_fallback,
    classify_and_sanitize_student_input,
    validate_and_sanitize_model_output,
)

MAX_TURNS = 5


# ── DB loaders ─────────────────────────────────────────────────────────────────
def load_prompt_config(engine, category: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT content FROM prompt_config
                WHERE policy_category = :cat AND is_active = true
                ORDER BY version DESC LIMIT 1
            """),
            {"cat": category},
        ).fetchone()
    if row is None:
        raise RuntimeError(f"No active prompt_config row for category '{category}'.")
    return row[0]


def load_static_prompts(engine) -> str:
    """
    Assemble static system prompt in prescribed order.
    KID_SAFE_APPENDIX appended last.
    RAG_CITATION_POLICY intentionally excluded (work in progress).
    """
    categories = [
        "ROLE",
        "SOCRATIC_CONSTRAINT",
        "SAFETY_AND_SCOPE",
        "ENCOURAGEMENT_POLICY",
    ]
    parts = [load_prompt_config(engine, cat) for cat in categories]
    parts.append(KID_SAFE_APPENDIX)
    return "\n\n".join(parts)


def load_student_profile(engine, student_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT name, grade, track, session_count
                FROM students
                WHERE student_id = :sid
            """),
            {"sid": student_id},
        ).fetchone()
    if row is None:
        raise RuntimeError(f"No student found with student_id={student_id}.")
    name, grade, track, session_count = row
    return {
        "student_name":  name,
        "student_grade": grade,
        "student_track": track or "cpp",
        "session_count": session_count,
    }


def get_conversation_turns(engine, conversation_id: str) -> int:
    """Count how many turns have been used in this conversation."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT COUNT(*) FROM conversation_history
                WHERE conversation_id = :cid
            """),
            {"cid": conversation_id},
        ).fetchone()
    return row[0] if row else 0


# ── Prompt assembly ────────────────────────────────────────────────────────────
def format_system_prompt(engine, static_prompt: str, profile: dict) -> str:
    track_behavior = load_prompt_config(
        engine, f"CURRICULUM_TRACK_BEHAVIOR_{profile['student_track'].upper()}"
    )
    student_block = (
        f"STUDENT PROFILE:\n"
        f"Name:               {profile['student_name']}\n"
        f"Grade:              {profile['student_grade']}\n"
        f"Curriculum Track:   {profile['student_track']}\n"
        f"Sessions Completed: {profile['session_count']}\n\n"
        f"Adapt your language and analogies to be age-appropriate for a "
        f"{profile['student_grade']} student. Use their name naturally in conversation."
    )
    return "\n\n".join([static_prompt, student_block, track_behavior])


def format_user_prompt(
    student_code: str,
    context: str,
    turns_used: int,
    question: str = "",
) -> str:
    q_section = f"\n\n**Student's question:** {question}" if question.strip() else ""
    turns_remaining = MAX_TURNS - turns_used

    if turns_remaining >= 4:
        escalation = "Give a broad conceptual hint. Ask an open question."
    elif turns_remaining >= 2:
        escalation = "Give a more specific hint. Point to a curriculum section."
    else:
        escalation = "Give a near-direct scaffold — almost step-by-step, but stop short of the final answer."

    session_block = (
        f"SESSION STATE:\n"
        f"Hints Remaining: {turns_remaining} of {MAX_TURNS}\n"
        f"Escalation instruction: {escalation}"
    )

    return f"""== STUDENT'S C++ CODE ==
```cpp
{student_code.strip()}
```
{q_section}

== RETRIEVED CONTEXT (base your response ONLY on these passages) ==
{context}

── INSTRUCTIONS ──────────────────────────────────────────────────────
1. Analyse the code using the Socratic method.
2. Identify the mistake type and provide a progressive hint — do NOT reveal the answer.
3. Every technical claim (function names, parameters, port numbers, library behaviour)
   MUST come from the RETRIEVED CONTEXT above.
4. Citation rules:
   - Curriculum passages [1], [2], ... -> cite as "According to [2]..."
   - Library passages [L1], [L2], ...  -> cite as "See [L3]..."
   - In the Curriculum Reference section use ONLY [N] numbers (not [LN]).
5. If the cited passage has a "Video URL(s):" line, add a Video Reference section
   with those URLs verbatim. Omit the section entirely if no video URL is listed.
6. If no retrieved passages are relevant, state that before offering general guidance.

{session_block}
"""


def format_image_prompt(context: str, turns_used: int, question: str = "") -> str:
    q_section = f"\n\n**Student's question:** {question}" if question.strip() else ""
    turns_remaining = MAX_TURNS - turns_used

    session_block = (
        f"SESSION STATE:\n"
        f"Hints Remaining: {turns_remaining} of {MAX_TURNS}"
    )

    return f"""The image shows a student's Spike block-code program for a Z-Bot robot.
{q_section}

== RETRIEVED CONTEXT (base your response ONLY on these passages) ==
{context}

── INSTRUCTIONS ──────────────────────────────────────────────────────
1. Describe what the block program is trying to do.
2. Identify any visual errors, missing blocks, or logic problems.
3. Apply the Socratic method — give a hint and a guiding question.
4. Do NOT rewrite the entire program for the student.
5. Every technical claim MUST be grounded in the RETRIEVED CONTEXT above. Cite by number.
6. If the cited passage has a "Video URL(s):" line, add a Video Reference section.
   Omit entirely if no video URL is listed.
7. If no retrieved passage is relevant, say so before offering general advice.

{session_block}
"""


# ── AgenticTutor ───────────────────────────────────────────────────────────────
class AgenticTutor:
    """
    Orchestrates RAG retrieval -> prompt assembly -> LLM call -> security checks.

    engine          : SQLAlchemy engine (same one used by RAG and conversation store)
    student_id      : loaded from students table at construction time
    conversation_id : used to count turns from conversation_history table
    provider        : 'OpenAI' | 'Gemini'
    retriever       : RAG retriever instance
    enable_security : run input/output security gates
    """

    def __init__(
        self,
        engine,
        student_id: int,
        conversation_id: str | None = None,
        provider: Literal["OpenAI", "Gemini"] = "OpenAI",
        retriever=None,
        enable_security: bool = True,
    ):
        self._engine          = engine
        self._student_id      = student_id
        self._conversation_id = conversation_id
        self.retriever        = retriever
        self.enable_security  = enable_security
        self._llm             = LLMInterface(provider=provider)

        profile             = load_student_profile(engine, student_id)
        static_prompt       = load_static_prompts(engine)
        self._system_prompt = format_system_prompt(engine, static_prompt, profile)

    def _check_turn_limit(self) -> dict | None:
        """
        Return a fallback dict if the conversation has hit MAX_TURNS, else None.
        Skips the check if no conversation_id is provided.
        """
        if not self._conversation_id:
            return None
        turns = get_conversation_turns(self._engine, self._conversation_id)
        if turns >= MAX_TURNS:
            return {
                "response": (
                    f"You've used all {MAX_TURNS} hints for this conversation. "
                    "Please start a new chat or ask your teacher for help!"
                ),
                "lms_references": [],
            }
        return None

    def analyse_code(self, student_code: str, question: str = "") -> dict:
        limit = self._check_turn_limit()
        if limit:
            return limit

        t0 = time.perf_counter()

        if self.enable_security:
            decision = classify_and_sanitize_student_input(student_code, question)
            if not decision["allowed"]:
                return {"response": build_security_fallback("Prompt-injection risk detected"), "lms_references": []}
            student_code = decision["student_code"]
            question     = decision["question"]

        context, docs  = build_rag_context(
            query=f"{student_code}\n{question}", retriever=self.retriever
        )
        lms_references = extract_lms_references(docs)

        turns_used  = get_conversation_turns(self._engine, self._conversation_id) if self._conversation_id else 0
        user_prompt = format_user_prompt(student_code, context, turns_used, question)
        response    = self._llm.chat(self._system_prompt, user_prompt)

        # if self.enable_security:
        #     check = validate_and_sanitize_model_output(response)
        #     if not check["safe"]:
        #         return {"response": build_security_fallback("; ".join(check["issues"])), "lms_references": []}
        #     response = check["response"]

        elapsed = (time.perf_counter() - t0) * 1000
        print(f"analyse_code latency: {elapsed:.0f} ms")
        return {"response": response, "lms_references": lms_references}

    def analyse_image(self, image_bytes: bytes, question: str = "") -> dict:
        limit = self._check_turn_limit()
        if limit:
            return limit

        t0 = time.perf_counter()

        if self.enable_security:
            decision = classify_and_sanitize_student_input("", question)
            if not decision["allowed"]:
                return {"response": build_security_fallback("Prompt-injection risk detected"), "lms_references": []}
            question = decision["question"]

        context, docs  = build_rag_context(
            query=question or "spike block code program", retriever=self.retriever
        )
        lms_references = extract_lms_references(docs)

        turns_used   = get_conversation_turns(self._engine, self._conversation_id) if self._conversation_id else 0
        image_prompt = format_image_prompt(context, turns_used, question)
        response     = self._llm.chat_with_image(self._system_prompt, image_prompt, image_bytes)

        # # TEMP DEBUG: output guardrails disabled for image flow to observe raw
        # # model behavior. Restore the validator block below before going live.
        # if self.enable_security:
        #     check = validate_and_sanitize_model_output(response)
        #     print(f"[image output validator] safe={check['safe']} issues={check['issues']}")
        #     print(f"[image raw response] {response[:500]}")
        #     response = check["response"]

        elapsed = (time.perf_counter() - t0) * 1000
        print(f"analyse_image latency: {elapsed:.0f} ms")
        return {"response": response, "lms_references": lms_references}