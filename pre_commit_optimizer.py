#!/usr/bin/env python3
"""Pre-Commit Pattern Recognition & Optimization Overlay.

Runs as part of the git-push workflow BEFORE committing. Analyzes staged
diffs using the best available LLM and writes a structured Markdown report.

Usage:
    python pre_commit_optimizer.py
    python pre_commit_optimizer.py --diff-only   # Print diff without analysis
    python pre_commit_optimizer.py --no-report   # Print to terminal only

Exit codes:
    0  always (never blocks a commit)
"""

import os
import sys
import asyncio
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an elite software architect reviewing code changes before they are committed.

Your job is to identify a SHORT list (3-7 items max) of optimization opportunities
that are **meaningful and additive** — improvements that genuinely increase quality,
performance, or maintainability — WITHOUT introducing undue complexity.

### Filtering rules (apply strictly):
- INCLUDE: changes that are simple to implement but provide clear value (e.g., making a function async, adding a missing index, extracting a reused literal to a constant)
- INCLUDE: patterns that deviate from the established codebase conventions visible in the diff
- INCLUDE: potential bugs or silent failure modes in the changed code
- EXCLUDE: stylistic nitpicks that don't affect correctness or readability
- EXCLUDE: large architectural refactors that would add significant complexity
- EXCLUDE: suggestions for things NOT changed in this diff
- EXCLUDE: anything already handled in tests visible in the diff

### Output format (strict Markdown, no preamble):

## Optimization Report — <ISO date>

### ✅ What's Good
One sentence summary of the strongest positive patterns in this change.

### 🎯 High-Value Suggestions
| Priority | File | Suggestion | Complexity Cost |
|----------|------|------------|-----------------|
| 🔴 Critical | file.py | ... | Minimal |
| 🟡 Worth Doing | file.py | ... | Low |
| 🟢 Nice-to-Have | file.py | ... | None |

### ⚠️ Patterns to Watch
Any recurring patterns in this diff that, if continued, could cause problems. Max 3 bullets.

### 💡 Architecture Alignment
One sentence: does this change align with or drift from the established architecture?
"""

USER_TEMPLATE = """Here are the staged changes ready to be committed:

```diff
{diff}
```

Analyze them against the rules in your system prompt and produce the structured report.
"""

# ── Provider ──────────────────────────────────────────────────────────────────

async def get_analysis(diff: str) -> str:
    """Send the diff to the best available LLM and return the analysis."""
    sys.path.insert(0, str(Path(__file__).parent))

    from src.app.mcp.providers import get_provider, ProviderMessage

    # Fallback chain: Claude → Gemini → Ollama
    if os.getenv("ANTHROPIC_API_KEY"):
        provider = get_provider("claude")
    elif os.getenv("GOOGLE_API_KEY"):
        provider = get_provider("gemini")
    else:
        provider = get_provider("ollama")

    messages = [
        ProviderMessage(role="system", content=SYSTEM_PROMPT),
        ProviderMessage(role="user", content=USER_TEMPLATE.format(diff=diff)),
    ]

    response = await provider.complete(messages)
    return response.content


# ── Git integration ───────────────────────────────────────────────────────────

def get_staged_diff() -> str:
    """Return the staged diff. Empty string if nothing staged."""
    result = subprocess.run(
        ["git", "diff", "--staged", "--unified=3"],
        capture_output=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr}")
    return (result.stdout or "").strip()


def get_staged_files() -> list[str]:
    """Return list of staged filenames."""
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        capture_output=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff --name-only failed: {result.stderr}")
    return [f.strip() for f in (result.stdout or "").strip().splitlines() if f.strip()]


# Noise file patterns to filter before sending to LLM
_NOISE_SUFFIXES = (
    ".lock", "-lock.json", ".min.js", ".min.css",
    ".map", ".svg", ".png", ".jpg", ".jpeg", ".gif",
)

def filter_diff(diff: str, files: list[str]) -> str:
    """Strip hunks for noise files (lock files, minified assets) to save tokens."""
    if not diff:
        return diff
    noise_files = {f for f in files if any(f.endswith(s) for s in _NOISE_SUFFIXES)}
    if not noise_files:
        return diff
    lines = []
    skip = False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            skip = any(nf in line for nf in noise_files)
        if not skip:
            lines.append(line)
    return "".join(lines)


# ── Report storage ────────────────────────────────────────────────────────────

def save_report(content: str) -> Path:
    """Save report to docs/optimizer_reports/ and return the path."""
    reports_dir = Path(__file__).parent / "docs" / "optimizer_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Include seconds to prevent collision on rapid commits
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = reports_dir / f"{timestamp}.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def truncate_diff(diff: str, max_chars: int = 12000) -> str:
    """Truncate very large diffs to keep within context limits."""
    if len(diff) <= max_chars:
        return diff
    half = max_chars // 2
    truncated = diff[:half]
    truncated += f"\n\n... [diff truncated — {len(diff) - max_chars} chars omitted] ...\n\n"
    truncated += diff[-half:]
    return truncated


# ── Entry point ───────────────────────────────────────────────────────────────

def print_banner(files: list[str]) -> None:
    print("\n" + "═" * 60)
    print("  🔍  Pre-Commit Optimizer")
    print("═" * 60)
    print(f"  Staged files ({len(files)}):")
    for f in files:
        print(f"    · {f}")
    print("═" * 60 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-commit optimization overlay")
    parser.add_argument("--diff-only", action="store_true", help="Print diff and exit")
    parser.add_argument("--no-report", action="store_true", help="Skip saving the report file")
    args = parser.parse_args()

    diff = get_staged_diff()
    files = get_staged_files()

    if not diff:
        print("ℹ️  No staged changes found — skipping optimizer.")
        return

    print_banner(files)

    if args.diff_only:
        print(diff)
        return

    print("⚡  Analyzing changes...\n")

    filtered = filter_diff(diff, files)
    if not filtered.strip():
        print("ℹ️  All staged changes are in noise files — skipping optimizer.")
        return

    try:
        analysis = await get_analysis(truncate_diff(filtered))
    except Exception as e:
        print(f"⚠️  Optimizer skipped (LLM error): {e}")
        print("    Proceeding with commit as normal.\n")
        return

    print(analysis)
    print()

    if not args.no_report:
        # Prepend file list to the saved report
        header = f"# Pre-Commit Optimizer Report\n\n**Files:** {', '.join(files)}\n\n---\n\n"
        report_path = save_report(header + analysis)
        print(f"📝  Report saved → {report_path.relative_to(Path(__file__).parent)}")

    print("\n" + "═" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
