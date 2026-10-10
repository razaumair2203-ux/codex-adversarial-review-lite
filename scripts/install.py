#!/usr/bin/env python3
"""Install one complete skill with a staged copy and recoverable backup."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

NAME = "codex-adversarial-review-lite"
HOST = "claude"
ROOT = Path(__file__).resolve().parent.parent


def default_root():
    if HOST == "claude":
        return Path(os.environ.get("CLAUDE_SKILLS_DIR", str(Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "skills")))
    # Update an existing legacy installation in place; new installs use current
    # documented discovery. Explicit root always takes precedence.
    if os.environ.get("CODEX_HOME"):
        return Path(os.environ["CODEX_HOME"]) / "skills"
    legacy = Path.home() / ".codex/skills"
    current = Path.home() / ".agents/skills"
    return legacy if (legacy / NAME / "SKILL.md").is_file() and not (current / NAME).exists() else current


def install(root):
    source = ROOT / "skills" / NAME
    for file in ("SKILL.md", "scripts/review_runner.py", "references/review-schema.json", "references/reviewer-prompt.md"):
        if not (source / file).is_file():
            raise ValueError("Incomplete checkout: " + file)
    json.loads((source / "references/review-schema.json").read_text(encoding="utf-8"))
    root = Path(root).expanduser().resolve()
    destination = root / NAME
    if destination.is_symlink() or (destination.exists() and destination.resolve() != destination):
        raise ValueError("Refusing to replace a linked installation. Choose --skills-root with a real destination.")
    if destination == source.resolve() or root.is_relative_to(source.resolve()):
        raise ValueError("Installation must not replace or nest inside its source checkout.")
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + NAME + "-install-", dir=root))
    backup = None
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        compile((stage / "scripts/review_runner.py").read_text(encoding="utf-8"), "review_runner.py", "exec")
        if destination.exists():
            backups = root.parent / "skill-backups"
            backups.mkdir(parents=True, exist_ok=True)
            backup = backups / (NAME + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
            destination.rename(backup)
        try:
            stage.rename(destination)
        except OSError:
            if backup:
                backup.rename(destination)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", help="Explicit installed skill parent directory")
    parser.add_argument("--check", action="store_true", help="Run installed offline checks after copying")
    args = parser.parse_args()
    try:
        if sys.version_info < (3, 11):
            raise ValueError("Python 3.11+ required; running " + sys.version.split()[0])
        destination, backup = install(args.skills_root or default_root())
        print("Installed " + NAME + " at " + str(destination), flush=True)
        if backup:
            print("Previous installation preserved at " + str(backup), flush=True)
        if HOST == "claude":
            legacy = destination.parent / "adversarial-reviewer-lite"
            if legacy.exists():
                print("Legacy /adversarial-reviewer-lite remains. Use /codex-adversarial-review-lite; archive the legacy copy when ready.")
        print("Available on your next turn; reopen the host if it does not appear.")
        backend = "codex" if HOST == "claude" else "claude"
        runner = destination / "scripts/review_runner.py"
        print("Check setup: " + subprocess.list2cmdline([sys.executable, str(runner), "selftest", "--backend", backend]))
        if args.check:
            return subprocess.call([sys.executable, str(runner), "selftest", "--backend", backend])
        return 0
    except (OSError, ValueError) as error:
        print("Install failed: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
