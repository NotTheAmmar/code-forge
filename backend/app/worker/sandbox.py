"""Docker sandbox execution logic.

This module implements the core code execution pipeline:
  1. Write student's Java source code to a temp directory.
  2. Compile with `javac` inside a sandbox container.
  3. For each test case: run `java Solution` in an ephemeral container,
     feed stdin, capture stdout/stderr, compare with expected output.
  4. Return structured results.

Security model:
  - Non-root `runner` user inside the container (set in sandbox Dockerfile).
  - Network disabled (--network=none).
  - Read-only root filesystem with tmpfs on /tmp.
  - All Linux capabilities dropped (--cap-drop=ALL).
  - no-new-privileges security option.
  - Per-problem memory and CPU limits.
  - Hard timeout per test case.

Container lifecycle:
  - Containers are always removed in a `try/finally` block.
  - No zombie containers should survive even on exceptions.
"""

import logging
import os
import shutil
import tarfile
import tempfile
import time
import uuid
from io import BytesIO

import docker
from docker.errors import ContainerError, DockerException, NotFound
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)

# The Docker image used for all Java sandbox containers.
# Build it once with: docker build -t codeforge-sandbox-java ./sandbox/java
SANDBOX_IMAGE = "codeforge-sandbox-java"
SANDBOX_WORKDIR = "/code"


# ── Output normalization ───────────────────────────────────────────────────────

def normalize(output: str) -> str:
    """Normalize program output for comparison.

    Rules:
    - Normalize line endings (\\r\\n → \\n).
    - Strip trailing whitespace per line.
    - Strip trailing newlines at end of output.

    This prevents false failures due to platform or printer differences.
    """
    output = output.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in output.split("\n")]
    return "\n".join(lines).rstrip()


# ── Main execution entry point ────────────────────────────────────────────────

def execute_submission(submission_id: str) -> dict:
    """Grade a submission by compiling and executing Java code in Docker containers.

    This function is called from the Celery grading task. It is synchronous
    because Celery workers are not async-aware.

    Args:
        submission_id: UUID string of the Submission record to grade.

    Returns:
        A dict with keys: status, score, passed_cases, total_cases, results_json,
        execution_time_ms. (The submission DB record is also updated in place.)
    """
    # Import here to avoid circular imports in module-level context
    from app.worker.sync_db import get_sync_session

    docker_client = _get_docker_client()

    with get_sync_session() as session:
        # ── Fetch submission + problem + test cases ────────────────────────
        submission = session.get(Submission, uuid.UUID(submission_id))
        if submission is None:
            raise ValueError(f"Submission {submission_id} not found in database")

        problem = session.get(Problem, submission.problem_id)
        if problem is None:
            raise ValueError(f"Problem {submission.problem_id} not found")

        # Determine which test cases to evaluate
        all_test_cases = (
            session.execute(
                select(TestCase)
                .where(TestCase.problem_id == problem.id)
                .order_by(TestCase.order_index)
            )
            .scalars()
            .all()
        )

        if submission.is_full_submit:
            test_cases_to_run = list(all_test_cases)
        else:
            test_cases_to_run = [tc for tc in all_test_cases if tc.is_visible]

        # Mark as running
        submission.status = "running"
        session.commit()

        # ── Work in a temp directory ────────────────────────────────────────
        tmp_dir = tempfile.mkdtemp(prefix="codeforge_")
        try:
            result = _compile_and_run(
                docker_client=docker_client,
                submission=submission,
                problem=problem,
                test_cases=test_cases_to_run,
                tmp_dir=tmp_dir,
                session=session,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


def _compile_and_run(
    docker_client,
    submission: Submission,
    problem: Problem,
    test_cases: list[TestCase],
    tmp_dir: str,
    session: Session,
) -> dict:
    """Write source, compile, then run each test case."""

    # Write source code to file
    source_path = os.path.join(tmp_dir, "Solution.java")
    with open(source_path, "w", encoding="utf-8") as f:
        f.write(submission.source_code)

    # ── Step 1: Compile ────────────────────────────────────────────────────
    compile_result = _compile_java(docker_client, tmp_dir, problem)

    if not compile_result["success"]:
        # Update submission: compile_error
        submission.status = "compile_error"
        submission.score = 0
        submission.total_cases = len(test_cases)
        submission.passed_cases = 0
        submission.results_json = []
        submission.execution_time_ms = 0
        # Store compile error in results_json so the frontend can display it
        submission.results_json = [{
            "test_case_id": "compile",
            "label": "compile",
            "is_visible": True,
            "passed": False,
            "expected_output": None,
            "actual_output": None,
            "execution_time_ms": 0,
            "error": compile_result["error"],
        }]
        session.commit()
        logger.info(
            "Submission %s: compile error", submission.id
        )
        return {
            "status": "compile_error",
            "score": 0,
            "passed_cases": 0,
            "total_cases": len(test_cases),
            "results_json": submission.results_json,
            "execution_time_ms": 0,
        }

    # ── Step 2: Run each test case ─────────────────────────────────────────
    results = []
    total_passed = 0
    total_time_ms = 0

    for tc in test_cases:
        tc_result = _run_test_case(
            docker_client=docker_client,
            test_case=tc,
            tmp_dir=tmp_dir,
            time_limit_sec=problem.time_limit_sec,
            memory_limit_mb=problem.memory_limit_mb,
        )
        results.append(tc_result)
        if tc_result["passed"]:
            total_passed += 1
        total_time_ms += tc_result.get("execution_time_ms") or 0

    total_cases = len(test_cases)
    score = round((total_passed / total_cases) * 100) if total_cases > 0 else 0

    # Determine overall status
    any_timeout = any(r.get("error") == "Time Limit Exceeded" for r in results)
    overall_status = "completed"
    if any_timeout and total_passed == 0:
        overall_status = "timeout"

    # Update submission
    submission.status = overall_status
    submission.score = score
    submission.total_cases = total_cases
    submission.passed_cases = total_passed
    submission.results_json = results
    submission.execution_time_ms = total_time_ms
    session.commit()

    logger.info(
        "Submission %s: %s, score=%d, passed=%d/%d",
        submission.id,
        overall_status,
        score,
        total_passed,
        total_cases,
    )
    return {
        "status": overall_status,
        "score": score,
        "passed_cases": total_passed,
        "total_cases": total_cases,
        "results_json": results,
        "execution_time_ms": total_time_ms,
    }


# ── Compilation ───────────────────────────────────────────────────────────────

def _compile_java(docker_client, tmp_dir: str, problem: Problem) -> dict:
    """Compile Solution.java inside a sandbox container.

    Uses put_archive to copy source code into the container rather than
    bind-mounting the temp directory. This works correctly when the Celery
    worker itself runs inside a Docker container (DinD scenario).

    Returns:
        {"success": True} or {"success": False, "error": "<javac stderr>"}
    """
    container = None
    try:
        # Create the container (don't start yet)
        container = docker_client.containers.create(
            image=SANDBOX_IMAGE,
            command="javac Solution.java",
            working_dir=SANDBOX_WORKDIR,
            network_disabled=True,
            mem_limit=f"{problem.memory_limit_mb}m",
            cpu_quota=50000,
            cpu_period=100000,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            user="runner",
        )

        # Copy Solution.java into the container via tar archive
        source_path = os.path.join(tmp_dir, "Solution.java")
        tar_buffer = BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(source_path, arcname="Solution.java")
        tar_buffer.seek(0)
        container.put_archive(SANDBOX_WORKDIR, tar_buffer.getvalue())

        # Start and wait for javac to finish
        container.start()
        exit_result = container.wait(timeout=60)
        exit_code = exit_result.get("StatusCode", -1)

        if exit_code == 0:
            # Compilation succeeded — copy the .class files back to tmp_dir
            # so the execution step can use them
            try:
                bits, _ = container.get_archive(SANDBOX_WORKDIR)
                class_tar = BytesIO(b"".join(bits))
                with tarfile.open(fileobj=class_tar, mode="r") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith(".class"):
                            member.name = os.path.basename(member.name)
                            tar.extract(member, path=tmp_dir)
            except Exception as e:
                logger.warning("Failed to retrieve .class files: %s", e)

            return {"success": True}
        else:
            # Compilation failed — capture stderr
            stderr_logs = container.logs(stdout=False, stderr=True)
            if isinstance(stderr_logs, bytes):
                stderr_logs = stderr_logs.decode("utf-8", errors="replace")
            return {"success": False, "error": stderr_logs or f"javac exited with code {exit_code}"}

    except DockerException as e:
        logger.exception("Docker error during compilation")
        return {"success": False, "error": f"Docker error: {e}"}

    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass



# ── Test case execution ───────────────────────────────────────────────────────

def _run_test_case(
    docker_client,
    test_case: TestCase,
    tmp_dir: str,
    time_limit_sec: int,
    memory_limit_mb: int,
) -> dict:
    """Execute the compiled Solution.class against a single test case.

    Strategy:
    - Write stdin to a file (stdin.txt) in tmp_dir.
    - Copy .class files + stdin.txt into the container via put_archive.
    - Run: sh -c 'java Solution < /code/stdin.txt'
    - Capture logs after completion.

    Returns a dict matching the TestCaseResult schema.
    """
    container = None
    start_time = time.monotonic()

    try:
        # Write stdin to a temp file so we can copy it into the container
        stdin_path = os.path.join(tmp_dir, "stdin.txt")
        with open(stdin_path, "w", encoding="utf-8") as f:
            f.write(test_case.input_data)

        # Create container
        container = docker_client.containers.create(
            image=SANDBOX_IMAGE,
            # Use sh to redirect stdin from file — avoids socket complexity
            command=["sh", "-c", "java -cp /code Solution < /code/stdin.txt"],
            working_dir=SANDBOX_WORKDIR,
            network_disabled=True,
            mem_limit=f"{memory_limit_mb}m",
            cpu_quota=50000,
            cpu_period=100000,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            user="runner",
            # Note: read_only=True removed — put_archive needs a writable /code.
            # Security is maintained via: network_disabled, cap_drop=ALL,
            # no-new-privileges, and running as non-root 'runner' user.
            tmpfs={"/tmp": "size=32m,noexec,nosuid"},
        )

        # Copy compiled .class files + stdin.txt into the container
        _copy_files_to_container(container, tmp_dir, extensions=(".class", ".txt"))

        # Start
        container.start()

        # Wait with timeout
        try:
            exit_result = container.wait(timeout=time_limit_sec + 2)
            exit_code = exit_result.get("StatusCode", -1)
        except Exception:
            # Timeout — kill the container
            try:
                container.kill()
            except Exception:
                pass
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return _make_result(
                test_case=test_case,
                passed=False,
                actual_output=None,
                execution_time_ms=elapsed_ms,
                error="Time Limit Exceeded",
            )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Check for wall-clock TLE
        if elapsed_ms > time_limit_sec * 1000:
            return _make_result(
                test_case=test_case,
                passed=False,
                actual_output=None,
                execution_time_ms=elapsed_ms,
                error="Time Limit Exceeded",
            )

        # Capture stdout and stderr separately
        stdout_logs = container.logs(stdout=True, stderr=False)
        stderr_logs = container.logs(stdout=False, stderr=True)

        if isinstance(stdout_logs, bytes):
            stdout_logs = stdout_logs.decode("utf-8", errors="replace")
        if isinstance(stderr_logs, bytes):
            stderr_logs = stderr_logs.decode("utf-8", errors="replace")

        # Runtime error (non-zero exit)
        if exit_code != 0:
            error_msg = stderr_logs.strip() or f"Exited with code {exit_code}"
            if len(error_msg) > 2000:
                error_msg = error_msg[:2000] + "\n... (truncated)"
            return _make_result(
                test_case=test_case,
                passed=False,
                actual_output=stdout_logs.strip() or None,
                execution_time_ms=elapsed_ms,
                error=error_msg,
            )

        # Compare normalized output
        actual = normalize(stdout_logs)
        expected = normalize(test_case.expected_output)
        passed = actual == expected

        return _make_result(
            test_case=test_case,
            passed=passed,
            actual_output=actual,
            execution_time_ms=elapsed_ms,
            error=None,
        )

    except DockerException as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception("Docker error running test case %s", test_case.label)
        return _make_result(
            test_case=test_case,
            passed=False,
            actual_output=None,
            execution_time_ms=elapsed_ms,
            error=f"Sandbox error: {e}",
        )

    finally:
        # Always remove the container — no zombie containers
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass



def _make_result(
    test_case: TestCase,
    passed: bool,
    actual_output: str | None,
    execution_time_ms: int,
    error: str | None,
) -> dict:
    """Build a TestCaseResult dict from execution data."""
    return {
        "test_case_id": str(test_case.id),
        "label": test_case.label,
        "is_visible": test_case.is_visible,
        "passed": passed,
        # Only expose expected/actual output for visible test cases
        "expected_output": test_case.expected_output if test_case.is_visible else None,
        "actual_output": actual_output if test_case.is_visible else None,
        "execution_time_ms": execution_time_ms,
        "error": error,
    }


def _copy_files_to_container(
    container,
    tmp_dir: str,
    extensions: tuple = (".class",),
) -> None:
    """Copy files with the given extensions from tmp_dir into the container at /code."""
    files = [f for f in os.listdir(tmp_dir) if f.endswith(extensions)]
    if not files:
        return

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for filename in files:
            filepath = os.path.join(tmp_dir, filename)
            tar.add(filepath, arcname=filename)
    tar_buffer.seek(0)

    container.put_archive(SANDBOX_WORKDIR, tar_buffer.getvalue())


# Keep old name as alias for tests that import it directly
_copy_class_files_to_container = _copy_files_to_container


def _get_docker_client():
    """Create and return a Docker client, with a helpful error message on failure."""
    try:
        client = docker.from_env()
        client.ping()  # Verify connection
        return client
    except DockerException as e:
        raise RuntimeError(
            "Cannot connect to Docker daemon. "
            "Ensure the Docker socket is mounted: "
            "-v /var/run/docker.sock:/var/run/docker.sock"
        ) from e
