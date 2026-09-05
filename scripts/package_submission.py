#!/usr/bin/env python3
"""Submission Archive Packager & Verification Inspector.

Creates a clean, hermetic ZIP archive for Buildathon Track 03 submission.
Strictly excludes:
- .env and secret files
- node_modules and virtual environments
- Local databases (*.db, *.sqlite3) and SQLite write-ahead journals (*-wal, *-shm)
- Local build caches, __pycache__, and temporary review folders

Verifies the packed archive for secrets before reporting clean status.
"""

import fnmatch
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "dist_submission"
ARCHIVE_NAME = "razorpay_recovery_autopilot_submission.zip"

# Strict exclusion patterns
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "coverage",
    ".vite",
    ".idea",
    ".vscode",
    "dist_submission",
}

EXCLUDE_PATTERNS = [
    ".env",
    ".env.*",
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.sqlite3",
    "*.sqlite3-wal",
    "*.sqlite3-shm",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".judge-review*",
    ".review-*",
]

SECRET_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9-_]{40,}"),
    re.compile(r"AQ\.[A-Za-z0-9-_]{40,}"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"),
]


def is_excluded(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    # Check directory components
    for p in parts[:-1]:
        if p in EXCLUDE_DIRS:
            return True
        if p.startswith(".review") or p.startswith(".judge-review"):
            return True

    # Check filename
    filename = parts[-1]
    if filename in EXCLUDE_DIRS:
        return True

    # .env.example is allowed; .env is excluded
    if filename == ".env.example":
        return False

    for pattern in EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


def create_submission_archive():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = OUTPUT_DIR / ARCHIVE_NAME

    if archive_path.exists():
        archive_path.unlink()

    packed_files = []
    print(f"[Packaging] Scanning repository: {ROOT_DIR}")

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Modify dirs in-place to avoid descending into excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDE_DIRS
                and not d.startswith(".review")
                and not d.startswith(".judge-review")
            ]

            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR).as_posix()

                if is_excluded(rel_path):
                    continue

                zf.write(full_path, arcname=rel_path)
                packed_files.append(rel_path)

    archive_size_bytes = archive_path.stat().st_size
    archive_size_mb = archive_size_bytes / (1024 * 1024)

    print(f"\n[Packaging] Archive generated successfully:")
    print(f"  - Target: {archive_path}")
    print(f"  - Total Files: {len(packed_files):,}")
    print(f"  - Archive Size: {archive_size_mb:.2f} MB ({archive_size_bytes:,} bytes)")

    # Inspection & Secret Verification
    print("\n[Inspection] Auditing packed archive contents for prohibited artifacts...")
    prohibited_found = []
    with zipfile.ZipFile(archive_path, "r") as zf:
        for name in zf.namelist():
            # Check prohibited filenames
            if name.endswith(".db") or name.endswith("-wal") or name.endswith("-shm"):
                prohibited_found.append(f"Prohibited DB file: {name}")
            if name == ".env" or name.startswith(".env.") and not name.endswith(".env.example"):
                prohibited_found.append(f"Prohibited secret file: {name}")
            if "node_modules/" in name:
                prohibited_found.append(f"Prohibited vendor dir: {name}")

            # Scan text files for exposed API keys
            if name.endswith((".py", ".json", ".ts", ".tsx", ".md", ".txt", ".yml", ".yaml")):
                try:
                    content = zf.read(name).decode("utf-8", errors="ignore")
                    for pat in SECRET_PATTERNS:
                        if pat.search(content):
                            prohibited_found.append(f"Potential secret pattern detected in: {name}")
                except Exception:
                    pass

    if prohibited_found:
        print("\n[ERROR] Prohibited artifacts detected in submission package:")
        for item in prohibited_found:
            print(f"  - {item}")
        sys.exit(1)

    print("[SUCCESS] Package verification passed! Zero secrets, databases, or local journals found.")
    print("Archive is 100% clean and ready for judge evaluation.")
    return archive_path


if __name__ == "__main__":
    create_submission_archive()
