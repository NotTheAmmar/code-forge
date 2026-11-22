"""Database seeding script for CodeForge TA-2 demonstration.

Seeds:
1. Default Instructor: admin@codeforge.local / changeme
2. Students:
   - student@codeforge.local / changeme ("Alex Student")
   - alice@codeforge.local / changeme ("Alice Johnson")
   - bob@codeforge.local / changeme ("Bob Smith")
   - charlie@codeforge.local / changeme ("Charlie Brown")
   - diana@codeforge.local / changeme ("Diana Prince")
3. Sample Course: CS101: Introduction to Programming (invite code: CS101A)
4. Sample Problems (all 4 attached to CS101 with Java & Python starters and test cases):
   - hello-world
   - two-sum
   - reverse-string
   - fizzbuzz
5. Active Lab Session: Lab 1: Programming Basics & Warm-up (mandatory: 1, extra solves earn badges)
6. Pre-seeded submissions & badges for live presentation dashboard:
   - Diana: 4 solved, 3 badges (Leaderboard top)
   - Alice: 3 solved, 2 badges
   - Bob: 2 solved, 1 badge
   - Charlie: 1 solved, 0 badges (baseline)
   - Alex Student: 1 solved (ready for live live badge earning demo!)

Idempotent: Safe to re-run multiple times without duplicate record conflicts.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, engine
from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User
from app.services.auth_service import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def seed() -> None:
    logger.info("Starting CodeForge database seeding...")

    async with AsyncSessionLocal() as session:
        # ── 1. Instructor User ────────────────────────────────────────────────
        inst_res = await session.execute(
            select(User).where(User.email == "admin@codeforge.local")
        )
        instructor = inst_res.scalar_one_or_none()
        if instructor is None:
            instructor = User(
                id=uuid.uuid4(),
                email="admin@codeforge.local",
                name="Admin Instructor",
                role="instructor",
                password_hash=hash_password("changeme"),
            )
            session.add(instructor)
            await session.flush()
            logger.info("Created default instructor: admin@codeforge.local")
        else:
            instructor.password_hash = hash_password("changeme")
            await session.flush()
            logger.info("Updated default instructor password: admin@codeforge.local")

        # ── 2. Student Users ──────────────────────────────────────────────────
        demo_students = [
            ("student@codeforge.local", "Alex Student"),
            ("alice@codeforge.local", "Alice Johnson"),
            ("bob@codeforge.local", "Bob Smith"),
            ("charlie@codeforge.local", "Charlie Brown"),
            ("diana@codeforge.local", "Diana Prince"),
        ]
        student_users: dict[str, User] = {}

        for email, name in demo_students:
            stud_res = await session.execute(
                select(User).where(User.email == email)
            )
            st = stud_res.scalar_one_or_none()
            if st is None:
                st = User(
                    id=uuid.uuid4(),
                    email=email,
                    name=name,
                    role="student",
                    password_hash=hash_password("changeme"),
                )
                session.add(st)
                await session.flush()
                logger.info("Created student: %s (%s)", email, name)
            else:
                st.password_hash = hash_password("changeme")
                await session.flush()
            student_users[email] = st

        # ── 3. Course ─────────────────────────────────────────────────────────
        course_res = await session.execute(
            select(Course).where(Course.invite_code == "CS101A")
        )
        course = course_res.scalar_one_or_none()
        if course is None:
            course = Course(
                id=uuid.uuid4(),
                title="CS101: Introduction to Programming",
                description="Introductory course covering algorithms, control flow, and data structures in Java and Python.",
                created_by=instructor.id,
                invite_code="CS101A",
            )
            session.add(course)
            await session.flush()
            logger.info("Created course: CS101 (Invite Code: CS101A)")
        else:
            logger.info("Course CS101 already exists (Invite Code: %s)", course.invite_code)

        # ── 4. Enrollments ────────────────────────────────────────────────────
        all_enroll = [(instructor, "instructor")] + [(st, "student") for st in student_users.values()]
        for user, role in all_enroll:
            enr_res = await session.execute(
                select(Enrollment).where(
                    Enrollment.course_id == course.id,
                    Enrollment.user_id == user.id,
                )
            )
            if enr_res.scalar_one_or_none() is None:
                enr = Enrollment(
                    id=uuid.uuid4(),
                    course_id=course.id,
                    user_id=user.id,
                    role=role,
                )
                session.add(enr)
                await session.flush()
                logger.info("Enrolled %s (%s) in CS101", user.name, role)

        # ── 5. Problems & Test Cases ──────────────────────────────────────────
        problems_def = [
            {
                "slug": "hello-world",
                "title": "Hello World",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Read a single line containing a name from standard input, and print `Hello, <name>!` to standard output.\n\n"
                    "#### Example Input\n```\nAlice\n```\n#### Example Output\n```\nHello, Alice!\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        String name = sc.nextLine();\n"
                    "        System.out.println(\"Hello, \" + name + \"!\");\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "name = sys.stdin.read().strip()\n"
                    "print(f\"Hello, {name}!\")\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "Alice\n", "expected_output": "Hello, Alice!", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "Bob\n", "expected_output": "Hello, Bob!", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "CodeForge\n", "expected_output": "Hello, CodeForge!", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "slug": "two-sum",
                "title": "Two Sum",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an array of integers `nums` and an integer `target`, return the 0-based indices of the two numbers such that they add up to `target`.\n\n"
                    "#### Input\n"
                    "- First line: integer `n` (array length)\n"
                    "- Second line: `n` space-separated integers\n"
                    "- Third line: integer `target`\n\n"
                    "#### Output\n"
                    "Two space-separated indices (`index1 index2`)\n\n"
                    "#### Example Input\n```\n4\n2 7 11 15\n9\n```\n#### Example Output\n```\n0 1\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        int[] nums = new int[n];\n"
                    "        for (int i = 0; i < n; i++) {\n"
                    "            nums[i] = sc.nextInt();\n"
                    "        }\n"
                    "        int target = sc.nextInt();\n"
                    "        // Your code here\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "def solve():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    if not data: return\n"
                    "    n = int(data[0])\n"
                    "    nums = [int(x) for x in data[1:n+1]]\n"
                    "    target = int(data[n+1])\n"
                    "    # Your code here\n\n"
                    "if __name__ == '__main__':\n"
                    "    solve()\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "4\n2 7 11 15\n9\n", "expected_output": "0 1", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "3\n3 2 4\n6\n", "expected_output": "1 2", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "2\n3 3\n6\n", "expected_output": "0 1", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "slug": "reverse-string",
                "title": "Reverse a String",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Read a single line of text from standard input, reverse it, and print the reversed string to standard output.\n\n"
                    "#### Example Input\n```\nhello\n```\n#### Example Output\n```\nolleh\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        String s = sc.nextLine();\n"
                    "        System.out.println(new StringBuilder(s).reverse().toString());\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "s = sys.stdin.read().rstrip('\\r\\n')\n"
                    "print(s[::-1])\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "hello\n", "expected_output": "olleh", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "Antigravity\n", "expected_output": "ytivargitnA", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "racecar\n", "expected_output": "racecar", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "slug": "fizzbuzz",
                "title": "FizzBuzz",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an integer N on standard input, print numbers from 1 to N each on a separate line.\n"
                    "- For multiples of 3, print `Fizz`\n"
                    "- For multiples of 5, print `Buzz`\n"
                    "- For numbers which are multiples of both 3 and 5, print `FizzBuzz`\n\n"
                    "#### Example Input\n```\n5\n```\n#### Example Output\n```\n1\n2\nFizz\n4\nBuzz\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        for (int i = 1; i <= n; i++) {\n"
                    "            if (i % 15 == 0) System.out.println(\"FizzBuzz\");\n"
                    "            else if (i % 3 == 0) System.out.println(\"Fizz\");\n"
                    "            else if (i % 5 == 0) System.out.println(\"Buzz\");\n"
                    "            else System.out.println(i);\n"
                    "        }\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "data = sys.stdin.read().strip()\n"
                    "if data:\n"
                    "    n = int(data)\n"
                    "    for i in range(1, n + 1):\n"
                    "        if i % 15 == 0:\n"
                    "            print('FizzBuzz')\n"
                    "        elif i % 3 == 0:\n"
                    "            print('Fizz')\n"
                    "        elif i % 5 == 0:\n"
                    "            print('Buzz')\n"
                    "        else:\n"
                    "            print(i)\n"
                ),
                "test_cases": [
                    {
                        "label": "01",
                        "input_data": "5\n",
                        "expected_output": "1\n2\nFizz\n4\nBuzz",
                        "is_visible": True,
                        "order_index": 0,
                    },
                    {
                        "label": "02",
                        "input_data": "15\n",
                        "expected_output": (
                            "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n"
                            "11\nFizz\n13\n14\nFizzBuzz"
                        ),
                        "is_visible": False,
                        "order_index": 1,
                    },
                ],
            },
        ]

        problem_map: dict[str, Problem] = {}
        seeded_problem_ids: list[uuid.UUID] = []

        for p_def in problems_def:
            prob_res = await session.execute(
                select(Problem).where(Problem.slug == p_def["slug"])
            )
            prob = prob_res.scalar_one_or_none()
            if prob is None:
                prob = Problem(
                    id=uuid.uuid4(),
                    course_id=course.id,
                    created_by=instructor.id,
                    slug=p_def["slug"],
                    title=p_def["title"],
                    description=p_def["description"],
                    difficulty=p_def["difficulty"],
                    starter_code_java=p_def["starter_code_java"],
                    starter_code_python=p_def["starter_code_python"],
                    time_limit_sec=10,
                    memory_limit_mb=128,
                )
                session.add(prob)
                await session.flush()

                for tc_def in p_def["test_cases"]:
                    tc = TestCase(
                        id=uuid.uuid4(),
                        problem_id=prob.id,
                        label=tc_def["label"],
                        input_data=tc_def["input_data"],
                        expected_output=tc_def["expected_output"],
                        is_visible=tc_def["is_visible"],
                        order_index=tc_def["order_index"],
                    )
                    session.add(tc)

                logger.info("Created problem: %s (%s)", prob.title, prob.slug)
            else:
                # Ensure problem belongs to CS101 course
                prob.course_id = course.id
                prob.created_by = instructor.id
                session.add(prob)
                logger.info("Problem %s assigned to CS101", prob.slug)

            problem_map[p_def["slug"]] = prob
            seeded_problem_ids.append(prob.id)

        await session.flush()

        # ── 6. Active Lab Session ─────────────────────────────────────────────
        lab_title = "Lab 1: Programming Basics & Warm-up"
        lab_res = await session.execute(
            select(LabSession).where(
                LabSession.course_id == course.id,
                LabSession.title == lab_title,
            )
        )
        lab = lab_res.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if lab is None:
            lab = LabSession(
                id=uuid.uuid4(),
                course_id=course.id,
                title=lab_title,
                description="Introductory lab session covering I/O, arithmetic, string manipulation, and control flow in Java and Python.",
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=7),
                mandatory_count=1,
                is_active=True,
            )
            session.add(lab)
            await session.flush()
        else:
            lab.is_active = True
            lab.mandatory_count = 1
            lab.ends_at = now + timedelta(days=7)
            session.add(lab)
            await session.flush()

        # Ensure all 4 problems are attached to LabSessionProblem
        for idx, pid in enumerate(seeded_problem_ids):
            lsp_res = await session.execute(
                select(LabSessionProblem).where(
                    LabSessionProblem.lab_session_id == lab.id,
                    LabSessionProblem.problem_id == pid,
                )
            )
            if lsp_res.scalar_one_or_none() is None:
                lsp = LabSessionProblem(
                    id=uuid.uuid4(),
                    lab_session_id=lab.id,
                    problem_id=pid,
                    order_index=idx,
                )
                session.add(lsp)

        await session.flush()
        logger.info("Lab session '%s' ready with %d problems", lab.title, len(seeded_problem_ids))

        # ── 7. Seed Demo Submissions & Badges ─────────────────────────────────
        # Scenario:
        # Diana Prince: solved 4 problems → 3 badges
        # Alice Johnson: solved 3 problems → 2 badges
        # Bob Smith: solved 2 problems → 1 badge
        # Charlie Brown: solved 1 problem → 0 badges
        # Alex Student: solved 1 problem → 0 badges (so student can earn a badge live!)
        student_solves = {
            "diana@codeforge.local": ["hello-world", "two-sum", "reverse-string", "fizzbuzz"],
            "alice@codeforge.local": ["hello-world", "two-sum", "reverse-string"],
            "bob@codeforge.local": ["hello-world", "two-sum"],
            "charlie@codeforge.local": ["hello-world"],
            "student@codeforge.local": ["hello-world"],
        }

        # For repeatable presentations: reset Alex Student's extra demo submissions & badges
        alex_user = student_users["student@codeforge.local"]
        alex_extra_pids = [problem_map[s].id for s in ["two-sum", "reverse-string", "fizzbuzz"] if s in problem_map]
        await session.execute(
            delete(Badge).where(
                Badge.user_id == alex_user.id,
                Badge.lab_session_id == lab.id,
            )
        )
        await session.execute(
            delete(Submission).where(
                Submission.user_id == alex_user.id,
                Submission.lab_session_id == lab.id,
                Submission.problem_id.in_(alex_extra_pids),
            )
        )

        for email, solved_slugs in student_solves.items():
            user = student_users[email]
            for order, slug in enumerate(solved_slugs):
                prob = problem_map[slug]
                
                # Check if submission exists
                sub_res = await session.execute(
                    select(Submission).where(
                        Submission.user_id == user.id,
                        Submission.problem_id == prob.id,
                        Submission.lab_session_id == lab.id,
                    )
                )
                if sub_res.scalar_one_or_none() is None:
                    sub = Submission(
                        id=uuid.uuid4(),
                        problem_id=prob.id,
                        user_id=user.id,
                        lab_session_id=lab.id,
                        language="python",
                        source_code=prob.starter_code_python or "# Solution",
                        status="completed",
                        score=100,
                        total_cases=3,
                        passed_cases=3,
                        is_full_submit=True,
                        results_json=[],
                        execution_time_ms=42,
                        submitted_at=now - timedelta(minutes=(60 - order * 10)),
                    )
                    session.add(sub)

                # Badges: awarded for each extra problem solved beyond mandatory_count (1)
                # i.e., index >= 1 awards a badge
                if order >= lab.mandatory_count:
                    badge_res = await session.execute(
                        select(Badge).where(
                            Badge.user_id == user.id,
                            Badge.lab_session_id == lab.id,
                            Badge.problem_id == prob.id,
                        )
                    )
                    if badge_res.scalar_one_or_none() is None:
                        badge = Badge(
                            id=uuid.uuid4(),
                            user_id=user.id,
                            lab_session_id=lab.id,
                            problem_id=prob.id,
                            earned_at=now - timedelta(minutes=(60 - order * 10)),
                        )
                        session.add(badge)

        await session.commit()

    logger.info("Seeding completed successfully!")
    logger.info("==================================================")
    logger.info("  Default Instructor: admin@codeforge.local / changeme")
    logger.info("  Default Student:    student@codeforge.local / changeme")
    logger.info("  Other Students:     diana@, alice@, bob@, charlie@ (password: changeme)")
    logger.info("  Default Course:     CS101 (Invite Code: CS101A)")
    logger.info("  Lab Session:        %s", lab_title)
    logger.info("  Pre-seeded Badges:  Diana (3 ⭐), Alice (2 ⭐), Bob (1 ⭐)")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(seed())
