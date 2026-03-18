#!/usr/bin/env python3
"""
Repo Knowledge Updater
======================

CLI utility to maintain shared/repo-knowledge.md — the single source of truth
for reusable utilities, frameworks, and conventions in the project.

Usage:
    python update_repo_knowledge.py list                     # Show all quick-lookup entries
    python update_repo_knowledge.py sections                 # Show all sections with line numbers
    python update_repo_knowledge.py find <term>              # Find all mentions of a term
    python update_repo_knowledge.py remove <term>            # Remove all rows mentioning a term from the quick-lookup table
    python update_repo_knowledge.py add "<need>" "<use>"     # Add a new quick-lookup entry
    python update_repo_knowledge.py validate                 # Check for inconsistencies

Examples:
    python update_repo_knowledge.py remove "Query"
    python update_repo_knowledge.py add "Send platform event" "EventPublisherService.publish(events)"
    python update_repo_knowledge.py find "Logr"
"""

import argparse
import re
import sys
from pathlib import Path

REPO_KNOWLEDGE = Path(__file__).parent / "repo-knowledge.md"

QUICK_LOOKUP_HEADER = '## Quick Lookup: "When you need X, use Y"'
TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$")
SECTION_RE = re.compile(r"^(#{2,3})\s+(.+)$")


def read_doc() -> str:
    if not REPO_KNOWLEDGE.exists():
        print(f"Error: {REPO_KNOWLEDGE} not found.", file=sys.stderr)
        sys.exit(1)
    return REPO_KNOWLEDGE.read_text(encoding="utf-8")


def write_doc(content: str) -> None:
    REPO_KNOWLEDGE.write_text(content, encoding="utf-8")


def parse_quick_lookup(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return list of (line_index, need, use_this) from the quick-lookup table."""
    entries = []
    in_table = False
    header_seen = False
    for i, line in enumerate(lines):
        if QUICK_LOOKUP_HEADER in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            m = TABLE_ROW_RE.match(line)
            if m:
                col1, col2 = m.group(1).strip(), m.group(2).strip()
                if col1.startswith("-") or col1 == "When you need to...":
                    header_seen = True
                    continue
                if header_seen:
                    entries.append((i, col1, col2))
        elif in_table and not line.strip().startswith("|") and line.strip() == "---":
            break
        elif in_table and line.strip() == "" and header_seen:
            continue
        elif in_table and not line.strip().startswith("|") and header_seen:
            break
    return entries


def cmd_list(args: argparse.Namespace) -> None:
    """Show all quick-lookup entries."""
    content = read_doc()
    lines = content.splitlines()
    entries = parse_quick_lookup(lines)
    if not entries:
        print("No quick-lookup entries found.")
        return
    print(f"{'#':<4} {'When you need to...':<45} {'Use this'}")
    print(f"{'─'*3}  {'─'*44} {'─'*50}")
    for idx, (_, need, use) in enumerate(entries, 1):
        print(f"{idx:<4} {need:<45} {use}")
    print(f"\nTotal: {len(entries)} entries")


def cmd_sections(args: argparse.Namespace) -> None:
    """Show all sections with line numbers."""
    content = read_doc()
    for i, line in enumerate(content.splitlines(), 1):
        m = SECTION_RE.match(line)
        if m:
            depth = len(m.group(1))
            indent = "  " * (depth - 2)
            print(f"  L{i:<5} {indent}{m.group(2)}")


def cmd_find(args: argparse.Namespace) -> None:
    """Find all lines mentioning a term."""
    content = read_doc()
    term = args.term.lower()
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if term in line.lower():
            matches.append((i, line.rstrip()))
    if not matches:
        print(f"No mentions of '{args.term}' found.")
        return
    print(f"Found {len(matches)} mention(s) of '{args.term}':\n")
    for lineno, line in matches:
        print(f"  L{lineno:<5} {line}")


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove all quick-lookup rows mentioning a term."""
    content = read_doc()
    lines = content.splitlines()
    entries = parse_quick_lookup(lines)
    term = args.term.lower()

    to_remove = [i for i, need, use in entries if term in need.lower() or term in use.lower()]
    if not to_remove:
        print(f"No quick-lookup entries mention '{args.term}'.")
        return

    print(f"Will remove {len(to_remove)} row(s) from quick-lookup table:")
    for idx in to_remove:
        print(f"  L{idx+1}: {lines[idx].rstrip()}")

    if not args.yes:
        confirm = input("\nProceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    new_lines = [line for i, line in enumerate(lines) if i not in to_remove]
    write_doc("\n".join(new_lines) + "\n")
    print(f"Removed {len(to_remove)} row(s). Quick-lookup table updated.")
    print(f"\nTip: Detailed sections referencing '{args.term}' were NOT removed.")
    print("     Review and update those sections manually if needed.")

    # Show remaining mentions for awareness
    remaining = read_doc()
    remaining_count = sum(1 for line in remaining.splitlines() if term in line.lower())
    if remaining_count:
        print(f"\n     '{args.term}' still appears in {remaining_count} other line(s) in the document.")


def cmd_add(args: argparse.Namespace) -> None:
    """Add a new quick-lookup entry."""
    content = read_doc()
    lines = content.splitlines()
    entries = parse_quick_lookup(lines)

    if not entries:
        print("Error: Could not locate quick-lookup table.", file=sys.stderr)
        sys.exit(1)

    # Find the last table row index
    last_row_idx = entries[-1][0]

    new_row = f"| {args.need} | {args.use} |"

    # Check for duplicate
    for _, need, use in entries:
        if args.need.lower() in need.lower() and args.use.lower() in use.lower():
            print(f"Warning: Similar entry already exists: '{need}' → '{use}'")
            if not args.yes:
                confirm = input("Add anyway? [y/N] ").strip().lower()
                if confirm != "y":
                    print("Aborted.")
                    return
            break

    lines.insert(last_row_idx + 1, new_row)
    write_doc("\n".join(lines) + "\n")
    print(f"Added: {new_row}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Check for inconsistencies between quick-lookup and detailed sections."""
    content = read_doc()
    lines = content.splitlines()
    entries = parse_quick_lookup(lines)

    # Extract class names from quick-lookup "Use this" column
    class_re = re.compile(r"`(\w+(?:\.\w+)?(?:\(\))?)`")
    lookup_classes = set()
    for _, _, use in entries:
        for m in class_re.finditer(use):
            name = m.group(1).rstrip("()")
            # Skip common non-class tokens
            if name not in ("true", "false", "null", "insert", "callout"):
                lookup_classes.add(name)

    # Check which classes appear in detailed sections (below the table)
    table_end = entries[-1][0] if entries else 0
    detail_text = "\n".join(lines[table_end:]).lower()

    issues = []
    for cls in sorted(lookup_classes):
        if cls.lower() not in detail_text:
            issues.append(f"  '{cls}' in quick-lookup but not documented in any detail section")

    if issues:
        print(f"Found {len(issues)} potential issue(s):\n")
        for issue in issues:
            print(issue)
    else:
        print("All quick-lookup entries have corresponding detail sections. ✓")

    print(f"\nQuick-lookup: {len(entries)} entries, {len(lookup_classes)} unique class/utility references")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Maintain shared/repo-knowledge.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show all quick-lookup entries")
    sub.add_parser("sections", help="Show all sections with line numbers")

    p_find = sub.add_parser("find", help="Find all mentions of a term")
    p_find.add_argument("term", help="Term to search for")

    p_remove = sub.add_parser("remove", help="Remove quick-lookup rows mentioning a term")
    p_remove.add_argument("term", help="Term to match (case-insensitive)")
    p_remove.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    p_add = sub.add_parser("add", help="Add a new quick-lookup entry")
    p_add.add_argument("need", help='The "When you need to..." text')
    p_add.add_argument("use", help='The "Use this" text')
    p_add.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    sub.add_parser("validate", help="Check for inconsistencies")

    args = parser.parse_args()
    commands = {
        "list": cmd_list,
        "sections": cmd_sections,
        "find": cmd_find,
        "remove": cmd_remove,
        "add": cmd_add,
        "validate": cmd_validate,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
