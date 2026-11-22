"""FastAPI router for Socratic AI Programming Tutor.

Provides conceptual, pedagogical guidance without ever writing solution code.
Strictly prohibited during active proctored exam sessions.
"""

import logging
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.dependencies import get_current_user
from app.models.exam_session import ExamSession
from app.models.problem import Problem
from app.models.user import User
from app.schemas.ai_tutor import AITutorRequest, AITutorResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-tutor"])

SYSTEM_PROMPT = """You are CodeForge AI Tutor, a computer science professor and algorithms mentor.
Your pedagogical mission is to guide students to understand algorithmic problems and discover solutions themselves.

STRICT NON-NEGOTIABLE POLICY:
1. NEVER write or output full code solutions, functions, or complete implementations for the problem.
2. DO NOT write the algorithm for the student in any programming language.
3. Explain the underlying intuition, mathematical model, and algorithm logic in simple, plain language.
4. Use analogies, diagrams, or step-by-step logic traces with small sample inputs (e.g. tracing [2, 7, 11] with target 9).
5. If the student asks about syntax or standard library methods, provide generic, isolated syntax snippets (e.g. how a dictionary or vector works in general), never adapted to solve this problem.
6. If the student submits buggy code, point out which case or invariant fails (e.g. "What happens when the array has identical elements?" or "Check your loop bounds") rather than editing their code.
7. Be concise, encouraging, and structured (use bullet points and bold headers)."""


async def _resolve_problem_or_404(id_or_slug: str, db: AsyncSession) -> Problem:
    """Resolve a problem by UUID or slug."""
    try:
        problem_id = uuid.UUID(id_or_slug)
        res = await db.execute(select(Problem).where(Problem.id == problem_id))
    except ValueError:
        res = await db.execute(select(Problem).where(Problem.slug == id_or_slug))

    problem = res.scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{id_or_slug}' not found.",
        )
    return problem


def _generate_offline_pedagogical_guidance(
    problem: Problem,
    message: str,
    language: str | None,
    source_code: str | None,
) -> str:
    """Deterministic Socratic guidance engine when live LLM API key is not configured."""
    p_title = problem.title
    p_slug = problem.slug.lower()
    p_diff = problem.difficulty
    lang = language or "your chosen language"

    msg_lower = message.lower()

    # Topic-specific conceptual intuition
    if "two-sum" in p_slug:
        intuition = (
            "### 💡 Conceptual Intuition (Two Sum)\n\n"
            "1. **The Core Question**: For every number `x` in the array, you are asking: *'Does `target - x` exist in the array at a different index?'*\n"
            "2. **Brute Force vs Optimization**:\n"
            "   - **Brute Force**: Two nested loops check every pair `(i, j)`. This works in $O(N^2)$ time.\n"
            "   - **One-Pass Hash Map**: As you iterate through the list, keep a record of each number and its index. For the current number, check if its required complement `target - x` was already recorded!\n"
            "3. **Lookup Complexity**: Checking a hash map takes $O(1)$ on average, bringing the overall time complexity down to $O(N)$."
        )
    elif "hello-world" in p_slug:
        intuition = (
            "### 💡 Conceptual Intuition (Standard I/O)\n\n"
            "1. **Input**: Read the name string from standard input (`stdin`). Be sure to trim trailing newline characters.\n"
            "2. **Output**: Format the exact template `Hello, <name>!` without extra spaces.\n"
            "3. **Key Check**: Notice that the exclamation mark directly touches the name."
        )
    elif "reverse-string" in p_slug:
        intuition = (
            "### 💡 Conceptual Intuition (Two Pointers / In-Place Swapping)\n\n"
            "1. **Two Pointers**: Place one pointer at the start `left = 0` and one at the end `right = len - 1`.\n"
            "2. **Symmetry**: Swap the characters at `left` and `right`, then move inward (`left++`, `right--`) until they meet in the middle.\n"
            "3. **Efficiency**: This reverses the string in $O(N)$ time with $O(1)$ extra space."
        )
    elif "fizzbuzz" in p_slug:
        intuition = (
            "### 💡 Conceptual Intuition (Divisibility Order)\n\n"
            "1. **Order of Evaluation**: Numbers divisible by both 3 and 5 (i.e. divisible by 15) must be caught first!\n"
            "2. **Modulus Operator**: Use the `%` operator: `x % 3 == 0` and `x % 5 == 0`.\n"
            "3. **Edge Case**: Remember 1-based indexing from `1` up to `n` inclusive."
        )
    else:
        intuition = (
            f"### 💡 Algorithmic Breakdown for {p_title} ({p_diff.capitalize()})\n\n"
            "1. **Understand Constraints**: Check the input size bounds. If $N \\le 10^5$, an $O(N \\log N)$ or $O(N)$ approach is necessary to avoid Time Limit Exceeded.\n"
            "2. **Identify Invariants**: What properties must remain true at each step of your loop or recursion?\n"
            "3. **Test with Small Input**: Trace the example input manually on paper before implementing."
        )

    # Edge cases section
    edge_cases = (
        "### 🔍 Common Edge Cases to Verify:\n"
        "- Minimum boundary inputs (empty, length 1, or 0 values).\n"
        "- Negative values and potential integer overflow if numbers can be large.\n"
        "- Duplicate values or elements appearing multiple times in the collection."
    )

    # Syntax guidance if requested
    syntax_note = ""
    if any(k in msg_lower for k in ["syntax", "how to", "function", "map", "dict", "array", "list"]):
        syntax_note = (
            f"\n\n### 🛠️ Language Notes ({lang.upper()}):\n"
            "- In Python, use `{}` or `dict()` for fast lookups: `seen = {}`\n"
            "- In Java, use `HashMap<Integer, Integer> map = new HashMap<>();`\n"
            "- In C++, use `std::unordered_map<int, int> map;`\n"
            "- In C, consider static frequency arrays or sorting if element ranges permit."
        )

    code_feedback = ""
    if source_code and len(source_code.strip()) > 30:
        code_feedback = (
            "\n\n### 📝 Review of Your Current Approach:\n"
            "- Your code structure is set up. Step through your loop logic: check if your indexing accounts for all edge cases.\n"
            "- Ensure your return or print format matches the exact specification without trailing whitespace."
        )

    return (
        f"{intuition}\n\n"
        f"{edge_cases}"
        f"{syntax_note}"
        f"{code_feedback}\n\n"
        f"---\n"
        f"*💡 Tip: To enable real-time interactive Gemini AI responses, add `GEMINI_API_KEY=your_key` to `.env` (Free tier at [Google AI Studio](https://aistudio.google.com)).*"
    )


@router.post(
    "/problems/{id_or_slug}/ai-tutor",
    response_model=AITutorResponse,
)
async def ask_ai_tutor(
    id_or_slug: str,
    body: AITutorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AITutorResponse:
    """Pedagogical AI Tutor assistance for students.

    Explains problem logic, invariants, and edge cases.
    STRICTLY PROHIBITED and blocked during proctored exam sessions.
    """
    # ── 1. Anti-Cheat & Exam Guard ───────────────────────────────────────────
    # A) Check if client explicitly referenced an exam session
    if body.exam_session_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI Tutor is disabled during proctored assessment sessions.",
        )

    # B) Check if the student currently has ANY active in-progress exam session
    active_exam_res = await db.execute(
        select(ExamSession).where(
            ExamSession.user_id == current_user.id,
            ExamSession.submitted_at.is_(None),
        )
    )
    if active_exam_res.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI Tutor is locked while an exam session is in progress. Complete or submit your exam first.",
        )

    # ── 2. Resolve Problem ───────────────────────────────────────────────────
    problem = await _resolve_problem_or_404(id_or_slug, db)

    # ── 3. Call Live Gemini API if API key is configured ─────────────────────
    api_key = settings.gemini_api_key.strip()
    if api_key:
        code_snippet = f"\n\nStudent's Current Code ({body.language}):\n```\n{body.source_code}\n```" if body.source_code else ""
        user_prompt = (
            f"Problem: {problem.title} (Difficulty: {problem.difficulty})\n"
            f"Description:\n{problem.description[:1500]}\n"
            f"Language: {body.language or 'general'}"
            f"{code_snippet}\n\n"
            f"Student Question / Request:\n{body.message}"
        )

        model_name = settings.gemini_model.strip() or "gemini-2.5-flash"
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        gemini_payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(gemini_url, json=gemini_payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            return AITutorResponse(
                                reply=text.strip(),
                                model=model_name,
                                is_live=True,
                            )
                else:
                    logger.warning("Gemini API returned status %d: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("Gemini API call failed (%s); falling back to offline tutor", exc)

    # ── 4. Fallback Socratic Guidance Engine ──────────────────────────────────
    offline_reply = _generate_offline_pedagogical_guidance(
        problem=problem,
        message=body.message,
        language=body.language,
        source_code=body.source_code,
    )
    return AITutorResponse(
        reply=offline_reply,
        model="offline-socratic",
        is_live=False,
    )
