#!/usr/bin/env python3
"""Compares vanilla and Pumpkin results of the minehouse-parity GameTests.

usage: compare.py <vanilla-junit.xml> <pumpkin.json> [known-gaps.txt]

Exit code 1 when:
  - a test fails on vanilla (the test itself is wrong),
  - a test fails on Pumpkin and is not in known-gaps.txt (regression).
A known gap that passes is only reported (mob AI is random, so a half-done
behaviour can pass some runs); remove it from the list once it keeps passing.
A `~` prefix marks gaps already seen passing on some runs.
Writes a Markdown table to $GITHUB_STEP_SUMMARY when it is set.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def vanilla_results(path):
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        out[case.get("name")] = case.find("failure") is None and case.find("error") is None
    return out


def main():
    vanilla = vanilla_results(sys.argv[1])
    pumpkin = {r["test"]: r for r in json.loads(Path(sys.argv[2]).read_text())}
    gaps_file = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).with_name("known-gaps.txt")
    lines = [l.strip() for l in gaps_file.read_text().splitlines() if l.strip() and not l.startswith("#")]
    flaky = {l[1:].strip() for l in lines if l.startswith("~")}
    gaps = {l.lstrip("~").strip() for l in lines}

    rows, errors, notes = [], [], []
    for test in sorted(set(vanilla) | set(pumpkin)):
        v = vanilla.get(test)
        p = pumpkin.get(test, {}).get("passed")
        if v is None:
            errors.append(f"{test}: did not run on vanilla")
        elif not v:
            errors.append(f"{test}: fails on vanilla, fix the test")
        if p is None:
            errors.append(f"{test}: did not run on Pumpkin")
        elif not p and test not in gaps:
            errors.append(f"{test}: fails on Pumpkin (regression, or add it to known-gaps.txt)")
        elif p and test in gaps and test not in flaky:
            notes.append(f"{test}: passed on Pumpkin this run; if it keeps passing, remove it from known-gaps.txt")
        mark = lambda x: "✅" if x else ("❌" if x is False else "—")
        note = "; ".join(m for m in pumpkin.get(test, {}).get("messages", []) if "failed" in m)
        rows.append(f"| `{test}` | {mark(v)} | {mark(p)} | {'unstable gap' if test in flaky else 'known gap' if test in gaps else ''} {note} |")

    passed = sum(1 for r in pumpkin.values() if r["passed"])
    summary = [
        f"### Vanilla parity: Pumpkin passes {passed} of {len(pumpkin)}",
        "",
        "| Test | Vanilla 26.3 | Pumpkin | Notes |",
        "|---|---|---|---|",
        *rows,
    ]
    if notes:
        summary += ["", "**Known gaps that passed:**", *[f"- {n}" for n in notes]]
    if errors:
        summary += ["", "**Problems:**", *[f"- {e}" for e in errors]]
    text = "\n".join(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
