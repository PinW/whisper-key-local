#!/usr/bin/env python3
import sys
import os
import shutil
import subprocess
from pathlib import Path

FILES_TO_SYMLINK = [
    ".claude/settings.local.json",
]

FILES_TO_COPY = [
    "py-build/build-config.json",  # Windows PowerShell can't follow Linux symlinks
]

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <project-name> <branch-name>")
        sys.exit(1)

    project_name = sys.argv[1]
    branch_name = sys.argv[2]

    home = Path.home()
    main_repo = home / project_name
    worktree = home / "worktrees" / project_name / branch_name

    if not main_repo.exists():
        print(f"Error: Main repo not found at {main_repo}")
        sys.exit(1)

    if not worktree.exists():
        print(f"Creating worktree at {worktree}...")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree), branch_name],
            cwd=main_repo,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error creating worktree: {result.stderr}")
            sys.exit(1)
        print(f"Created worktree for branch '{branch_name}'")
    else:
        print(f"Worktree already exists at {worktree}")

    for rel_path in FILES_TO_SYMLINK:
        source = main_repo / rel_path
        target = worktree / rel_path

        if not source.exists():
            print(f"Warning: Source file not found: {source}")
            continue

        if target.exists() or target.is_symlink():
            print(f"Skipping (already exists): {target}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(source, target)
        print(f"Created symlink: {target} -> {source}")

    for rel_path in FILES_TO_COPY:
        source = main_repo / rel_path
        target = worktree / rel_path

        if not source.exists():
            print(f"Warning: Source file not found: {source}")
            continue

        if target.exists():
            print(f"Skipping (already exists): {target}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print(f"Copied: {source} -> {target}")

if __name__ == "__main__":
    main()
