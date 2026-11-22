"""Sandbox execution tests for C and C++ (Phase A2).

Requires Docker to be running and images built:
    codeforge-sandbox-c
    codeforge-sandbox-cpp
"""

import os
import tempfile
import uuid
import pytest
from unittest.mock import MagicMock

from app.models.problem import Problem
from app.models.test_case import TestCase as TestCaseModel
TestCaseModel.__test__ = False

from app.worker.sandbox import (
    _compile_code,
    _get_docker_client,
    _run_test_case,
)


def _make_mock_problem(memory_limit_mb=128, time_limit_sec=5):
    prob = MagicMock(spec=Problem)
    prob.id = uuid.uuid4()
    prob.memory_limit_mb = memory_limit_mb
    prob.time_limit_sec = time_limit_sec
    return prob


def _make_mock_test_case(label="01", input_data="", expected_output="", is_visible=True):
    tc = MagicMock(spec=TestCaseModel)
    tc.id = uuid.uuid4()
    tc.label = label
    tc.input_data = input_data
    tc.expected_output = expected_output
    tc.is_visible = is_visible
    return tc


class TestCSandbox:
    """Tests for the C sandbox container (codeforge-sandbox-c)."""

    def test_c_correct_hello_world(self):
        """Correct C solution compiles, executes, and passes matching expected output."""
        source = """#include <stdio.h>
int main() {
    int a, b;
    if (scanf("%d %d", &a, &b) == 2) {
        printf("%d\\n", a + b);
    }
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.c"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="c")
            assert compile_result["success"] is True

            tc = _make_mock_test_case("01", "12 34\n", "46")
            result = _run_test_case(
                client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="c"
            )

            assert result["passed"] is True
            assert result["error"] is None
            assert result["actual_output"] == "46"

    def test_c_compile_error(self):
        """Syntax error in C code produces compile error with compiler logs."""
        source = """#include <stdio.h>
int main() {
    this_is_a_syntax_error
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.c"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="c")
            assert compile_result["success"] is False
            assert "error" in compile_result
            assert len(compile_result["error"]) > 0

    def test_c_wrong_answer(self):
        """Valid C program producing incorrect output is marked passed=False."""
        source = """#include <stdio.h>
int main() {
    printf("Wrong Output\\n");
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.c"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="c")
            assert compile_result["success"] is True

            tc = _make_mock_test_case("01", "", "Expected Output")
            result = _run_test_case(
                client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="c"
            )

            assert result["passed"] is False
            assert result["error"] is None
            assert result["actual_output"] == "Wrong Output"

    def test_c_timeout(self):
        """C program with infinite loop triggers Time Limit Exceeded."""
        source = """int main() {
    while (1) {}
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.c"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="c")
            assert compile_result["success"] is True

            tc = _make_mock_test_case("01", "", "")
            result = _run_test_case(
                client, tc, tmp_dir, time_limit_sec=2, memory_limit_mb=128, language="c"
            )

            assert result["passed"] is False
            assert result["error"] == "Time Limit Exceeded"

    def test_c_no_zombie_containers(self):
        """Containers are cleanly removed even after execution."""
        import docker as docker_module

        source = """#include <stdio.h>
int main() {
    printf("clean\\n");
    return 0;
}
"""
        client = _get_docker_client()
        docker_client = docker_module.from_env()
        problem = _make_mock_problem()

        before_ids = {
            c.id for c in docker_client.containers.list(all=True, filters={"ancestor": "codeforge-sandbox-c"})
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.c"), "w", encoding="utf-8") as f:
                f.write(source)

            _compile_code(client, tmp_dir, problem, language="c")
            tc = _make_mock_test_case("01", "", "clean")
            _run_test_case(
                client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="c"
            )

        after_containers = [
            c for c in docker_client.containers.list(all=True, filters={"ancestor": "codeforge-sandbox-c"})
            if c.id not in before_ids
        ]
        assert len(after_containers) == 0, f"Found {len(after_containers)} zombie C containers"


class TestCppSandbox:
    """Tests for the C++ sandbox container (codeforge-sandbox-cpp)."""

    def test_cpp_correct_solution(self):
        """Valid C++20 program compiles and outputs correctly."""
        source = """#include <iostream>
int main() {
    int a, b;
    if (std::cin >> a >> b) {
        std::cout << (a * b) << "\\n";
    }
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.cpp"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="cpp")
            assert compile_result["success"] is True

            tc = _make_mock_test_case("01", "7 8\n", "56")
            result = _run_test_case(
                client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="cpp"
            )

            assert result["passed"] is True
            assert result["error"] is None
            assert result["actual_output"] == "56"

    def test_cpp_compile_error(self):
        """Invalid C++ produces compile error."""
        source = """#include <iostream>
int main() {
    std::cout << undefined_symbol << std::endl;
    return 0;
}
"""
        client = _get_docker_client()
        problem = _make_mock_problem()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.cpp"), "w", encoding="utf-8") as f:
                f.write(source)

            compile_result = _compile_code(client, tmp_dir, problem, language="cpp")
            assert compile_result["success"] is False
            assert "undefined_symbol" in compile_result["error"]
