"""Docker sandbox execution logic.

Developer A: implement this module in Phase A3.
"""


def normalize(output: str) -> str:
    """
    Normalize program output for comparison.

    - Strip trailing whitespace per line.
    - Strip trailing newlines at end of output.
    - Normalize line endings (\\r\\n → \\n).

    TODO (Phase A3): implement this function.
    """
    raise NotImplementedError


def execute_submission(submission_id: str) -> dict:
    """
    Core sandbox execution logic.

    Steps (Phase A3):
    1. Fetch submission + problem + test_cases from DB.
    2. Write source_code to a temp Solution.java file.
    3. Compile step: spawn sandbox container, run `javac Solution.java`.
       - On compile error → mark all test cases failed, return early.
    4. Execution step (per test case):
       - Create ephemeral container from `codeforge-sandbox-java`.
       - Set: mem_limit=128m, cpu_quota=50000, network_disabled=True,
               read_only=True, cap_drop=ALL, no-new-privileges.
       - Feed input_data via stdin.
       - Wait with timeout (time_limit_sec).
       - Capture stdout + stderr.
       - Compare normalize(stdout) == normalize(expected_output).
       - Record pass/fail + execution_time_ms.
       - Remove container (try/finally — always clean up).
    5. Calculate score and update submission record.

    TODO (Phase A3): implement this function.
    """
    raise NotImplementedError
