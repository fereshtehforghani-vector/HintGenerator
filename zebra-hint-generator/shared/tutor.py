"""
ZebraBot Socratic tutor — core logic.

Contains:
  - SOCRATIC_SYSTEM_PROMPT  (with kid-safety appendix)
  - format_user_prompt / format_image_prompt
  - AgenticTutor class
"""

import time
from pathlib import Path
from typing import Literal

from shared.llm_interface import LLMInterface
from shared.rag_utils import build_rag_context, extract_lms_references
from shared.security import (
    KID_SAFE_APPENDIX,
    build_security_fallback,
    classify_and_sanitize_student_input,
    validate_and_sanitize_model_output,
)

# ── Socratic system prompt ─────────────────────────────────────────────────────
SOCRATIC_SYSTEM_PROMPT = """You are "ZebraBot", a Socratic programming tutor for a Z-Bot
robotics course using custom C++ libraries on an ESP32 board.

YOUR CORE RULES — follow these strictly:
─────────────────────────────────────────
1. NEVER give the student the complete corrected code.
2. Use the Socratic method: guide through questions and progressive hints.
3. Always identify the TYPE of mistake first (e.g., "Syntax Error",
   "Logic Error", "Library Misuse", "Missing Initialization").
4. Structure every response in these sections:
   🔍 **Mistake Type**: [category from taxonomy]
   💡 **Hint 1** (gentle nudge — point to the area, NOT the fix)
   🤔 **Guiding Question**: Ask the student a question that will lead them to discover the fix.
   📚 **Curriculum Reference**: Cite a 📘 Curriculum passage using its [N] number (e.g. "[2]").
      These numbers are shown to the student as clickable lesson links.
      ONLY use an [N] number here (never [L1], [L2] etc.).
      Fall back to a library passage only if no Curriculum passage is relevant.
5. If you can't find the issue, say so honestly and ask the student to
   describe their intended behaviour.
6. Be encouraging, concise, and age-appropriate (teens / young adults).
7. For image inputs (Spike block code): describe what you see and identify
   which block or connection looks problematic.

GROUNDING RULES — these are critical for accuracy:
──────────────────────────────────────────────────
• ONLY use facts, function names, parameter details, and API behaviour that
  appear in the RETRIEVED CONTEXT provided below.
• When you mention a library function (e.g. begin(), getYaw(), read()),
  describe it exactly as the context documents it — do not invent parameters,
  return types, or behaviour.
• Curriculum passages are numbered [1], [2], … and match the LMS lesson links shown to
  the student.  Library/other passages are numbered [L1], [L2], …
• Cite passages by their label, e.g. "According to [2] Curriculum…" or "See [L3] Library Docs…"
• If the retrieved context does NOT contain enough information to explain
  the issue, explicitly say: "The retrieved references do not cover this
  specific topic — here is my best general guidance:" before giving any
  advice that goes beyond the context.
• NEVER fabricate library names, function signatures, port numbers, or
  hardware details that are not in the context.

COMMON MISTAKE TAXONOMY (use these labels when they match):
- Missing begin() / initialization
- Assignment in condition (= instead of ==)
- Wrong port number
- Variable not updated in loop
- Infinite loop in setup()
- Missing variable declaration
- Incorrect library function call
- Sensor read not stored in variable
- Logic / control flow error
- Missing semicolon / brace
- Case sensitivity error
- Unnecessary code block
- Concept misunderstanding
""" + "\n\n" + KID_SAFE_APPENDIX


# ── Prompt formatters ──────────────────────────────────────────────────────────
def format_user_prompt(student_code: str, context: str, question: str = "") -> str:
    q_section = f"\n\n**Student's question:** {question}" if question.strip() else ""
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
3. Every technical claim you make (function names, parameters, port numbers,
   library behaviour) MUST come from the RETRIEVED CONTEXT above.
4. Citation rules:
   - Curriculum passages are labelled [1], [2], …  → cite as "According to [2]…"
   - Library/other passages are labelled [L1], [L2], … → cite as "See [L3]…"
   - In the 📚 Curriculum Reference section use ONLY [N] numbers (not [LN]).
5. If none of the retrieved passages are relevant, state that clearly
   before offering any general guidance.
"""


def format_image_prompt(context: str, question: str = "") -> str:
    q_section = f"\n\n**Student's question:** {question}" if question.strip() else ""
    return f"""The image shows a student's Spike block-code program for a Z-Bot robot.
{q_section}

== RETRIEVED CONTEXT (base your response ONLY on these passages) ==
{context}

── INSTRUCTIONS ──────────────────────────────────────────────────────
1. Describe what the block program is trying to do.
2. Identify any visual errors, missing blocks, or logic problems.
3. Apply the Socratic method — give a hint and a guiding question.
4. Do NOT rewrite the entire program for the student.
5. Every technical claim MUST be grounded in the RETRIEVED CONTEXT above.
   Cite passages by number.
6. If no retrieved passage is relevant, say so before offering general advice.
"""


# ── AgenticTutor ───────────────────────────────────────────────────────────────
class AgenticTutor:
    """
    Orchestrates RAG retrieval → prompt assembly → LLM call → security checks.

    Designed for use inside a Cloud Function:
      - No IPython / notebook dependencies
      - display_output is always False (returns plain string)
      - analyse_image is omitted from the GCP deployment (text-only for v1)
    """

    def __init__(
        self,
        provider: Literal["OpenAI", "Gemini"] = "OpenAI",
        retriever=None,
        enable_security: bool = True,
    ):
        self.retriever       = retriever
        self.enable_security = enable_security
        self._llm            = LLMInterface(provider=provider)

    def analyse_code(self, student_code: str, question: str = "") -> dict:
        """
        Analyse a student's C++ code and return a dict with:
            {
                "response":       "<Socratic hint markdown>",
                "lms_references": [
                    {
                        "title":     "Variables",
                        "module":    5,
                        "course":    "Self Driving Car",
                        "course_id": "sdv",
                        "content":   "<first 800 chars of the lesson>"
                    },
                    ...
                ]
            }

        Parameters
        ----------
        student_code : the C++ code submitted by the student
        question     : optional free-text question from the student
        """
        t0 = time.perf_counter()

        if self.enable_security:
            decision = classify_and_sanitize_student_input(student_code, question)
            if not decision["allowed"]:
                fallback = build_security_fallback("Prompt-injection risk detected")
                return {"response": fallback, "lms_references": []}
            student_code = decision["student_code"]
            question     = decision["question"]

        context, docs = build_rag_context(
            query=f"{student_code}\n{question}",
            retriever=self.retriever,
        )
        lms_references = extract_lms_references(docs)

        user_prompt = format_user_prompt(student_code, context, question)
        response    = self._llm.chat(SOCRATIC_SYSTEM_PROMPT, user_prompt)

        if self.enable_security:
            check = validate_and_sanitize_model_output(response)
            if not check["safe"]:
                fallback = build_security_fallback("; ".join(check["issues"]))
                return {"response": fallback, "lms_references": []}
            response = check["response"]

        elapsed = (time.perf_counter() - t0) * 1000
        print(f"analyse_code latency: {elapsed:.0f} ms")
        return {"response": response, "lms_references": lms_references}

    def analyse_image(self, image_bytes: bytes, question: str = "") -> dict:
        """
        Analyse an image of a student's Spike block-code program.

        Retrieval uses the student's question as the query (image embedding
        is not supported by gemini-embedding-2). Returns the same shape as
        analyse_code: {"response", "lms_references"}.
        """
        t0 = time.perf_counter()

        if self.enable_security:
            decision = classify_and_sanitize_student_input("", question)
            if not decision["allowed"]:
                fallback = build_security_fallback("Prompt-injection risk detected")
                return {"response": fallback, "lms_references": []}
            question = decision["question"]

        context, docs = build_rag_context(
            query=question or "spike block code program",
            retriever=self.retriever,
        )
        lms_references = extract_lms_references(docs)

        user_prompt = format_image_prompt(context, question)
        response    = self._llm.chat_with_image(
            SOCRATIC_SYSTEM_PROMPT, user_prompt, image_bytes
        )

        if self.enable_security:
            check = validate_and_sanitize_model_output(response)
            if not check["safe"]:
                fallback = build_security_fallback("; ".join(check["issues"]))
                return {"response": fallback, "lms_references": []}
            response = check["response"]

        elapsed = (time.perf_counter() - t0) * 1000
        print(f"analyse_image latency: {elapsed:.0f} ms")
        return {"response": response, "lms_references": lms_references}
