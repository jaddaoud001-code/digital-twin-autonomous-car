"""Cross-language contract tests: C# CSV recorder vs. JSON Schema.

These tests read the Unity source (read-only) and fail if the CSV header or the
number of written values drifts from the contract.
"""

import re

import pytest

from twin_maintenance import contract
from twin_maintenance.paths import csv_recorder_source_path


@pytest.fixture(scope="module")
def csharp_source() -> str:
    return csv_recorder_source_path().read_text(encoding="utf-8")


def _method_body(source: str, signature: str) -> str:
    """Return the brace-delimited body of the first method matching ``signature``."""
    match = re.search(signature, source)
    assert match, f"method not found: {signature}"
    start = source.index("{", match.end())
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"unbalanced braces in {signature}")


def _call_arguments(text: str, call: str) -> list[str]:
    """Split the top-level arguments of the first ``call(`` in ``text``.

    Aware of nested parentheses and C# string literals.
    """
    start = text.index(call) + len(call)
    args: list[str] = []
    depth, current, in_str = 0, [], False
    for ch in text[start:]:
        if in_str:
            current.append(ch)
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                args.append("".join(current).strip())
                return args
            depth -= 1
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    raise AssertionError(f"unterminated call: {call}")


def extract_csv_header(source: str) -> list[str]:
    """Header written in StartRecording(): concatenation of C# string literals."""
    body = _method_body(source, r"void\s+StartRecording\s*\(\s*\)")
    (arg,) = _call_arguments(body, "writer.WriteLine(")
    # Only literals joined by '+' are supported; anything else must fail loudly
    assert re.fullmatch(r'\s*"[^"]*"(\s*\+\s*"[^"]*")*\s*', arg), f"unsupported header: {arg}"
    return "".join(re.findall(r'"([^"]*)"', arg)).split(",")


def test_csharp_header_matches_schema(csharp_source: str) -> None:
    assert extract_csv_header(csharp_source) == contract.columns()


def test_csharp_writes_one_value_per_column(csharp_source: str) -> None:
    body = _method_body(csharp_source, r"void\s+WriteSample\s*\(")
    args = _call_arguments(body, "string.Join(")
    assert args[0] == '","'
    assert len(args) - 1 == len(contract.columns())


def test_header_extractor_detects_missing_comma() -> None:
    # Guard for the extractor itself: a missing comma between literals must be visible
    source = """
    public void StartRecording()
    {
        writer.WriteLine(
            "a,b," +
            "c" +
            "d,e");
    }
    """
    assert extract_csv_header(source) == ["a", "b", "cd", "e"]
