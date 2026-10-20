#!/usr/bin/env python3
"""Count prompt characters; optionally inspect Markdown text blocks."""
import argparse
import json
import re
import sys
from pathlib import Path

# Mean expansion factor when equivalent Chinese is rewritten in English.
# Measured on 5 role-description pairs; see references/length-and-language.md.
EN_EXPANSION = 4.16


def inspect_text(text, budget=None, language=None):
    placeholders = re.findall(r"\{\{[^{}\n]+\}\}|【全局固定前缀】|\[GLOBAL_PREFIX\]", text)
    report = {
        "characters": len(text),
        "budget": budget,
        "within_budget": None if budget is None else len(text) <= budget,
        "placeholder_candidates": placeholders,
    }
    if language == "en":
        report["language"] = "en"
        report["equivalent_chinese_characters"] = round(len(text) / EN_EXPANSION)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="UTF-8 prompt character checker, not a token or visual-quality checker")
    parser.add_argument("file", help="UTF-8 input file, or - for stdin")
    parser.add_argument("--budget", type=int, help="User-defined total character budget")
    parser.add_argument("--markdown", action="store_true", help="Inspect fenced text blocks instead of the whole file")
    parser.add_argument("--strict", action="store_true", help="Return 1 for over-budget text or placeholder candidates")
    parser.add_argument("--language", choices=["zh", "en"], help="Prompt language; en adds an equivalent-Chinese length estimate")
    args = parser.parse_args(argv)
    if args.budget is not None and args.budget < 1:
        parser.error("--budget must be positive")
    try:
        raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        parser.exit(2, f"Cannot read UTF-8 input: {exc}\n")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if args.markdown:
        texts = re.findall(r"^```text[^\S\n]*\n(.*?)^```[^\S\n]*(?:\n|$)", raw, re.M | re.S)
        if not texts:
            parser.exit(2, "No fenced text blocks found\n")
        texts = [item[:-1] if item.endswith("\n") else item for item in texts]
    else:
        texts = [raw]
    reports = [dict(index=i + 1, **inspect_text(value, args.budget, args.language)) for i, value in enumerate(texts)]
    print(json.dumps({"counting": "Python len; line endings normalized to LF; not model tokens", "items": reports}, ensure_ascii=False, indent=2))
    failed = any(item["within_budget"] is False or item["placeholder_candidates"] for item in reports)
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
