"""Database seeding script for CodeForge Final Jury demonstration.

Seeds rich, comprehensive multi-entity demonstration data:
1. Instructors (3 accounts):
   - admin@codeforge.local / changeme ("Admin Instructor" - System Admin & Faculty Head)
   - prof.chen@codeforge.local / changeme ("Prof. Alan Chen" - DSA & Algorithms)
   - dr.stone@codeforge.local / changeme ("Dr. Elena Stone" - Systems & Low-Level)
2. Students (12 accounts, all password: changeme):
   - student@codeforge.local ("Alex Student" - Fresh student for live walkthroughs)
   - alice@codeforge.local ("Alice Johnson")
   - bob@codeforge.local ("Bob Smith")
   - charlie@codeforge.local ("Charlie Brown")
   - diana@codeforge.local ("Diana Prince" - Top leaderboard achiever)
   - evan@codeforge.local ("Evan Wright")
   - fiona@codeforge.local ("Fiona Gallagher")
   - george@codeforge.local ("George Clark")
   - hannah@codeforge.local ("Hannah Abbott")
   - ian@codeforge.local ("Ian Malcolm")
   - julia@codeforge.local ("Julia Roberts")
   - kevin@codeforge.local ("Kevin Mitnick" - Systems hacker)
3. Courses (4 distinct courses across domains):
   - CS101: Introduction to Programming (invite: CS101A)
   - CS201: Data Structures & Algorithms (invite: CS201B)
   - CS301: Systems & Low-Level C/C++ Programming (invite: CS301C)
   - MATH150: Discrete Mathematics for CS (invite: M150D)
4. Problem Catalog (11 problems with Java, Python, C, C++ starter codes and full test cases):
   - CS101: hello-world, two-sum, reverse-string, fizzbuzz, palindrome-number
   - CS201: valid-palindrome, binary-search, merge-sorted-arrays, maximum-subarray
   - CS301: bitwise-parity, pointer-swap-reverse
5. Lab Sessions (4 sessions across courses):
   - CS101: Lab 1: Programming Basics & Warm-up (Active, mandatory: 1)
   - CS201: Lab 2: Searching & Pointer Invariants (Active, mandatory: 2)
   - CS301: Lab 3: C/C++ Memory & Bitwise Lab (Active, mandatory: 1)
   - CS101: Lab 0: Diagnostic Orientation (Closed/Archived, mandatory: 1)
6. Proctored Exams (4 assessments):
   - CS101 Midterm Examination: Fundamentals (Active window, pre-seeded sessions & violations)
   - CS101 Final Assessment: Problem Solving Mastery (Scheduled window)
   - CS201 Midterm: Algorithmic Efficiency & Searching (Active window)
   - CS301 Practical Systems Exam: Memory & Bitwise Ops (Active window)
7. Learning Modules (6 curriculum modules with theory markdown, video lectures, and practice problems).
8. Pre-seeded Submissions, Badges, and Anti-cheat Violations:
   - Rich leaderboard, gradebook matrix, analytics error distribution, and proctoring logs.

Idempotent: Safe to re-run multiple times without duplicate record conflicts.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.exam import Exam, ExamProblem
from app.models.exam_session import ExamSession
from app.models.exam_violation import ExamViolation
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.learning_content import LearningContent
from app.models.learning_module import LearningModule
from app.models.module_progress import ModuleProgress
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User
from app.services.auth_service import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def seed() -> None:
    logger.info("Starting CodeForge rich multi-entity database seeding...")

    async with AsyncSessionLocal() as session:
        # ── 1. Instructor Accounts ───────────────────────────────────────────
        instructor_defs = [
            ("admin@codeforge.local", "Admin Instructor"),
            ("prof.chen@codeforge.local", "Prof. Alan Chen"),
            ("dr.stone@codeforge.local", "Dr. Elena Stone"),
        ]
        instructors: dict[str, User] = {}
        for email, name in instructor_defs:
            inst_res = await session.execute(
                select(User).where(User.email == email)
            )
            inst = inst_res.scalar_one_or_none()
            if inst is None:
                inst = User(
                    id=uuid.uuid4(),
                    email=email,
                    name=name,
                    role="instructor",
                    password_hash=hash_password("changeme"),
                )
                session.add(inst)
                await session.flush()
                logger.info("Created instructor: %s (%s)", email, name)
            else:
                inst.name = name
                inst.password_hash = hash_password("changeme")
                await session.flush()
            instructors[email] = inst

        admin_inst = instructors["admin@codeforge.local"]
        chen_inst = instructors["prof.chen@codeforge.local"]
        stone_inst = instructors["dr.stone@codeforge.local"]

        # ── 2. Student Accounts ──────────────────────────────────────────────
        demo_students = [
            ("student@codeforge.local", "Alex Student"),
            ("alice@codeforge.local", "Alice Johnson"),
            ("bob@codeforge.local", "Bob Smith"),
            ("charlie@codeforge.local", "Charlie Brown"),
            ("diana@codeforge.local", "Diana Prince"),
            ("evan@codeforge.local", "Evan Wright"),
            ("fiona@codeforge.local", "Fiona Gallagher"),
            ("george@codeforge.local", "George Clark"),
            ("hannah@codeforge.local", "Hannah Abbott"),
            ("ian@codeforge.local", "Ian Malcolm"),
            ("julia@codeforge.local", "Julia Roberts"),
            ("kevin@codeforge.local", "Kevin Mitnick"),
        ]
        students: dict[str, User] = {}
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
                st.name = name
                st.password_hash = hash_password("changeme")
                await session.flush()
            students[email] = st

        # ── 3. Courses ───────────────────────────────────────────────────────
        course_defs = [
            {
                "invite_code": "CS101A",
                "title": "CS101: Introduction to Programming",
                "description": "Foundational programming paradigms, algorithm formulation, standard I/O, and control flow across Python, Java, C, and C++.",
                "creator": admin_inst,
            },
            {
                "invite_code": "CS201B",
                "title": "CS201: Data Structures & Algorithms",
                "description": "Deep dive into algorithmic complexity, asymptotic analysis, search invariants, divide & conquer, and dynamic memory structures.",
                "creator": chen_inst,
            },
            {
                "invite_code": "CS301C",
                "title": "CS301: Systems & Low-Level C/C++ Programming",
                "description": "Low-level systems programming, pointer mechanics, manual memory layout, bitwise manipulation, and system boundaries.",
                "creator": stone_inst,
            },
            {
                "invite_code": "M150D",
                "title": "MATH150: Discrete Mathematics for CS",
                "description": "Mathematical structures for computer science: propositional logic, bitwise parity, modular arithmetic, and recurrence relations.",
                "creator": chen_inst,
            },
        ]

        courses: dict[str, Course] = {}
        for c_def in course_defs:
            c_res = await session.execute(
                select(Course).where(Course.invite_code == c_def["invite_code"])
            )
            c = c_res.scalar_one_or_none()
            if c is None:
                c = Course(
                    id=uuid.uuid4(),
                    title=c_def["title"],
                    description=c_def["description"],
                    created_by=c_def["creator"].id,
                    invite_code=c_def["invite_code"],
                )
                session.add(c)
                await session.flush()
                logger.info("Created course: %s (%s)", c.title, c.invite_code)
            else:
                c.title = c_def["title"]
                c.description = c_def["description"]
                c.created_by = c_def["creator"].id
                await session.flush()
            courses[c_def["invite_code"]] = c

        cs101 = courses["CS101A"]
        cs201 = courses["CS201B"]
        cs301 = courses["CS301C"]
        math150 = courses["M150D"]

        # ── 4. Enrollments ───────────────────────────────────────────────────
        # Setup course enrollments
        enrollment_plan = [
            # CS101: All instructors and all 12 students
            (cs101, admin_inst, "instructor"),
            (cs101, chen_inst, "instructor"),
            *[(cs101, st, "student") for st in students.values()],

            # CS201: Prof. Chen (instructor), 8 students
            (cs201, chen_inst, "instructor"),
            (cs201, admin_inst, "instructor"),
            *[(cs201, students[email], "student") for email in [
                "student@codeforge.local", "alice@codeforge.local", "bob@codeforge.local",
                "charlie@codeforge.local", "diana@codeforge.local", "evan@codeforge.local",
                "fiona@codeforge.local", "george@codeforge.local",
            ]],

            # CS301: Dr. Stone (instructor), 7 students
            (cs301, stone_inst, "instructor"),
            (cs301, admin_inst, "instructor"),
            *[(cs301, students[email], "student") for email in [
                "student@codeforge.local", "bob@codeforge.local", "diana@codeforge.local",
                "fiona@codeforge.local", "ian@codeforge.local", "julia@codeforge.local",
                "kevin@codeforge.local",
            ]],

            # MATH150: Prof. Chen (instructor), 6 students
            (math150, chen_inst, "instructor"),
            *[(math150, students[email], "student") for email in [
                "student@codeforge.local", "alice@codeforge.local", "charlie@codeforge.local",
                "hannah@codeforge.local", "ian@codeforge.local", "kevin@codeforge.local",
            ]],
        ]

        for course, user, role in enrollment_plan:
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
        logger.info("Enrollments populated across 4 courses.")

        # ── 5. Problems & Test Cases ─────────────────────────────────────────
        problems_def = [
            # ── CS101 Problems ──
            {
                "course": cs101,
                "creator": admin_inst,
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
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    char name[128];\n"
                    "    if (scanf(\"%127s\", name) == 1) {\n"
                    "        printf(\"Hello, %s!\\n\", name);\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    string name;\n"
                    "    if (cin >> name) {\n"
                    "        cout << \"Hello, \" << name << \"!\" << endl;\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "Alice\n", "expected_output": "Hello, Alice!", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "Bob\n", "expected_output": "Hello, Bob!", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "CodeForge\n", "expected_output": "Hello, CodeForge!", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
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
                    "        for (int i = 0; i < n; i++) {\n"
                    "            for (int j = i + 1; j < n; j++) {\n"
                    "                if (nums[i] + nums[j] == target) {\n"
                    "                    System.out.println(i + \" \" + j);\n"
                    "                    return;\n"
                    "                }\n"
                    "            }\n"
                    "        }\n"
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
                    "    lookup = {}\n"
                    "    for i, num in enumerate(nums):\n"
                    "        diff = target - num\n"
                    "        if diff in lookup:\n"
                    "            print(f\"{lookup[diff]} {i}\")\n"
                    "            return\n"
                    "        lookup[num] = i\n\n"
                    "if __name__ == '__main__':\n"
                    "    solve()\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int nums[1000];\n"
                    "    for (int i = 0; i < n; i++) scanf(\"%d\", &nums[i]);\n"
                    "    int target;\n"
                    "    scanf(\"%d\", &target);\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        for (int j = i + 1; j < n; j++) {\n"
                    "            if (nums[i] + nums[j] == target) {\n"
                    "                printf(\"%d %d\\n\", i, j);\n"
                    "                return 0;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "#include <unordered_map>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n; if (!(cin >> n)) return 0;\n"
                    "    vector<int> nums(n);\n"
                    "    for (int i = 0; i < n; i++) cin >> nums[i];\n"
                    "    int target; cin >> target;\n"
                    "    unordered_map<int, int> mp;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        int diff = target - nums[i];\n"
                    "        if (mp.count(diff)) {\n"
                    "            cout << mp[diff] << \" \" << i << endl;\n"
                    "            return 0;\n"
                    "        }\n"
                    "        mp[nums[i]] = i;\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "4\n2 7 11 15\n9\n", "expected_output": "0 1", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "3\n3 2 4\n6\n", "expected_output": "1 2", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "2\n3 3\n6\n", "expected_output": "0 1", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
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
                "starter_code_c": (
                    "#include <stdio.h>\n"
                    "#include <string.h>\n\n"
                    "int main() {\n"
                    "    char s[1024];\n"
                    "    if (fgets(s, sizeof(s), stdin)) {\n"
                    "        s[strcspn(s, \"\\r\\n\")] = 0;\n"
                    "        int len = strlen(s);\n"
                    "        for (int i = len - 1; i >= 0; i--) putchar(s[i]);\n"
                    "        putchar('\\n');\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    string s;\n"
                    "    if (getline(cin, s)) {\n"
                    "        reverse(s.begin(), s.end());\n"
                    "        cout << s << endl;\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "hello\n", "expected_output": "olleh", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "Antigravity\n", "expected_output": "ytivargitnA", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "racecar\n", "expected_output": "racecar", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
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
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) == 1) {\n"
                    "        for (int i = 1; i <= n; i++) {\n"
                    "            if (i % 15 == 0) printf(\"FizzBuzz\\n\");\n"
                    "            else if (i % 3 == 0) printf(\"Fizz\\n\");\n"
                    "            else if (i % 5 == 0) printf(\"Buzz\\n\");\n"
                    "            else printf(\"%d\\n\", i);\n"
                    "        }\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (cin >> n) {\n"
                    "        for (int i = 1; i <= n; i++) {\n"
                    "            if (i % 15 == 0) cout << \"FizzBuzz\\n\";\n"
                    "            else if (i % 3 == 0) cout << \"Fizz\\n\";\n"
                    "            else if (i % 5 == 0) cout << \"Buzz\\n\";\n"
                    "            else cout << i << \"\\n\";\n"
                    "        }\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "5\n", "expected_output": "1\n2\nFizz\n4\nBuzz", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "15\n", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", "is_visible": False, "order_index": 1},
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
                "slug": "palindrome-number",
                "title": "Palindrome Number",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an integer `x`, print `true` if `x` is a palindrome, and `false` otherwise.\n"
                    "An integer is a palindrome when it reads the same forward and backward (e.g. `121` is, while `-121` and `10` are not).\n\n"
                    "#### Example Input\n```\n121\n```\n#### Example Output\n```\ntrue\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        String s = sc.next();\n"
                    "        String rev = new StringBuilder(s).reverse().toString();\n"
                    "        System.out.println(s.equals(rev) && !s.startsWith(\"-\") ? \"true\" : \"false\");\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "s = sys.stdin.read().strip()\n"
                    "if s:\n"
                    "    print(\"true\" if s == s[::-1] and not s.startswith('-') else \"false\")\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n"
                    "#include <string.h>\n\n"
                    "int main() {\n"
                    "    char s[64];\n"
                    "    if (scanf(\"%63s\", s) == 1) {\n"
                    "        if (s[0] == '-') { printf(\"false\\n\"); return 0; }\n"
                    "        int l = 0, r = strlen(s) - 1;\n"
                    "        while (l < r) {\n"
                    "            if (s[l++] != s[r--]) { printf(\"false\\n\"); return 0; }\n"
                    "        }\n"
                    "        printf(\"true\\n\");\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    string s;\n"
                    "    if (cin >> s) {\n"
                    "        string rev = s;\n"
                    "        reverse(rev.begin(), rev.end());\n"
                    "        cout << (s == rev && s[0] != '-' ? \"true\" : \"false\") << endl;\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "121\n", "expected_output": "true", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "-121\n", "expected_output": "false", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "10\n", "expected_output": "false", "is_visible": False, "order_index": 2},
                ],
            },

            # ── CS201 Problems ──
            {
                "course": cs201,
                "creator": chen_inst,
                "slug": "valid-palindrome",
                "title": "Valid Palindrome",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.\n"
                    "Given a string `s`, print `true` if it is a palindrome, or `false` otherwise.\n\n"
                    "#### Example Input\n```\nA man, a plan, a canal: Panama\n```\n#### Example Output\n```\ntrue\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        String line = sc.hasNextLine() ? sc.nextLine() : \"\";\n"
                    "        StringBuilder clean = new StringBuilder();\n"
                    "        for (char c : line.toCharArray()) {\n"
                    "            if (Character.isLetterOrDigit(c)) clean.append(Character.toLowerCase(c));\n"
                    "        }\n"
                    "        String orig = clean.toString();\n"
                    "        String rev = clean.reverse().toString();\n"
                    "        System.out.println(orig.equals(rev) ? \"true\" : \"false\");\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "s = sys.stdin.read().strip()\n"
                    "clean = [c.lower() for c in s if c.isalnum()]\n"
                    "print(\"true\" if clean == clean[::-1] else \"false\")\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n"
                    "#include <ctype.h>\n"
                    "#include <string.h>\n\n"
                    "int main() {\n"
                    "    char buf[1024];\n"
                    "    if (fgets(buf, sizeof(buf), stdin)) {\n"
                    "        char clean[1024]; int k = 0;\n"
                    "        for (int i = 0; buf[i]; i++) {\n"
                    "            if (isalnum((unsigned char)buf[i])) clean[k++] = tolower((unsigned char)buf[i]);\n"
                    "        }\n"
                    "        clean[k] = 0;\n"
                    "        int l = 0, r = k - 1;\n"
                    "        while (l < r) {\n"
                    "            if (clean[l++] != clean[r--]) { printf(\"false\\n\"); return 0; }\n"
                    "        }\n"
                    "        printf(\"true\\n\");\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "#include <cctype>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    string s; getline(cin, s);\n"
                    "    string clean = \"\";\n"
                    "    for (char c : s) if (isalnum(c)) clean += tolower(c);\n"
                    "    string rev = clean;\n"
                    "    reverse(rev.begin(), rev.end());\n"
                    "    cout << (clean == rev ? \"true\" : \"false\") << endl;\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "A man, a plan, a canal: Panama\n", "expected_output": "true", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "race a car\n", "expected_output": "false", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "0P\n", "expected_output": "false", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs201,
                "creator": chen_inst,
                "slug": "binary-search",
                "title": "Binary Search",
                "difficulty": "medium",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an array of integers `nums` which is sorted in ascending order, and an integer `target`, write a function to search `target` in `nums`.\n"
                    "If `target` exists, then print its 0-based index. Otherwise, print `-1`.\n"
                    "You must write an algorithm with `O(log n)` runtime complexity.\n\n"
                    "#### Input\n"
                    "- First line: integer `n`\n"
                    "- Second line: `n` space-separated sorted integers\n"
                    "- Third line: integer `target`\n\n"
                    "#### Example Input\n```\n5\n1 3 5 7 9\n5\n```\n#### Example Output\n```\n2\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        int[] a = new int[n];\n"
                    "        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n"
                    "        int target = sc.nextInt();\n"
                    "        int l = 0, r = n - 1, ans = -1;\n"
                    "        while (l <= r) {\n"
                    "            int mid = l + (r - l) / 2;\n"
                    "            if (a[mid] == target) { ans = mid; break; }\n"
                    "            else if (a[mid] < target) l = mid + 1;\n"
                    "            else r = mid - 1;\n"
                    "        }\n"
                    "        System.out.println(ans);\n"
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
                    "    l, r = 0, n - 1\n"
                    "    ans = -1\n"
                    "    while l <= r:\n"
                    "        mid = (l + r) // 2\n"
                    "        if nums[mid] == target:\n"
                    "            ans = mid\n"
                    "            break\n"
                    "        elif nums[mid] < target:\n"
                    "            l = mid + 1\n"
                    "        else:\n"
                    "            r = mid - 1\n"
                    "    print(ans)\n\n"
                    "if __name__ == '__main__':\n"
                    "    solve()\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int a[20000];\n"
                    "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
                    "    int target; scanf(\"%d\", &target);\n"
                    "    int l = 0, r = n - 1, ans = -1;\n"
                    "    while (l <= r) {\n"
                    "        int mid = l + (r - l) / 2;\n"
                    "        if (a[mid] == target) { ans = mid; break; }\n"
                    "        else if (a[mid] < target) l = mid + 1;\n"
                    "        else r = mid - 1;\n"
                    "    }\n"
                    "    printf(\"%d\\n\", ans);\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n; if (!(cin >> n)) return 0;\n"
                    "    vector<int> a(n);\n"
                    "    for (int i = 0; i < n; i++) cin >> a[i];\n"
                    "    int target; cin >> target;\n"
                    "    int l = 0, r = n - 1, ans = -1;\n"
                    "    while (l <= r) {\n"
                    "        int mid = l + (r - l) / 2;\n"
                    "        if (a[mid] == target) { ans = mid; break; }\n"
                    "        else if (a[mid] < target) l = mid + 1;\n"
                    "        else r = mid - 1;\n"
                    "    }\n"
                    "    cout << ans << endl;\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "5\n1 3 5 7 9\n5\n", "expected_output": "2", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "5\n1 3 5 7 9\n2\n", "expected_output": "-1", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "1\n10\n10\n", "expected_output": "0", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs201,
                "creator": chen_inst,
                "slug": "merge-sorted-arrays",
                "title": "Merge Sorted Arrays",
                "difficulty": "medium",
                "description": (
                    "### Problem Statement\n\n"
                    "Given two sorted integer arrays `arr1` and `arr2`, merge them into a single sorted array and print the elements separated by space.\n\n"
                    "#### Input\n"
                    "- First line: `n` (length of `arr1`)\n"
                    "- Second line: `n` space-separated integers\n"
                    "- Third line: `m` (length of `arr2`)\n"
                    "- Fourth line: `m` space-separated integers\n\n"
                    "#### Example Input\n```\n3\n1 3 5\n3\n2 4 6\n```\n#### Example Output\n```\n1 2 3 4 5 6\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        int[] a = new int[n];\n"
                    "        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n"
                    "        int m = sc.nextInt();\n"
                    "        int[] b = new int[m];\n"
                    "        for (int i = 0; i < m; i++) b[i] = sc.nextInt();\n"
                    "        int i = 0, j = 0;\n"
                    "        StringBuilder sb = new StringBuilder();\n"
                    "        while (i < n && j < m) {\n"
                    "            if (a[i] <= b[j]) sb.append(a[i++]).append(\" \");\n"
                    "            else sb.append(b[j++]).append(\" \");\n"
                    "        }\n"
                    "        while (i < n) sb.append(a[i++]).append(\" \");\n"
                    "        while (j < m) sb.append(b[j++]).append(\" \");\n"
                    "        System.out.println(sb.toString().trim());\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "def solve():\n"
                    "    data = sys.stdin.read().split()\n"
                    "    if not data: return\n"
                    "    n = int(data[0])\n"
                    "    a = [int(x) for x in data[1:n+1]]\n"
                    "    m = int(data[n+1])\n"
                    "    b = [int(x) for x in data[n+2:n+2+m]]\n"
                    "    res = sorted(a + b)\n"
                    "    print(\" \".join(map(str, res)))\n\n"
                    "if __name__ == '__main__':\n"
                    "    solve()\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n; if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int a[1000]; for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
                    "    int m; scanf(\"%d\", &m);\n"
                    "    int b[1000]; for (int i = 0; i < m; i++) scanf(\"%d\", &b[i]);\n"
                    "    int i = 0, j = 0, first = 1;\n"
                    "    while (i < n && j < m) {\n"
                    "        if (!first) printf(\" \");\n"
                    "        first = 0;\n"
                    "        if (a[i] <= b[j]) printf(\"%d\", a[i++]);\n"
                    "        else printf(\"%d\", b[j++]);\n"
                    "    }\n"
                    "    while (i < n) { if (!first) printf(\" \"); printf(\"%d\", a[i++]); first = 0; }\n"
                    "    while (j < m) { if (!first) printf(\" \"); printf(\"%d\", b[j++]); first = 0; }\n"
                    "    printf(\"\\n\");\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n; if (!(cin >> n)) return 0;\n"
                    "    vector<int> a(n);\n"
                    "    for (int i = 0; i < n; i++) cin >> a[i];\n"
                    "    int m; cin >> m;\n"
                    "    vector<int> b(m);\n"
                    "    for (int i = 0; i < m; i++) cin >> b[i];\n"
                    "    vector<int> res(n + m);\n"
                    "    merge(a.begin(), a.end(), b.begin(), b.end(), res.begin());\n"
                    "    for (size_t i = 0; i < res.size(); i++) {\n"
                    "        cout << res[i] << (i + 1 == res.size() ? \"\" : \" \");\n"
                    "    }\n"
                    "    cout << endl;\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "3\n1 3 5\n3\n2 4 6\n", "expected_output": "1 2 3 4 5 6", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "2\n5 10\n1\n3\n", "expected_output": "3 5 10", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "1\n7\n1\n7\n", "expected_output": "7 7", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs201,
                "creator": chen_inst,
                "slug": "maximum-subarray",
                "title": "Maximum Subarray (Kadane's Algorithm)",
                "difficulty": "medium",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an integer array `nums`, find the subarray with the largest sum, and print its sum.\n"
                    "A subarray is a contiguous non-empty sequence of elements within an array.\n\n"
                    "#### Input\n"
                    "- First line: `n`\n"
                    "- Second line: `n` space-separated integers\n\n"
                    "#### Example Input\n```\n9\n-2 1 -3 4 -1 2 1 -5 4\n```\n#### Example Output\n```\n6\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        int maxSoFar = sc.nextInt(), curr = maxSoFar;\n"
                    "        for (int i = 1; i < n; i++) {\n"
                    "            int val = sc.nextInt();\n"
                    "            curr = Math.max(val, curr + val);\n"
                    "            maxSoFar = Math.max(maxSoFar, curr);\n"
                    "        }\n"
                    "        System.out.println(maxSoFar);\n"
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
                    "    max_so_far = curr = nums[0]\n"
                    "    for x in nums[1:]:\n"
                    "        curr = max(x, curr + x)\n"
                    "        max_so_far = max(max_so_far, curr)\n"
                    "    print(max_so_far)\n\n"
                    "if __name__ == '__main__':\n"
                    "    solve()\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n; if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int val; scanf(\"%d\", &val);\n"
                    "    int max_so_far = val, curr = val;\n"
                    "    for (int i = 1; i < n; i++) {\n"
                    "        scanf(\"%d\", &val);\n"
                    "        curr = (val > curr + val) ? val : curr + val;\n"
                    "        if (curr > max_so_far) max_so_far = curr;\n"
                    "    }\n"
                    "    printf(\"%d\\n\", max_so_far);\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n; if (!(cin >> n)) return 0;\n"
                    "    int val; cin >> val;\n"
                    "    int max_so_far = val, curr = val;\n"
                    "    for (int i = 1; i < n; i++) {\n"
                    "        cin >> val;\n"
                    "        curr = max(val, curr + val);\n"
                    "        max_so_far = max(max_so_far, curr);\n"
                    "    }\n"
                    "    cout << max_so_far << endl;\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "9\n-2 1 -3 4 -1 2 1 -5 4\n", "expected_output": "6", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "1\n1\n", "expected_output": "1", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "5\n5 4 -1 7 8\n", "expected_output": "23", "is_visible": False, "order_index": 2},
                ],
            },

            # ── CS301 / MATH150 Problems ──
            {
                "course": cs301,
                "creator": stone_inst,
                "slug": "bitwise-parity",
                "title": "Bitwise Parity Calculation",
                "difficulty": "easy",
                "description": (
                    "### Problem Statement\n\n"
                    "Given a single 32-bit non-negative integer `N`, determine its parity.\n"
                    "The parity is `1` if the number of 1s in the binary representation of `N` is odd, and `0` if even.\n\n"
                    "#### Example Input\n```\n5\n```\n#### Example Output\n```\n0\n```\n*(5 in binary is 101, which has two 1s -> even parity -> 0)*"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        long n = sc.nextLong();\n"
                    "        int count = Long.bitCount(n);\n"
                    "        System.out.println(count % 2 == 1 ? 1 : 0);\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "data = sys.stdin.read().strip()\n"
                    "if data:\n"
                    "    n = int(data)\n"
                    "    parity = bin(n).count('1') % 2\n"
                    "    print(parity)\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    unsigned int n;\n"
                    "    if (scanf(\"%u\", &n) == 1) {\n"
                    "        int count = 0;\n"
                    "        while (n) { count ^= (n & 1); n >>= 1; }\n"
                    "        printf(\"%d\\n\", count);\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    unsigned int n;\n"
                    "    if (cin >> n) {\n"
                    "        int count = 0;\n"
                    "        while (n) { count ^= (n & 1); n >>= 1; }\n"
                    "        cout << count << endl;\n"
                    "    }\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "5\n", "expected_output": "0", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "7\n", "expected_output": "1", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "0\n", "expected_output": "0", "is_visible": False, "order_index": 2},
                ],
            },
            {
                "course": cs301,
                "creator": stone_inst,
                "slug": "pointer-swap-reverse",
                "title": "In-Place Array Traversal & Reversal",
                "difficulty": "medium",
                "description": (
                    "### Problem Statement\n\n"
                    "Given an array of `n` integers, reverse the array in place and print the resulting elements separated by spaces.\n\n"
                    "#### Input\n"
                    "- First line: `n`\n"
                    "- Second line: `n` space-separated integers\n\n"
                    "#### Example Input\n```\n4\n10 20 30 40\n```\n#### Example Output\n```\n40 30 20 10\n```"
                ),
                "starter_code_java": (
                    "import java.util.Scanner;\n\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        int n = sc.nextInt();\n"
                    "        int[] a = new int[n];\n"
                    "        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n"
                    "        for (int i = 0; i < n / 2; i++) {\n"
                    "            int tmp = a[i]; a[i] = a[n - 1 - i]; a[n - 1 - i] = tmp;\n"
                    "        }\n"
                    "        for (int i = 0; i < n; i++) {\n"
                    "            System.out.print(a[i] + (i + 1 == n ? \"\" : \" \"));\n"
                    "        }\n"
                    "        System.out.println();\n"
                    "    }\n"
                    "}\n"
                ),
                "starter_code_python": (
                    "import sys\n\n"
                    "data = sys.stdin.read().split()\n"
                    "if data:\n"
                    "    n = int(data[0])\n"
                    "    nums = data[1:n+1]\n"
                    "    nums.reverse()\n"
                    "    print(\" \".join(nums))\n"
                ),
                "starter_code_c": (
                    "#include <stdio.h>\n\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int a[1000];\n"
                    "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
                    "    int *p1 = a, *p2 = a + n - 1;\n"
                    "    while (p1 < p2) {\n"
                    "        int tmp = *p1; *p1 = *p2; *p2 = tmp;\n"
                    "        p1++; p2--;\n"
                    "    }\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        printf(\"%d%s\", a[i], (i + 1 == n ? \"\" : \" \"));\n"
                    "    }\n"
                    "    printf(\"\\n\");\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "starter_code_cpp": (
                    "#include <iostream>\n"
                    "#include <vector>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n\n"
                    "int main() {\n"
                    "    int n; if (!(cin >> n)) return 0;\n"
                    "    vector<int> a(n);\n"
                    "    for (int i = 0; i < n; i++) cin >> a[i];\n"
                    "    reverse(a.begin(), a.end());\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        cout << a[i] << (i + 1 == n ? \"\" : \" \");\n"
                    "    }\n"
                    "    cout << endl;\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "test_cases": [
                    {"label": "01", "input_data": "4\n10 20 30 40\n", "expected_output": "40 30 20 10", "is_visible": True, "order_index": 0},
                    {"label": "02", "input_data": "3\n1 2 3\n", "expected_output": "3 2 1", "is_visible": True, "order_index": 1},
                    {"label": "03", "input_data": "1\n99\n", "expected_output": "99", "is_visible": False, "order_index": 2},
                ],
            },
        ]

        problem_map: dict[str, Problem] = {}
        for p_def in problems_def:
            prob_res = await session.execute(
                select(Problem).where(Problem.slug == p_def["slug"])
            )
            prob = prob_res.scalar_one_or_none()
            if prob is None:
                prob = Problem(
                    id=uuid.uuid4(),
                    course_id=p_def["course"].id,
                    created_by=p_def["creator"].id,
                    slug=p_def["slug"],
                    title=p_def["title"],
                    description=p_def["description"],
                    difficulty=p_def["difficulty"],
                    starter_code_java=p_def["starter_code_java"],
                    starter_code_python=p_def["starter_code_python"],
                    starter_code_c=p_def.get("starter_code_c"),
                    starter_code_cpp=p_def.get("starter_code_cpp"),
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
                prob.course_id = p_def["course"].id
                prob.created_by = p_def["creator"].id
                prob.starter_code_c = p_def.get("starter_code_c")
                prob.starter_code_cpp = p_def.get("starter_code_cpp")
                await session.flush()

                # Ensure test cases exist
                tc_chk = await session.execute(
                    select(func.count(TestCase.id)).where(TestCase.problem_id == prob.id)
                )
                if (tc_chk.scalar() or 0) == 0:
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

            problem_map[p_def["slug"]] = prob
        await session.flush()
        logger.info("Problems catalog populated with %d items.", len(problem_map))

        # ── 6. Lab Sessions Across Courses ───────────────────────────────────
        now = datetime.now(timezone.utc)
        lab_defs = [
            {
                "course": cs101,
                "title": "Lab 1: Programming Basics & Warm-up",
                "description": "Introductory lab session covering I/O, arithmetic, string manipulation, and control flow in Java, Python, C, and C++.",
                "starts_at": now - timedelta(hours=2),
                "ends_at": now + timedelta(days=7),
                "mandatory_count": 1,
                "is_active": True,
                "problem_slugs": ["hello-world", "two-sum", "reverse-string", "fizzbuzz", "palindrome-number"],
            },
            {
                "course": cs201,
                "title": "Lab 2: Searching & Pointer Invariants",
                "description": "Practical laboratory on divide-and-conquer searching and two-pointer array manipulation techniques.",
                "starts_at": now - timedelta(hours=1),
                "ends_at": now + timedelta(days=5),
                "mandatory_count": 2,
                "is_active": True,
                "problem_slugs": ["valid-palindrome", "binary-search", "merge-sorted-arrays", "maximum-subarray"],
            },
            {
                "course": cs301,
                "title": "Lab 3: C/C++ Memory & Bitwise Lab",
                "description": "Practical exercises focusing on bit-level manipulation, memory layouts, and pointer traversal mechanics.",
                "starts_at": now - timedelta(hours=3),
                "ends_at": now + timedelta(days=6),
                "mandatory_count": 1,
                "is_active": True,
                "problem_slugs": ["bitwise-parity", "pointer-swap-reverse"],
            },
            {
                "course": cs101,
                "title": "Lab 0: Diagnostic Orientation",
                "description": "Pre-course baseline diagnostics to calibrate environment readiness and compiler output verification.",
                "starts_at": now - timedelta(days=14),
                "ends_at": now - timedelta(days=7),
                "mandatory_count": 1,
                "is_active": False,
                "problem_slugs": ["hello-world"],
            },
        ]

        labs: dict[str, LabSession] = {}
        for l_def in lab_defs:
            l_res = await session.execute(
                select(LabSession).where(
                    LabSession.course_id == l_def["course"].id,
                    LabSession.title == l_def["title"],
                )
            )
            lab = l_res.scalar_one_or_none()
            if lab is None:
                lab = LabSession(
                    id=uuid.uuid4(),
                    course_id=l_def["course"].id,
                    title=l_def["title"],
                    description=l_def["description"],
                    starts_at=l_def["starts_at"],
                    ends_at=l_def["ends_at"],
                    mandatory_count=l_def["mandatory_count"],
                    is_active=l_def["is_active"],
                )
                session.add(lab)
                await session.flush()
                logger.info("Created lab session: %s", lab.title)
            else:
                lab.is_active = l_def["is_active"]
                lab.mandatory_count = l_def["mandatory_count"]
                lab.ends_at = l_def["ends_at"]
                await session.flush()

            labs[l_def["title"]] = lab

            # Link problems to lab
            for idx, slug in enumerate(l_def["problem_slugs"]):
                if slug in problem_map:
                    p = problem_map[slug]
                    lsp_res = await session.execute(
                        select(LabSessionProblem).where(
                            LabSessionProblem.lab_session_id == lab.id,
                            LabSessionProblem.problem_id == p.id,
                        )
                    )
                    if lsp_res.scalar_one_or_none() is None:
                        session.add(
                            LabSessionProblem(
                                id=uuid.uuid4(),
                                lab_session_id=lab.id,
                                problem_id=p.id,
                                order_index=idx,
                            )
                        )
        await session.flush()
        logger.info("Lab sessions linked to respective problems.")

        # ── 7. Seed Submissions & Badges Across Students ─────────────────────
        # For repeatable presentations: reset Alex Student's extra demo submissions & badges
        # so Alex Student can earn a badge live during demonstrations!
        lab1 = labs["Lab 1: Programming Basics & Warm-up"]
        lab2 = labs["Lab 2: Searching & Pointer Invariants"]
        lab3 = labs["Lab 3: C/C++ Memory & Bitwise Lab"]

        alex_user = students["student@codeforge.local"]
        alex_extra_pids = [
            problem_map[s].id
            for s in ["two-sum", "reverse-string", "fizzbuzz", "palindrome-number"]
            if s in problem_map
        ]
        await session.execute(
            delete(Badge).where(
                Badge.user_id == alex_user.id,
                Badge.lab_session_id.in_([lab1.id, lab2.id, lab3.id]),
            )
        )
        await session.execute(
            delete(Submission).where(
                Submission.user_id == alex_user.id,
                Submission.problem_id.in_(alex_extra_pids),
            )
        )

        # Plan rich student solves for Lab 1 (CS101):
        # Mandatory count = 1. Beyond 1 earns badges!
        lab1_solves = {
            "diana@codeforge.local": ["hello-world", "two-sum", "reverse-string", "fizzbuzz", "palindrome-number"],  # 5 solved -> 4 badges (Rank 1)
            "alice@codeforge.local": ["hello-world", "two-sum", "reverse-string", "fizzbuzz"],                       # 4 solved -> 3 badges (Rank 2)
            "bob@codeforge.local": ["hello-world", "two-sum", "reverse-string"],                                      # 3 solved -> 2 badges (Rank 3)
            "evan@codeforge.local": ["hello-world", "two-sum"],                                                       # 2 solved -> 1 badge
            "fiona@codeforge.local": ["hello-world", "fizzbuzz"],                                                     # 2 solved -> 1 badge
            "kevin@codeforge.local": ["hello-world", "reverse-string"],                                               # 2 solved -> 1 badge
            "charlie@codeforge.local": ["hello-world"],                                                               # 1 solved -> 0 badges (baseline)
            "hannah@codeforge.local": ["hello-world"],                                                                # 1 solved -> 0 badges
            "ian@codeforge.local": ["hello-world"],                                                                   # 1 solved -> 0 badges
            "julia@codeforge.local": ["hello-world"],                                                                 # 1 solved -> 0 badges
            "student@codeforge.local": ["hello-world"],                                                               # 1 solved -> 0 badges (ready for live demo!)
        }

        for email, solved_slugs in lab1_solves.items():
            u = students[email]
            for order, slug in enumerate(solved_slugs):
                prob = problem_map[slug]
                sub_res = await session.execute(
                    select(Submission).where(
                        Submission.user_id == u.id,
                        Submission.problem_id == prob.id,
                        Submission.lab_session_id == lab1.id,
                    )
                )
                if sub_res.scalar_one_or_none() is None:
                    session.add(
                        Submission(
                            id=uuid.uuid4(),
                            problem_id=prob.id,
                            user_id=u.id,
                            lab_session_id=lab1.id,
                            language="python" if order % 2 == 0 else "java",
                            source_code=prob.starter_code_python or prob.starter_code_java or "# Solved",
                            status="completed",
                            score=100,
                            total_cases=3,
                            passed_cases=3,
                            is_full_submit=True,
                            results_json=[],
                            execution_time_ms=35 + order * 5,
                            submitted_at=now - timedelta(minutes=(120 - order * 15)),
                        )
                    )

                if order >= lab1.mandatory_count:
                    badge_res = await session.execute(
                        select(Badge).where(
                            Badge.user_id == u.id,
                            Badge.lab_session_id == lab1.id,
                            Badge.problem_id == prob.id,
                        )
                    )
                    if badge_res.scalar_one_or_none() is None:
                        session.add(
                            Badge(
                                id=uuid.uuid4(),
                                user_id=u.id,
                                lab_session_id=lab1.id,
                                problem_id=prob.id,
                                earned_at=now - timedelta(minutes=(120 - order * 15)),
                            )
                        )

        # Lab 2 (CS201): mandatory_count = 2
        lab2_solves = {
            "diana@codeforge.local": ["valid-palindrome", "binary-search", "merge-sorted-arrays", "maximum-subarray"], # 4 solved -> 2 badges
            "alice@codeforge.local": ["valid-palindrome", "binary-search", "merge-sorted-arrays"],                     # 3 solved -> 1 badge
            "evan@codeforge.local": ["valid-palindrome", "binary-search"],                                             # 2 solved -> 0 badges (baseline)
            "george@codeforge.local": ["valid-palindrome", "binary-search"],                                           # 2 solved -> 0 badges
        }
        for email, solved_slugs in lab2_solves.items():
            u = students[email]
            for order, slug in enumerate(solved_slugs):
                prob = problem_map[slug]
                sub_res = await session.execute(
                    select(Submission).where(
                        Submission.user_id == u.id,
                        Submission.problem_id == prob.id,
                        Submission.lab_session_id == lab2.id,
                    )
                )
                if sub_res.scalar_one_or_none() is None:
                    session.add(
                        Submission(
                            id=uuid.uuid4(),
                            problem_id=prob.id,
                            user_id=u.id,
                            lab_session_id=lab2.id,
                            language="cpp" if order % 2 == 1 else "python",
                            source_code=prob.starter_code_cpp or prob.starter_code_python or "// Solved",
                            status="completed",
                            score=100,
                            total_cases=3,
                            passed_cases=3,
                            is_full_submit=True,
                            results_json=[],
                            execution_time_ms=28 + order * 4,
                            submitted_at=now - timedelta(minutes=(90 - order * 12)),
                        )
                    )

                if order >= lab2.mandatory_count:
                    b_chk = await session.execute(
                        select(Badge).where(
                            Badge.user_id == u.id,
                            Badge.lab_session_id == lab2.id,
                            Badge.problem_id == prob.id,
                        )
                    )
                    if b_chk.scalar_one_or_none() is None:
                        session.add(
                            Badge(
                                id=uuid.uuid4(),
                                user_id=u.id,
                                lab_session_id=lab2.id,
                                problem_id=prob.id,
                                earned_at=now - timedelta(minutes=(90 - order * 12)),
                            )
                        )

        # Lab 3 (CS301): mandatory_count = 1
        lab3_solves = {
            "kevin@codeforge.local": ["bitwise-parity", "pointer-swap-reverse"], # 2 solved -> 1 badge
            "ian@codeforge.local": ["bitwise-parity"],                           # 1 solved -> 0 badges
        }
        for email, solved_slugs in lab3_solves.items():
            u = students[email]
            for order, slug in enumerate(solved_slugs):
                prob = problem_map[slug]
                sub_res = await session.execute(
                    select(Submission).where(
                        Submission.user_id == u.id,
                        Submission.problem_id == prob.id,
                        Submission.lab_session_id == lab3.id,
                    )
                )
                if sub_res.scalar_one_or_none() is None:
                    session.add(
                        Submission(
                            id=uuid.uuid4(),
                            problem_id=prob.id,
                            user_id=u.id,
                            lab_session_id=lab3.id,
                            language="c",
                            source_code=prob.starter_code_c or "/* Solved */",
                            status="completed",
                            score=100,
                            total_cases=3,
                            passed_cases=3,
                            is_full_submit=True,
                            results_json=[],
                            execution_time_ms=18,
                            submitted_at=now - timedelta(minutes=(50 - order * 10)),
                        )
                    )

                if order >= lab3.mandatory_count:
                    b_chk = await session.execute(
                        select(Badge).where(
                            Badge.user_id == u.id,
                            Badge.lab_session_id == lab3.id,
                            Badge.problem_id == prob.id,
                        )
                    )
                    if b_chk.scalar_one_or_none() is None:
                        session.add(
                            Badge(
                                id=uuid.uuid4(),
                                user_id=u.id,
                                lab_session_id=lab3.id,
                                problem_id=prob.id,
                                earned_at=now - timedelta(minutes=(50 - order * 10)),
                            )
                        )
        await session.flush()
        logger.info("Submissions & Badges successfully seeded.")

        # ── 8. Learning Modules & Contents Across Courses ────────────────────
        module_specs = [
            # CS101 Modules
            {
                "course": cs101,
                "creator": admin_inst,
                "title": "Module 1: Introduction to Python & Algorithms",
                "description": "Foundations of dynamic typing, object references, and standard input/output programs.",
                "order_index": 1,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Understanding Python Variables & Memory Model",
                        "body": (
                            "## Variables in Python\n\n"
                            "In Python, variables are references to objects in memory, not direct memory addresses.\n\n"
                            "### Key Principles:\n"
                            "- **Dynamic Typing:** You do not declare types explicitly. Types are bound at runtime.\n"
                            "- **First-Class Objects:** Functions, numbers, and classes are all first-class objects.\n"
                            "- **Pass-by-Object-Reference:** Arguments to functions bind references to caller objects."
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "video",
                        "title": "Python Control Flow & Functions Masterclass",
                        "body": "https://www.youtube.com/watch?v=kqtD5dpn9C8",
                        "problem_slug": None,
                        "order_index": 2,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: Hello World & Stdin Basics",
                        "body": "Apply basic stdin reading and output formatting with the standard Hello World exercise.",
                        "problem_slug": "hello-world",
                        "order_index": 3,
                    },
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
                "title": "Module 2: Algorithmic Thinking & Control Flow",
                "description": "Conditional branching, loop invariants, and algorithmic complexity trade-offs.",
                "order_index": 2,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Branching Invariants & Edge Case Handling",
                        "body": (
                            "## Writing Resilient Conditionals\n\n"
                            "When implementing competitive programming algorithms:\n"
                            "1. Check constraints and boundary conditions (empty input, negative values).\n"
                            "2. Order conditions from most restrictive to least restrictive.\n"
                            "3. Keep predicates pure and side-effect free."
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "video",
                        "title": "Loops, Comprehensions, and Invariants",
                        "body": "https://www.youtube.com/watch?v=6iF8Xb7Z3wQ",
                        "problem_slug": None,
                        "order_index": 2,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: FizzBuzz Logic",
                        "body": "Implement classical 3/5 division logic handling overlapping multiples of 15.",
                        "problem_slug": "fizzbuzz",
                        "order_index": 3,
                    },
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
                "title": "Module 3: String Mechanics & Reversal",
                "description": "Character encoding, UTF-8 buffers, two-pointer string traversal, and palindromes.",
                "order_index": 3,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Two-Pointer Invariants on Strings",
                        "body": (
                            "## Symmetrical Invariants\n\n"
                            "A string reversal or palindrome check can be performed with two pointers meeting in the middle:\n"
                            "```python\n"
                            "l, r = 0, len(s) - 1\n"
                            "while l < r:\n"
                            "    if s[l] != s[r]: return False\n"
                            "    l += 1; r -= 1\n"
                            "return True\n"
                            "```"
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: Reverse a String",
                        "body": "Reverse input text using standard stream techniques.",
                        "problem_slug": "reverse-string",
                        "order_index": 2,
                    },
                ],
            },

            # CS201 Modules
            {
                "course": cs201,
                "creator": chen_inst,
                "title": "Module 1: Asymptotic Analysis & Binary Search",
                "description": "Logarithmic time complexity, loop invariants, and boundary correctness.",
                "order_index": 1,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Binary Search Invariants & Midpoint Overflow",
                        "body": (
                            "## The Invariant of Binary Search\n\n"
                            "Always maintain: `target` is in `a[l..r]`. When dividing:\n"
                            "Use `mid = l + (r - l) // 2` to prevent 32-bit signed integer overflow."
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "video",
                        "title": "Binary Search: 101 to Advanced Patterns",
                        "body": "https://www.youtube.com/watch?v=fDKIpRe8GW4",
                        "problem_slug": None,
                        "order_index": 2,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: Binary Search Implementation",
                        "body": "Find target index in O(log n) time.",
                        "problem_slug": "binary-search",
                        "order_index": 3,
                    },
                ],
            },
            {
                "course": cs201,
                "creator": chen_inst,
                "title": "Module 2: Divide & Conquer and Subarray Invariants",
                "description": "Array merging, contiguous subarray bounds, and Kadane's optimal theorem.",
                "order_index": 2,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Kadane's Algorithm: Dynamic Programming in O(1) Space",
                        "body": (
                            "## Maximum Subarray Sum\n\n"
                            "At each element `i`, the maximum subarray ending at `i` is:\n"
                            "`curr = max(nums[i], curr + nums[i])`\n"
                            "This reduces an O(n^2) brute force search into a single linear pass!"
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: Merge Sorted Arrays",
                        "body": "Combine two ascending arrays in linear time.",
                        "problem_slug": "merge-sorted-arrays",
                        "order_index": 2,
                    },
                ],
            },

            # CS301 Module
            {
                "course": cs301,
                "creator": stone_inst,
                "title": "Module 1: Computer Architecture & Bitwise Logic",
                "description": "Binary representations, bit masks, two's complement, and CPU ALU operations.",
                "order_index": 1,
                "is_published": True,
                "contents": [
                    {
                        "content_type": "text",
                        "title": "Fast Bit Manipulation Techniques",
                        "body": (
                            "## Essential Bitwise Tricks\n\n"
                            "- `n & (n - 1)` clears the lowest set bit.\n"
                            "- `n & -n` isolates the lowest set bit.\n"
                            "- `x ^ x = 0`, while `x ^ 0 = x`."
                        ),
                        "problem_slug": None,
                        "order_index": 1,
                    },
                    {
                        "content_type": "problem",
                        "title": "Practice: Bitwise Parity Calculation",
                        "body": "Compute parity of 32-bit integer in constant operations.",
                        "problem_slug": "bitwise-parity",
                        "order_index": 2,
                    },
                ],
            },
        ]

        seeded_modules = []
        for m_spec in module_specs:
            mod_res = await session.execute(
                select(LearningModule).where(
                    LearningModule.course_id == m_spec["course"].id,
                    LearningModule.title == m_spec["title"],
                )
            )
            mod = mod_res.scalar_one_or_none()
            if mod is None:
                mod = LearningModule(
                    id=uuid.uuid4(),
                    course_id=m_spec["course"].id,
                    title=m_spec["title"],
                    description=m_spec["description"],
                    order_index=m_spec["order_index"],
                    is_published=m_spec["is_published"],
                    created_by=m_spec["creator"].id,
                )
                session.add(mod)
                await session.flush()
                logger.info("Created learning module: %s", mod.title)
            seeded_modules.append(mod)

            for c_spec in m_spec["contents"]:
                cnt_res = await session.execute(
                    select(LearningContent).where(
                        LearningContent.module_id == mod.id,
                        LearningContent.title == c_spec["title"],
                    )
                )
                if cnt_res.scalar_one_or_none() is None:
                    linked_prob_id = None
                    if c_spec["problem_slug"] and c_spec["problem_slug"] in problem_map:
                        linked_prob_id = problem_map[c_spec["problem_slug"]].id

                    cnt = LearningContent(
                        id=uuid.uuid4(),
                        module_id=mod.id,
                        content_type=c_spec["content_type"],
                        title=c_spec["title"],
                        body=c_spec["body"],
                        problem_id=linked_prob_id,
                        order_index=c_spec["order_index"],
                    )
                    session.add(cnt)

        # Pre-seed student progress on modules
        if seeded_modules:
            for mod in seeded_modules:
                for student_email in ["diana@codeforge.local", "alice@codeforge.local"]:
                    u = students[student_email]
                    prog_chk = await session.execute(
                        select(ModuleProgress).where(
                            ModuleProgress.module_id == mod.id,
                            ModuleProgress.user_id == u.id,
                        )
                    )
                    if prog_chk.scalar_one_or_none() is None:
                        session.add(
                            ModuleProgress(
                                id=uuid.uuid4(),
                                module_id=mod.id,
                                user_id=u.id,
                                is_completed=True,
                                completed_at=now - timedelta(hours=3),
                            )
                        )
        await session.flush()
        logger.info("Learning modules & progress seeded.")

        # ── 9. Proctored Exams Across Courses ────────────────────────────────
        exam_defs = [
            {
                "course": cs101,
                "creator": admin_inst,
                "title": "CS101 Midterm Proctored Assessment",
                "description": "Comprehensive proctored assessment covering programming fundamentals and problem solving in a browser lockdown environment.",
                "duration_minutes": 60,
                "starts_at": now - timedelta(hours=3),
                "ends_at": now + timedelta(days=2),
                "is_active": True,
                "fullscreen_required": True,
                "tab_switch_limit": 3,
                "copy_paste_blocked": True,
                "problems": [
                    ("hello-world", 40, 0),
                    ("two-sum", 60, 1),
                ],
            },
            {
                "course": cs101,
                "creator": admin_inst,
                "title": "CS101 Final Assessment: Problem Solving Mastery",
                "description": "Scheduled comprehensive final examination testing algorithmic problem solving and memory model mastery.",
                "duration_minutes": 90,
                "starts_at": now + timedelta(days=3),
                "ends_at": now + timedelta(days=5),
                "is_active": True,
                "fullscreen_required": True,
                "tab_switch_limit": 3,
                "copy_paste_blocked": True,
                "problems": [
                    ("reverse-string", 30, 0),
                    ("fizzbuzz", 30, 1),
                    ("palindrome-number", 40, 2),
                ],
            },
            {
                "course": cs201,
                "creator": chen_inst,
                "title": "CS201 Midterm: Algorithmic Efficiency & Searching",
                "description": "Strict proctored assessment focusing on asymptotic bounds, binary search variants, and two-pointer arrays.",
                "duration_minutes": 75,
                "starts_at": now - timedelta(hours=2),
                "ends_at": now + timedelta(days=3),
                "is_active": True,
                "fullscreen_required": True,
                "tab_switch_limit": 2,
                "copy_paste_blocked": True,
                "problems": [
                    ("valid-palindrome", 30, 0),
                    ("binary-search", 35, 1),
                    ("merge-sorted-arrays", 35, 2),
                ],
            },
            {
                "course": cs301,
                "creator": stone_inst,
                "title": "CS301 Practical Systems Exam: Memory & Bitwise Ops",
                "description": "Hands-on low-level systems exam evaluating pointer arithmetic and bit manipulation routines in C/C++.",
                "duration_minutes": 90,
                "starts_at": now - timedelta(hours=1),
                "ends_at": now + timedelta(days=2),
                "is_active": True,
                "fullscreen_required": True,
                "tab_switch_limit": 2,
                "copy_paste_blocked": True,
                "problems": [
                    ("bitwise-parity", 50, 0),
                    ("pointer-swap-reverse", 50, 1),
                ],
            },
        ]

        exams: dict[str, Exam] = {}
        for e_spec in exam_defs:
            exam_chk = await session.execute(
                select(Exam).where(
                    Exam.course_id == e_spec["course"].id,
                    Exam.title == e_spec["title"],
                )
            )
            exam = exam_chk.scalar_one_or_none()
            if exam is None:
                exam = Exam(
                    id=uuid.uuid4(),
                    course_id=e_spec["course"].id,
                    title=e_spec["title"],
                    description=e_spec["description"],
                    duration_minutes=e_spec["duration_minutes"],
                    starts_at=e_spec["starts_at"],
                    ends_at=e_spec["ends_at"],
                    is_active=e_spec["is_active"],
                    fullscreen_required=e_spec["fullscreen_required"],
                    tab_switch_limit=e_spec["tab_switch_limit"],
                    copy_paste_blocked=e_spec["copy_paste_blocked"],
                    created_by=e_spec["creator"].id,
                )
                session.add(exam)
                await session.flush()
                logger.info("Created exam: %s", exam.title)
            else:
                exam.is_active = e_spec["is_active"]
                exam.duration_minutes = e_spec["duration_minutes"]
                exam.ends_at = e_spec["ends_at"]
                await session.flush()

            exams[e_spec["title"]] = exam

            for p_slug, weight, order_idx in e_spec["problems"]:
                if p_slug in problem_map:
                    p = problem_map[p_slug]
                    ep_chk = await session.execute(
                        select(ExamProblem).where(
                            ExamProblem.exam_id == exam.id,
                            ExamProblem.problem_id == p.id,
                        )
                    )
                    if ep_chk.scalar_one_or_none() is None:
                        session.add(
                            ExamProblem(
                                id=uuid.uuid4(),
                                exam_id=exam.id,
                                problem_id=p.id,
                                order_index=order_idx,
                                weight=weight,
                            )
                        )
        await session.flush()

        # ── 10. Pre-seed Exam Sessions & Anti-Cheat Violations ───────────────
        midterm101 = exams["CS101 Midterm Proctored Assessment"]

        # Ensure student@codeforge.local has NO session so user can take the exam live!
        await session.execute(
            delete(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == alex_user.id,
            )
        )

        # Diana: Completed, 100%, 0 violations
        diana_user = students["diana@codeforge.local"]
        diana_sess_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == diana_user.id,
            )
        )
        if diana_sess_chk.scalar_one_or_none() is None:
            session.add(
                ExamSession(
                    id=uuid.uuid4(),
                    exam_id=midterm101.id,
                    user_id=diana_user.id,
                    started_at=now - timedelta(minutes=90),
                    submitted_at=now - timedelta(minutes=40),
                    is_auto_submitted=False,
                    total_score=100,
                )
            )

        # Alice: Completed, 100%, 1 violation (tab switch)
        alice_user = students["alice@codeforge.local"]
        alice_sess_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == alice_user.id,
            )
        )
        if alice_sess_chk.scalar_one_or_none() is None:
            alice_sess = ExamSession(
                id=uuid.uuid4(),
                exam_id=midterm101.id,
                user_id=alice_user.id,
                started_at=now - timedelta(minutes=75),
                submitted_at=now - timedelta(minutes=30),
                is_auto_submitted=False,
                total_score=100,
            )
            session.add(alice_sess)
            await session.flush()

            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=alice_sess.id,
                    violation_type="tab_switch",
                    details="Switched tab away for 4 seconds",
                    occurred_at=now - timedelta(minutes=60),
                )
            )

        # Fiona: Completed, 100%, 2 violations (desktop_blur and focus_loss)
        fiona_user = students["fiona@codeforge.local"]
        fiona_sess_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == fiona_user.id,
            )
        )
        if fiona_sess_chk.scalar_one_or_none() is None:
            fiona_sess = ExamSession(
                id=uuid.uuid4(),
                exam_id=midterm101.id,
                user_id=fiona_user.id,
                started_at=now - timedelta(minutes=80),
                submitted_at=now - timedelta(minutes=35),
                is_auto_submitted=False,
                total_score=100,
            )
            session.add(fiona_sess)
            await session.flush()

            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=fiona_sess.id,
                    violation_type="focus_loss",
                    details="Window blur detected (switched desktop workspace)",
                    occurred_at=now - timedelta(minutes=65),
                )
            )
            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=fiona_sess.id,
                    violation_type="copy_paste",
                    details="Attempted clipboard paste in code editor",
                    occurred_at=now - timedelta(minutes=50),
                )
            )

        # Evan: Completed, 40%, 0 violations
        evan_user = students["evan@codeforge.local"]
        evan_sess_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == evan_user.id,
            )
        )
        if evan_sess_chk.scalar_one_or_none() is None:
            session.add(
                ExamSession(
                    id=uuid.uuid4(),
                    exam_id=midterm101.id,
                    user_id=evan_user.id,
                    started_at=now - timedelta(minutes=70),
                    submitted_at=now - timedelta(minutes=25),
                    is_auto_submitted=False,
                    total_score=40,
                )
            )

        # Bob: In progress, 2 violations (tab switch & fullscreen exit)
        bob_user = students["bob@codeforge.local"]
        bob_sess_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm101.id,
                ExamSession.user_id == bob_user.id,
            )
        )
        if bob_sess_chk.scalar_one_or_none() is None:
            bob_sess = ExamSession(
                id=uuid.uuid4(),
                exam_id=midterm101.id,
                user_id=bob_user.id,
                started_at=now - timedelta(minutes=20),
                submitted_at=None,
                is_auto_submitted=False,
                total_score=None,
            )
            session.add(bob_sess)
            await session.flush()

            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=bob_sess.id,
                    violation_type="tab_switch",
                    details="Switched to external browser tab",
                    occurred_at=now - timedelta(minutes=15),
                )
            )
            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=bob_sess.id,
                    violation_type="fullscreen_exit",
                    details="Exited fullscreen lockdown mode",
                    occurred_at=now - timedelta(minutes=10),
                )
            )

        # CS201 Midterm session: Diana & George
        midterm201 = exams["CS201 Midterm: Algorithmic Efficiency & Searching"]
        george_user = students["george@codeforge.local"]
        g_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == midterm201.id,
                ExamSession.user_id == george_user.id,
            )
        )
        if g_chk.scalar_one_or_none() is None:
            g_sess = ExamSession(
                id=uuid.uuid4(),
                exam_id=midterm201.id,
                user_id=george_user.id,
                started_at=now - timedelta(minutes=85),
                submitted_at=now - timedelta(minutes=20),
                is_auto_submitted=False,
                total_score=70,
            )
            session.add(g_sess)
            await session.flush()

            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=g_sess.id,
                    violation_type="tab_switch",
                    details="Tab switch detected (external documentation lookup)",
                    occurred_at=now - timedelta(minutes=45),
                )
            )

        # CS301 Systems Exam session: Kevin (completed with violations) and Ian
        sys_exam = exams["CS301 Practical Systems Exam: Memory & Bitwise Ops"]
        kevin_user = students["kevin@codeforge.local"]
        k_chk = await session.execute(
            select(ExamSession).where(
                ExamSession.exam_id == sys_exam.id,
                ExamSession.user_id == kevin_user.id,
            )
        )
        if k_chk.scalar_one_or_none() is None:
            k_sess = ExamSession(
                id=uuid.uuid4(),
                exam_id=sys_exam.id,
                user_id=kevin_user.id,
                started_at=now - timedelta(minutes=60),
                submitted_at=now - timedelta(minutes=10),
                is_auto_submitted=False,
                total_score=100,
            )
            session.add(k_sess)
            await session.flush()

            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=k_sess.id,
                    violation_type="fullscreen_exit",
                    details="Full screen exited via ESC key",
                    occurred_at=now - timedelta(minutes=40),
                )
            )
            session.add(
                ExamViolation(
                    id=uuid.uuid4(),
                    exam_session_id=k_sess.id,
                    violation_type="focus_loss",
                    details="Window blur detected (screenshot key combination intercepted)",
                    occurred_at=now - timedelta(minutes=25),
                )
            )

        await session.commit()

    logger.info("Seeding completed successfully!")
    logger.info("====================================================================")
    logger.info("  Instructors (password: changeme):")
    logger.info("    admin@codeforge.local      - Admin Instructor (CS101, CS201, CS301)")
    logger.info("    prof.chen@codeforge.local  - Prof. Alan Chen (CS201, MATH150)")
    logger.info("    dr.stone@codeforge.local   - Dr. Elena Stone (CS301)")
    logger.info("--------------------------------------------------------------------")
    logger.info("  Students (12 accounts, password: changeme):")
    logger.info("    student@codeforge.local    - Alex Student (Clean baseline for live demos)")
    logger.info("    alice@, bob@, charlie@, diana@, evan@, fiona@, george@,")
    logger.info("    hannah@, ian@, julia@, kevin@codeforge.local")
    logger.info("--------------------------------------------------------------------")
    logger.info("  Courses:")
    logger.info("    CS101: Introduction to Programming (Code: CS101A)")
    logger.info("    CS201: Data Structures & Algorithms (Code: CS201B)")
    logger.info("    CS301: Systems & Low-Level C/C++ Programming (Code: CS301C)")
    logger.info("    MATH150: Discrete Mathematics for CS (Code: M150D)")
    logger.info("--------------------------------------------------------------------")
    logger.info("  Labs (4 sessions):")
    logger.info("    CS101: Lab 1: Programming Basics & Warm-up (Active)")
    logger.info("    CS201: Lab 2: Searching & Pointer Invariants (Active)")
    logger.info("    CS301: Lab 3: C/C++ Memory & Bitwise Lab (Active)")
    logger.info("    CS101: Lab 0: Diagnostic Orientation (Closed)")
    logger.info("--------------------------------------------------------------------")
    logger.info("  Exams (4 assessments):")
    logger.info("    CS101 Midterm Proctored Assessment (Active window)")
    logger.info("    CS101 Final Assessment: Problem Solving Mastery (Scheduled)")
    logger.info("    CS201 Midterm: Algorithmic Efficiency & Searching (Active window)")
    logger.info("    CS301 Practical Systems Exam: Memory & Bitwise Ops (Active window)")
    logger.info("====================================================================")


if __name__ == "__main__":
    asyncio.run(seed())
