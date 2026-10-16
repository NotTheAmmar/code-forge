"""Database seeding script for CodeForge TA-2 demonstration.

Seeds:
1. Default Instructor: admin@codeforge.local / changeme
2. Default Student: student@codeforge.local / changeme
3. Sample Course: CS101: Introduction to Programming (invite code: CS101A)
4. Sample Problems:
   - hello-world (Java & Python starter code + visible & hidden test cases)
   - two-sum (Java & Python starter code + visible & hidden test cases)
   - reverse-string (Java & Python starter code + visible & hidden test cases)
   - fizzbuzz (Java & Python starter code + visible & hidden test cases)
5. Active Lab Session: Lab 1: Programming Basics & Warm-up (mandatory: 1, extra solves earn badges)

Idempotent: Safe to re-run multiple times without duplicate record conflicts.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, engine
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
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

        # ── 2. Student User ───────────────────────────────────────────────────
        stud_res = await session.execute(
            select(User).where(User.email == "student@codeforge.local")
        )
        student = stud_res.scalar_one_or_none()
        if student is None:
            student = User(
                id=uuid.uuid4(),
                email="student@codeforge.local",
                name="Alex Student",
                role="student",
                password_hash=hash_password("changeme"),
            )
            session.add(student)
            await session.flush()
            logger.info("Created default student: student@codeforge.local")
        else:
            student.password_hash = hash_password("changeme")
            await session.flush()
            logger.info("Updated default student password: student@codeforge.local")

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
        for user, role in [(instructor, "instructor"), (student, "student")]:
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
                    "Given two integers separated by space on standard input, calculate and print their sum.\n\n"
                    "#### Example Input\n```\n3 5\n```\n#### Example Output\n```\n8\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int a = sc.nextInt();\n"
                    "        int b = sc.nextInt();\n"
                    "        System.out.println(a + b);\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "tokens = sys.stdin.read().split()\n"
                    "if len(tokens) >= 2:\n"
                    "    print(int(tokens[0]) + int(tokens[1]))\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "3 5\n", "expected_output": "8", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "-10 25\n", "expected_output": "15", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "1000 2345\n", "expected_output": "3345", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "slug": "reverse-string",
                "title": "Reverse a String",
                "difficulty": "medium",
                "description": (
                    "### Problem Statement\n\n"
                    "Read a single line of text from standard input and print the string reversed.\n\n"
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
                        "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz",
                        "is_visible": False,
                        "order_index": 1,
                    },
                ],
            },
        ]

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
                logger.info("Problem %s already exists", prob.slug)

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

            for idx, pid in enumerate(seeded_problem_ids):
                lsp = LabSessionProblem(
                    id=uuid.uuid4(),
                    lab_session_id=lab.id,
                    problem_id=pid,
                    order_index=idx,
                )
                session.add(lsp)

            logger.info("Created lab session: %s (Mandatory: 1, Problems: %d)", lab.title, len(seeded_problem_ids))
        else:
            logger.info("Lab session '%s' already exists", lab_title)

        await session.commit()

    logger.info("Seeding completed successfully!")
    logger.info("==================================================")
    logger.info("  Default Instructor: admin@codeforge.local / changeme")
    logger.info("  Default Student:    student@codeforge.local / changeme")
    logger.info("  Default Course:     CS101 (Invite Code: CS101A)")
    logger.info("  Lab Session:        %s", lab_title)
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(seed())
