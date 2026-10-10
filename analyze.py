#!/usr/bin/env python3
"""Lightweight repository intelligence analyzer for GitHub Actions.

Collects LOC (via scc), git stats, basic README check, optional secret scan,
and evaluates simple acceptance gates. Writes report.json.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd, check=True, capture=True):
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=capture,
        text=True,
    )
    if check and result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def scc_summary():
    """Return total code lines and file count from scc JSON."""
    result = run(["scc", "--format", "json", "."], check=False)
    if result.returncode != 0:
        print("scc failed, falling back to zeros", file=sys.stderr)
        return 0, 0, {}
    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return 0, 0, {}
    total_code = 0
    total_files = 0
    by_lang = {}
    if isinstance(data, list):
        for item in data:
            code = int(item.get("Code", 0) or 0)
            files = int(item.get("Count", 0) or 0)
            total_code += code
            total_files += files
            name = item.get("Name") or "Unknown"
            by_lang[name] = {"code": code, "files": files}
    return total_code, total_files, by_lang


def git_stats():
    """Return commit count, contributor count, and approximate span in months."""
    commits = 0
    contributors = 0
    span_months = 0
    first = None
    last = None

    log = run(
        ["git", "log", "--pretty=format:%aI|%aN", "--all"],
        check=False,
    )
    if log.returncode != 0 or not log.stdout.strip():
        return commits, contributors, span_months, first, last

    authors = set()
    dates = []
    for line in log.stdout.splitlines():
        if "|" not in line:
            continue
        date_s, author = line.split("|", 1)
        authors.add(author.strip())
        try:
            dates.append(datetime.fromisoformat(date_s.replace("Z", "+00:00")))
        except ValueError:
            continue

    commits = len(dates)
    contributors = len(authors)
    if dates:
        first = min(dates)
        last = max(dates)
        delta = last - first
        span_months = round(delta.days / 30.44, 1)

    return commits, contributors, span_months, (
        first.isoformat() if first else None
    ), (last.isoformat() if last else None)


def readme_ok(min_chars=200):
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = Path(name)
        if p.is_file():
            text = p.read_text(errors="replace")
            return len(text.strip()) >= min_chars, len(text.strip()), name
    return False, 0, None


def secret_scan():
    """Run gitleaks if available. Returns finding count or None if skipped."""
    if os.environ.get("SCAN_SECRETS", "true").lower() not in ("1", "true", "yes"):
        return None
    result = run(
        ["gitleaks", "detect", "--source", ".", "--report-format", "json", "--report-path", "gitleaks-report.json", "--no-banner", "--exit-code", "0"],
        check=False,
    )
    report = Path("gitleaks-report.json")
    if report.is_file():
        try:
            findings = json.loads(report.read_text() or "[]")
            return len(findings) if isinstance(findings, list) else 0
        except json.JSONDecodeError:
            return 0
    return 0


def main():
    min_files = int(os.environ.get("MIN_SOURCE_FILES", "20"))
    min_loc = int(os.environ.get("MIN_LOC", "5000"))
    min_contrib = int(os.environ.get("MIN_CONTRIBUTORS", "2"))
    min_commits = int(os.environ.get("MIN_COMMITS", "100"))
    min_months = float(os.environ.get("MIN_MONTHS", "6"))
    require_readme = os.environ.get("REQUIRE_README", "true").lower() in ("1", "true", "yes")

    loc, source_files, by_lang = scc_summary()
    commits, contributors, span_months, first, last = git_stats()
    has_readme, readme_chars, readme_name = readme_ok()
    secrets = secret_scan()

    failures = []
    if source_files < min_files:
        failures.append(f"source files {source_files} < {min_files}")
    if loc < min_loc:
        failures.append(f"LOC {loc} < {min_loc}")
    if contributors < min_contrib:
        failures.append(f"contributors {contributors} < {min_contrib}")
    if commits < min_commits:
        failures.append(f"commits {commits} < {min_commits}")
    if span_months < min_months:
        failures.append(f"span {span_months} months < {min_months}")
    if require_readme and not has_readme:
        failures.append(f"README missing or shorter than 200 chars (got {readme_chars})")

    passed = len(failures) == 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "ref": os.environ.get("GITHUB_REF", ""),
        "sha": os.environ.get("GITHUB_SHA", ""),
        "loc": loc,
        "source_files": source_files,
        "languages": by_lang,
        "commits": commits,
        "contributors": contributors,
        "span_months": span_months,
        "first_commit": first,
        "last_commit": last,
        "readme": {"present": has_readme, "chars": readme_chars, "file": readme_name},
        "secret_findings": secrets,
        "gates": {
            "min_source_files": min_files,
            "min_loc": min_loc,
            "min_contributors": min_contrib,
            "min_commits": min_commits,
            "min_months": min_months,
            "require_readme": require_readme,
        },
        "failures": failures,
        "passed": passed,
    }

    Path("report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    # GitHub Actions outputs
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"report_path=report.json\n")
            f.write(f"passed={str(passed).lower()}\n")
            f.write(f"loc={loc}\n")

    fail_on_gates = os.environ.get("FAIL_ON_GATES", "false").lower() in ("1", "true", "yes")
    if fail_on_gates and not passed:
        print("Acceptance gates failed", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
