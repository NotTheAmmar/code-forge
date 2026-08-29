#!/usr/bin/env python3
"""CodeForge management CLI.

Usage:
    # Load all problems from the problems/ directory
    python manage.py load-problems ./problems/

    # Load a single problem folder
    python manage.py load-problems ./problems/two-sum/

Re-running is idempotent — updates existing problems, adds new ones.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


def get_sync_engine():
    """Create a synchronous SQLAlchemy engine from settings."""
    from app.config import settings

    sync_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    # Fallback for plain postgresql:// URLs
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    return create_engine(sync_url, echo=False, pool_pre_ping=True)


def load_problems(problems_dir: Path) -> None:
    """Scan a directory for problem folders and load each into the database."""
    # Collect problem folders: either a single problem dir or a parent dir
    if _is_problem_folder(problems_dir):
        problem_dirs = [problems_dir]
    else:
        problem_dirs = sorted(
            [d for d in problems_dir.iterdir() if d.is_dir() and _is_problem_folder(d)]
        )

    if not problem_dirs:
        logger.error("No valid problem folders found in: %s", problems_dir)
        sys.exit(1)

    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Import models here (after sys.path is set up)
    from app.models.problem import Problem
    from app.models.test_case import TestCase

    # Ensure tables exist (idempotent — does not drop existing tables)
    from app.db import Base
    import app.models  # noqa: F401 — registers all models with Base.metadata
    Base.metadata.create_all(engine)

    loaded = 0
    errors = 0

    with SessionLocal() as session:
        for problem_dir in problem_dirs:
            try:
                _load_single_problem(problem_dir, session, Problem, TestCase)
                session.commit()
                loaded += 1
            except Exception as e:
                session.rollback()
                logger.error("✗ Failed to load '%s': %s", problem_dir.name, e)
                errors += 1

    logger.info("")
    logger.info("Done. Loaded: %d  Errors: %d", loaded, errors)
    if errors:
        sys.exit(1)


def _is_problem_folder(path: Path) -> bool:
    """Return True if this directory looks like a problem folder."""
    return (path / "problem.yaml").exists()


def _load_single_problem(
    problem_dir: Path,
    session: Session,
    Problem,
    TestCase,
) -> None:
    """Load or update a single problem from its directory."""
    slug = problem_dir.name

    # ── Read problem.yaml ──────────────────────────────────────────────────
    yaml_path = problem_dir / "problem.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    _validate_yaml(meta, yaml_path)

    # ── Read description.md ────────────────────────────────────────────────
    desc_path = problem_dir / "description.md"
    if not desc_path.exists():
        raise FileNotFoundError(f"Missing description.md in {problem_dir}")
    description = desc_path.read_text(encoding="utf-8")

    # ── Read test case files ───────────────────────────────────────────────
    tests_dir = problem_dir / "tests"
    if not tests_dir.exists():
        raise FileNotFoundError(f"Missing tests/ directory in {problem_dir}")

    test_cases = _read_test_cases(tests_dir, meta.get("visible_tests", []))

    if not test_cases:
        raise ValueError(f"No test cases found in {tests_dir}")

    # ── Upsert problem ─────────────────────────────────────────────────────
    existing = session.execute(
        select(Problem).where(Problem.slug == slug)
    ).scalar_one_or_none()

    starter_code = meta.get("starter_code", {}).get("java", "")

    if existing is None:
        problem = Problem(
            slug=slug,
            title=meta["title"],
            description=description,
            difficulty=meta["difficulty"],
            starter_code_java=starter_code,
            time_limit_sec=int(meta.get("time_limit_sec", 10)),
            memory_limit_mb=int(meta.get("memory_limit_mb", 128)),
        )
        session.add(problem)
        session.flush()  # Get the ID
        action = "Created"
    else:
        existing.title = meta["title"]
        existing.description = description
        existing.difficulty = meta["difficulty"]
        existing.starter_code_java = starter_code
        existing.time_limit_sec = int(meta.get("time_limit_sec", 10))
        existing.memory_limit_mb = int(meta.get("memory_limit_mb", 128))
        problem = existing
        action = "Updated"

    # ── Upsert test cases ──────────────────────────────────────────────────
    # Delete existing test cases and re-insert (simplest idempotent approach)
    existing_tcs = session.execute(
        select(TestCase).where(TestCase.problem_id == problem.id)
    ).scalars().all()
    for tc in existing_tcs:
        session.delete(tc)
    session.flush()

    for tc_data in test_cases:
        tc = TestCase(
            problem_id=problem.id,
            label=tc_data["label"],
            input_data=tc_data["input_data"],
            expected_output=tc_data["expected_output"],
            is_visible=tc_data["is_visible"],
            order_index=tc_data["order_index"],
        )
        session.add(tc)

    visible_count = sum(1 for tc in test_cases if tc["is_visible"])
    hidden_count = len(test_cases) - visible_count

    logger.info(
        "✓ %s '%s' (%s) — %d test cases (%d visible, %d hidden)",
        action,
        slug,
        meta["difficulty"],
        len(test_cases),
        visible_count,
        hidden_count,
    )


def _read_test_cases(tests_dir: Path, visible_tests: list[str]) -> list[dict]:
    """Read all .in/.out pairs from the tests/ directory."""
    # Find all .in files
    in_files = sorted(tests_dir.glob("*.in"))
    test_cases = []

    for in_file in in_files:
        label = in_file.stem  # e.g. "01"
        out_file = tests_dir / f"{label}.out"

        if not out_file.exists():
            raise FileNotFoundError(
                f"Test case '{label}' has .in but no matching .out file"
            )

        input_data = in_file.read_text(encoding="utf-8")
        expected_output = out_file.read_text(encoding="utf-8")

        # Normalize — strip trailing newline from .out files
        expected_output = expected_output.rstrip("\n")

        test_cases.append({
            "label": label,
            "input_data": input_data.rstrip("\n"),
            "expected_output": expected_output,
            "is_visible": label in visible_tests,
            "order_index": _label_to_index(label),
        })

    return test_cases


def _label_to_index(label: str) -> int:
    """Convert a test case label like '01' to an integer sort key."""
    try:
        return int(label)
    except ValueError:
        # Fallback: use ASCII sort order for non-numeric labels
        return sum(ord(c) for c in label)


def _validate_yaml(meta: dict, path: Path) -> None:
    """Validate required fields are present in problem.yaml."""
    required = ["title", "difficulty", "starter_code"]
    missing = [field for field in required if field not in meta]
    if missing:
        raise ValueError(
            f"{path}: missing required fields: {', '.join(missing)}"
        )

    valid_difficulties = {"easy", "medium", "hard"}
    if meta["difficulty"] not in valid_difficulties:
        raise ValueError(
            f"{path}: difficulty must be one of {valid_difficulties}, "
            f"got '{meta['difficulty']}'"
        )

    if "java" not in meta.get("starter_code", {}):
        raise ValueError(
            f"{path}: starter_code.java is required"
        )


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CodeForge management commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # load-problems sub-command
    load_parser = subparsers.add_parser(
        "load-problems",
        help="Load/update problems from YAML files into the database",
    )
    load_parser.add_argument(
        "path",
        type=Path,
        help="Path to a problems directory or a single problem folder",
    )

    args = parser.parse_args()

    if args.command == "load-problems":
        path = args.path.resolve()
        if not path.exists():
            logger.error("Path does not exist: %s", path)
            sys.exit(1)
        logger.info("Loading problems from: %s", path)
        load_problems(path)


if __name__ == "__main__":
    main()
