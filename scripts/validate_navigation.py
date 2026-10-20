#!/usr/bin/env python3
"""
CaseBridge AI — Repository Navigation and Documentation Validator.

Validates that:
1. Root `AGENTS.md` and `progress.md` exist.
2. Every non-ignored source directory contains its corresponding `<dirname>.md`.
3. Every directory documentation file contains the required standard sections:
   - Purpose
   - Directory tree
   - File inventory
   - Subdirectory inventory
   - Relationships and dependencies
   - Development and verification
   - Maintenance notes
4. Every direct child file in a directory is inventoried in its `<dirname>.md`.
5. Every direct child subdirectory is listed in its `<dirname>.md`.
6. Relative Markdown links between navigation files resolve to existing files.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Directories to exclude from the navigation documentation requirement
EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}

# Root files that don't need their own directory markdown
ROOT_DOCS = {"AGENTS.md", "progress.md"}

# Required section headers (case-insensitive substring check)
REQUIRED_SECTIONS = [
    "Purpose",
    "Directory tree",
    "File inventory",
    "Subdirectory inventory",
    "Relationships and dependencies",
    "Development and verification",
    "Maintenance notes",
]


def find_target_directories(root: Path) -> list[Path]:
    """Find all directories that must contain a documentation file."""
    dirs_to_check: list[Path] = []
    for current_root, dirs, _ in os.walk(root):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES and not d.startswith(".")]
        current_path = Path(current_root)
        if current_path != root:
            dirs_to_check.append(current_path)
    return sorted(dirs_to_check)


def check_directory_doc(dir_path: Path, root: Path) -> list[str]:
    """Validate the documentation file for a single directory."""
    errors: list[str] = []
    dir_name = dir_path.name
    doc_file = dir_path / f"{dir_name}.md"

    if not doc_file.is_file():
        errors.append(f"Missing doc file: {doc_file.relative_to(root)}")
        return errors

    content = doc_file.read_text(encoding="utf-8")

    # Check required sections
    for section in REQUIRED_SECTIONS:
        if not re.search(re.escape(section), content, re.IGNORECASE):
            errors.append(f"{doc_file.relative_to(root)}: Missing required section '{section}'")

    # Check that direct child files are listed (except the doc file itself)
    child_files = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.name != doc_file.name and f.name not in {".DS_Store"}
    ]
    for child in child_files:
        if child.name not in content:
            errors.append(f"{doc_file.relative_to(root)}: Child file '{child.name}' not mentioned in file inventory")

    # Check that direct child directories are listed
    child_dirs = [
        d for d in dir_path.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_DIR_NAMES and not d.name.startswith(".")
    ]
    for cdir in child_dirs:
        if cdir.name not in content:
            errors.append(f"{doc_file.relative_to(root)}: Child directory '{cdir.name}' not mentioned in subdirectory inventory")

    # Check Markdown links
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    for match in link_pattern.finditer(content):
        link_target = match.group(2).split("#")[0].strip()
        if not link_target or link_target.startswith(("http://", "https://", "mailto:")):
            continue
        target_path = (dir_path / link_target).resolve()
        if not target_path.exists():
            errors.append(f"{doc_file.relative_to(root)}: Broken link to '{link_target}'")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    print(f"Auditing CaseBridge AI navigation system at: {root}")
    all_errors: list[str] = []

    # 1. Root AGENTS.md check
    root_agents = root / "AGENTS.md"
    if not root_agents.is_file():
        all_errors.append("Root AGENTS.md does not exist.")
    else:
        agents_content = root_agents.read_text(encoding="utf-8")
        if "progress.md" not in agents_content:
            all_errors.append("Root AGENTS.md does not reference progress.md.")

    # 2. Root progress.md check
    root_progress = root / "progress.md"
    if not root_progress.is_file():
        all_errors.append("Root progress.md does not exist.")

    # 3. Check every non-excluded directory
    target_dirs = find_target_directories(root)
    print(f"Discovered {len(target_dirs)} directories requiring documentation.")

    for d in target_dirs:
        dir_errors = check_directory_doc(d, root)
        all_errors.extend(dir_errors)

    if all_errors:
        print(f"\n[FAIL] Found {len(all_errors)} navigation/documentation issue(s):")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("\n[PASS] All directories and files are properly documented and linked!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
