"""Sandbox execution tests.

These tests verify the Docker sandbox execution engine directly.
They REQUIRE Docker to be running and the sandbox image to be built:

    docker build -t codeforge-sandbox-java ./sandbox/java

Run with:
    docker compose exec api pytest tests/test_sandbox.py -v -s

NOTE: These tests are slower (each spawns Docker containers).
      They are tagged with `@pytest.mark.sandbox` so you can run
      only fast tests with: pytest -m "not sandbox"
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.worker.sandbox import normalize


# ── normalize() unit tests (no Docker required) ───────────────────────────────

class TestNormalize:
    def test_strips_trailing_whitespace_per_line(self):
        assert normalize("hello   \nworld  ") == "hello\nworld"

    def test_strips_trailing_newlines(self):
        assert normalize("hello\n\n\n") == "hello"

    def test_normalizes_crlf_line_endings(self):
        assert normalize("hello\r\nworld\r\n") == "hello\nworld"

    def test_empty_string(self):
        assert normalize("") == ""

    def test_single_newline(self):
        assert normalize("\n") == ""

    def test_mixed_line_endings(self):
        result = normalize("line1\r\nline2\nline3\r")
        assert result == "line1\nline2\nline3"

    def test_preserves_internal_blank_lines(self):
        result = normalize("a\n\nb")
        assert result == "a\n\nb"

    def test_matching_outputs_are_equal(self):
        expected = "0 1"
        actual = "0 1\n"
        assert normalize(actual) == normalize(expected)


# ── Docker sandbox tests (require Docker) ─────────────────────────────────────

pytestmark_sandbox = pytest.mark.sandbox


def _make_mock_test_case(
    label: str,
    input_data: str,
    expected_output: str,
    is_visible: bool = True,
    order_index: int = 1,
) -> MagicMock:
    """Create a mock TestCase object for sandbox tests."""
    tc = MagicMock()
    tc.id = uuid.uuid4()
    tc.label = label
    tc.input_data = input_data
    tc.expected_output = expected_output
    tc.is_visible = is_visible
    tc.order_index = order_index
    return tc


def _make_mock_problem(time_limit_sec: int = 5, memory_limit_mb: int = 128) -> MagicMock:
    problem = MagicMock()
    problem.id = uuid.uuid4()
    problem.time_limit_sec = time_limit_sec
    problem.memory_limit_mb = memory_limit_mb
    return problem


@pytest.mark.sandbox
class TestDockerSandbox:
    """Integration tests that spawn real Docker containers."""

    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Skip sandbox tests if Docker is not available."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            # Check sandbox image exists
            try:
                client.images.get("codeforge-sandbox-java")
            except docker.errors.ImageNotFound:
                pytest.skip(
                    "Sandbox image 'codeforge-sandbox-java' not found. "
                    "Run: docker build -t codeforge-sandbox-java ./sandbox/java"
                )
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")

    def test_correct_hello_world(self):
        """Correct code passes all visible test cases."""
        from app.worker.sandbox import _compile_java, _get_docker_client, _run_test_case
        import tempfile, os

        source = """
import java.util.Scanner;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String name = sc.nextLine();
        System.out.println("Hello, " + name + "!");
    }
}
"""
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            compile_result = _compile_java(client, tmp_dir, problem)
            assert compile_result["success"], f"Compile failed: {compile_result.get('error')}"

            tc = _make_mock_test_case("01", "Alice", "Hello, Alice!")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128)

            assert result["passed"] is True
            assert result["error"] is None
            assert result["execution_time_ms"] is not None

    def test_compile_error(self):
        """Syntax error in Java source is caught as compile_error."""
        from app.worker.sandbox import _compile_java, _get_docker_client
        import tempfile, os

        source = "this is not valid java { {{ }"

        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            result = _compile_java(client, tmp_dir, problem)

            assert result["success"] is False
            assert "error" in result
            assert result["error"]  # Non-empty error message

    def test_wrong_answer(self):
        """Code that produces wrong output is marked as failed."""
        from app.worker.sandbox import _compile_java, _get_docker_client, _run_test_case
        import tempfile, os

        source = """
public class Solution {
    public static void main(String[] args) {
        System.out.println("Wrong Answer");
    }
}
"""
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            compile_result = _compile_java(client, tmp_dir, problem)
            assert compile_result["success"]

            tc = _make_mock_test_case("01", "", "Hello, Alice!")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128)

            assert result["passed"] is False
            assert result["error"] is None  # Not an error, just wrong answer
            assert result["actual_output"] == "Wrong Answer"

    def test_runtime_exception(self):
        """Code that throws a runtime exception returns error info."""
        from app.worker.sandbox import _compile_java, _get_docker_client, _run_test_case
        import tempfile, os

        source = """
public class Solution {
    public static void main(String[] args) {
        int x = 1 / 0;  // ArithmeticException
    }
}
"""
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            compile_result = _compile_java(client, tmp_dir, problem)
            assert compile_result["success"]

            tc = _make_mock_test_case("01", "", "")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128)

            assert result["passed"] is False
            assert result["error"] is not None
            assert "ArithmeticException" in result["error"] or "zero" in result["error"].lower()

    def test_timeout(self):
        """Infinite loop is caught as Time Limit Exceeded."""
        from app.worker.sandbox import _compile_java, _get_docker_client, _run_test_case
        import tempfile, os

        source = """
public class Solution {
    public static void main(String[] args) throws Exception {
        while (true) { Thread.sleep(100); }
    }
}
"""
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            compile_result = _compile_java(client, tmp_dir, problem)
            assert compile_result["success"]

            tc = _make_mock_test_case("01", "", "")
            # Use 2s timeout so the test doesn't take forever
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=2, memory_limit_mb=128)

            assert result["passed"] is False
            assert result["error"] == "Time Limit Exceeded"

    def test_no_zombie_containers(self):
        """Verify no sandbox containers are left behind after execution."""
        import docker as docker_module
        from app.worker.sandbox import _compile_java, _get_docker_client, _run_test_case
        import tempfile, os

        source = """
public class Solution {
    public static void main(String[] args) { System.out.println("ok"); }
}
"""
        client = _get_docker_client()
        docker_client = docker_module.from_env()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.java"), "w") as f:
                f.write(source)

            problem = _make_mock_problem()
            _compile_java(client, tmp_dir, problem)

            tc = _make_mock_test_case("01", "", "ok")
            _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128)

        # Check for leftover containers using the sandbox image
        containers = docker_client.containers.list(
            all=True,
            filters={"ancestor": "codeforge-sandbox-java", "status": "exited"}
        )
        assert len(containers) == 0, (
            f"Found {len(containers)} zombie containers after sandbox run"
        )


@pytest.mark.sandbox
class TestPythonSandbox:
    """Integration tests that spawn real Python Docker containers."""

    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Skip sandbox tests if Docker is not available."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            try:
                client.images.get("codeforge-sandbox-python")
            except docker.errors.ImageNotFound:
                pytest.skip(
                    "Sandbox image 'codeforge-sandbox-python' not found. "
                    "Run: docker build -t codeforge-sandbox-python ./sandbox/python"
                )
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")

    def test_python_correct_hello_world(self):
        """Correct Python code passes test case."""
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "import sys\nname = sys.stdin.read().strip()\nprint(f'Hello, {name}!')\n"
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "Alice", "Hello, Alice!")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="python")

            assert result["passed"] is True
            assert result["error"] is None
            assert result["actual_output"] == "Hello, Alice!"
            assert result["execution_time_ms"] is not None

    def test_python_wrong_answer(self):
        """Python code producing incorrect output is marked passed=False."""
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "print('Wrong Answer')\n"
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "", "Expected Answer")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="python")

            assert result["passed"] is False
            assert result["error"] is None
            assert result["actual_output"] == "Wrong Answer"

    def test_python_runtime_exception(self):
        """Python runtime exception (ZeroDivisionError) is captured."""
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "x = 1 / 0\n"
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "", "")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="python")

            assert result["passed"] is False
            assert result["error"] is not None
            assert "ZeroDivisionError" in result["error"]

    def test_python_syntax_error(self):
        """Python syntax error produces non-zero exit and syntax error info."""
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "def foo(\n"
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "", "")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="python")

            assert result["passed"] is False
            assert result["error"] is not None
            assert "SyntaxError" in result["error"]

    def test_python_timeout(self):
        """Python infinite loop is caught as Time Limit Exceeded."""
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "while True:\n    pass\n"
        client = _get_docker_client()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "", "")
            result = _run_test_case(client, tc, tmp_dir, time_limit_sec=2, memory_limit_mb=128, language="python")

            assert result["passed"] is False
            assert result["error"] == "Time Limit Exceeded"

    def test_python_no_zombie_containers(self):
        """Verify no sandbox containers survive after Python execution."""
        import docker as docker_module
        from app.worker.sandbox import _get_docker_client, _run_test_case
        import tempfile, os

        source = "print('done')\n"
        client = _get_docker_client()
        docker_client = docker_module.from_env()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Solution.py"), "w") as f:
                f.write(source)

            tc = _make_mock_test_case("01", "", "done")
            _run_test_case(client, tc, tmp_dir, time_limit_sec=5, memory_limit_mb=128, language="python")

        containers = docker_client.containers.list(
            all=True,
            filters={"ancestor": "codeforge-sandbox-python", "status": "exited"}
        )
        assert len(containers) == 0, f"Found {len(containers)} zombie Python containers"
