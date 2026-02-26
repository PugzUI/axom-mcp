"""Analyze tool handler for Axom MCP.

This module handles analysis operations:
- debug: Troubleshoot issues, investigate errors
- review: Code review, quality assessment
- audit: Security audit, compliance check
- refactor: Refactoring suggestions
- test: Test coverage analysis
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..schemas import AnalyzeInput

logger = logging.getLogger(__name__)


def _validate_path(target: str) -> Path:
    """Validate path is within allowed directories."""
    path = Path(target).resolve()

    allowed_bases = [
        Path(os.getcwd()).resolve(),
        Path.home(),
    ]

    for base in allowed_bases:
        try:
            path.relative_to(base)
            return path
        except ValueError:
            continue

    raise ValueError(f"Path {target} is outside allowed directories")


async def handle_analyze(arguments: dict[str, Any]) -> str:
    """Handle axom_mcp_analyze tool calls.

    Args:
        arguments: Tool arguments containing analysis type and parameters

    Returns:
        JSON string with analysis result
    """
    # Validate input
    input_data = AnalyzeInput(**arguments)
    analysis_type = input_data.type
    target = input_data.target
    focus = input_data.focus
    depth = input_data.depth or "medium"
    output_format = input_data.output_format or "summary"

    try:
        # Check if target is a file path or code content
        target_path = None
        code_content = None

        try:
            target_path = _validate_path(target)
            # If path exists and is a file, read it; otherwise treat as code content
            if target_path.exists() and target_path.is_file():
                code_content = target_path.read_text(encoding="utf-8", errors="replace")
            else:
                # Path is valid but file doesn't exist - treat as code content
                code_content = target
        except ValueError:
            # Target is code content, not a file path
            code_content = target

        if code_content is None:
            return json.dumps({"error": f"Could not read target: {target}"})

        # Perform analysis based on type
        if analysis_type == "debug":
            result = await _analyze_debug(code_content, focus, depth)
        elif analysis_type == "review":
            result = await _analyze_review(code_content, focus, depth)
        elif analysis_type == "audit":
            result = await _analyze_audit(code_content, focus, depth)
        elif analysis_type == "refactor":
            result = await _analyze_refactor(code_content, focus, depth)
        elif analysis_type == "test":
            result = await _analyze_test(code_content, focus, depth)
        else:
            return json.dumps({"error": f"Unknown analysis type: {analysis_type}"})

        # Format output
        if output_format == "detailed":
            return json.dumps(result, indent=2)
        elif output_format == "actionable":
            return _format_actionable(result)
        else:
            return json.dumps(
                {
                    "success": result.get("success", True),
                    "type": analysis_type,
                    "target": str(target_path) if target_path else "code",
                    "focus": focus if focus else "general",
                    "issues_found": result.get("issues_found", False),
                    "summary": result.get("summary", ""),
                    "recommendations": result.get("recommendations", []),
                }
            )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return json.dumps({"error": str(e)})


async def _analyze_debug(code: str, focus: str | None, depth: str) -> dict[str, Any]:
    """Perform debug analysis."""
    issues = []

    # Common error patterns
    error_patterns = [
        (
            r"\bException\b",
            "Generic exception - consider using specific exception type",
        ),
        (r"\bprint\s*\(", "Debug print statement found"),
        (r"\bTODO\b", "TODO comment found - may indicate incomplete code"),
        (r"\bFIXME\b", "FIXME comment found - indicates known issue"),
        (r"\bXXX\b", "XXX comment found - indicates problematic code"),
        (r"\bHACK\b", "HACK comment found - indicates workaround"),
        (r"except\s*:", "Bare except clause - catches all exceptions"),
        (
            r"except\s+Exception\s*:",
            "Catches generic Exception - may hide specific errors",
        ),
        (r"pass\s*$", "Empty block - may indicate missing implementation"),
    ]

    for pattern, message in error_patterns:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[: match.start()].count("\n") + 1
            issues.append(
                {
                    "line": line_num,
                    "type": "debug",
                    "message": message,
                    "severity": (
                        "warning" if "TODO" in message or "FIXME" in message else "info"
                    ),
                }
            )

    return {
        "success": True,
        "type": "debug",
        "issues_found": len(issues) > 0,
        "issues": issues,
        "summary": f"Found {len(issues)} potential debug issues",
        "recommendations": (
            [i["message"] for i in issues[:5]] if issues else ["No debug issues found"]
        ),
    }


async def _analyze_review(code: str, focus: str | None, depth: str) -> dict[str, Any]:
    """Perform code review analysis."""
    issues = []

    # Code quality patterns
    quality_patterns = [
        (r"^\s*def\s+\w+\s*\([^)]*\)\s*:", "Function missing docstring", "docstring"),
        (r"^\s*class\s+\w+\s*:", "Class missing docstring", "docstring"),
        (r"\bglobal\s+\w+", "Global variable usage - consider refactoring", "scope"),
        (
            r"\blambda\s*:",
            "Lambda expression - consider named function for clarity",
            "readability",
        ),
        (r"if\s+[^:]+\s*:\s*pass", "Empty if block", "logic"),
        (r"for\s+[^:]+\s*:\s*pass", "Empty for loop", "logic"),
        (r"while\s+[^:]+\s*:\s*pass", "Empty while loop", "logic"),
    ]

    for pattern, message, category in quality_patterns:
        matches = re.finditer(pattern, code, re.MULTILINE)
        for match in matches:
            line_num = code[: match.start()].count("\n") + 1
            issues.append(
                {
                    "line": line_num,
                    "type": category,
                    "message": message,
                    "severity": "info",
                }
            )

    # Check for long functions
    function_pattern = r"def\s+(\w+)\s*\([^)]*\)\s*:"
    for match in re.finditer(function_pattern, code):
        func_name = match.group(1)
        func_start = match.start()
        # Simple heuristic: count lines until next def or end
        remaining = code[func_start:]
        next_def = re.search(r"\ndef\s+", remaining[1:])
        func_content = remaining[: next_def.start() + 1] if next_def else remaining
        func_lines = func_content.count("\n")
        if func_lines > 50:
            issues.append(
                {
                    "line": code[:func_start].count("\n") + 1,
                    "type": "complexity",
                    "message": f"Function '{func_name}' is {func_lines} lines - consider breaking down",
                    "severity": "warning",
                }
            )

    return {
        "success": True,
        "type": "review",
        "issues_found": len(issues) > 0,
        "issues": issues,
        "summary": f"Found {len(issues)} code quality issues",
        "recommendations": (
            list({i["message"] for i in issues[:5]}) if issues else ["Code looks good!"]
        ),
    }


async def _analyze_audit(code: str, focus: str | None, depth: str) -> dict[str, Any]:
    """Perform security audit analysis."""
    issues = []

    # Security patterns
    security_patterns = [
        (r"eval\s*\(", "eval() is dangerous - can execute arbitrary code", "critical"),
        (r"exec\s*\(", "exec() is dangerous - can execute arbitrary code", "critical"),
        (r"__import__\s*\(", "Dynamic import - potential security risk", "warning"),
        (
            r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True",
            "Shell=True in subprocess - command injection risk",
            "critical",
        ),
        (r"os\.system\s*\(", "os.system() - command injection risk", "critical"),
        (r"pickle\.loads?\s*\(", "pickle is unsafe for untrusted data", "warning"),
        (r"marshal\.loads?\s*\(", "marshal is unsafe for untrusted data", "warning"),
        (r"yaml\.load\s*\([^)]*\)", "yaml.load() without Loader - unsafe", "warning"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password found", "critical"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key found", "critical"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret found", "critical"),
        (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token found", "critical"),
        (
            r"SELECT\s+.*\+",
            "Potential SQL injection - string concatenation in query",
            "critical",
        ),
        (
            r"INSERT\s+.*\+",
            "Potential SQL injection - string concatenation in query",
            "critical",
        ),
        (
            r"UPDATE\s+.*\+",
            "Potential SQL injection - string concatenation in query",
            "critical",
        ),
        (
            r"DELETE\s+.*\+",
            "Potential SQL injection - string concatenation in query",
            "critical",
        ),
    ]

    for pattern, message, severity in security_patterns:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[: match.start()].count("\n") + 1
            issues.append(
                {
                    "line": line_num,
                    "type": "security",
                    "message": message,
                    "severity": severity,
                }
            )

    # Sort by severity
    issues.sort(key=lambda x: 0 if x["severity"] == "critical" else 1)

    return {
        "success": True,
        "type": "audit",
        "issues_found": len(issues) > 0,
        "issues": issues,
        "summary": f"Found {len(issues)} security issues ({sum(1 for i in issues if i['severity'] == 'critical')} critical)",
        "recommendations": (
            [i["message"] for i in issues[:5]]
            if issues
            else ["No security issues found"]
        ),
    }


async def _analyze_refactor(code: str, focus: str | None, depth: str) -> dict[str, Any]:
    """Perform refactoring analysis."""
    suggestions = []

    # Refactoring patterns
    refactor_patterns = [
        (
            r"(\bif\s+[^:]+\s*:\s*\n\s*)(if\s+)",
            "Nested if statements - consider combining conditions",
        ),
        (
            r"(\bfor\s+[^:]+\s*:\s*\n\s*)(for\s+)",
            "Nested loops - consider extracting method",
        ),
        (
            r"(\bwhile\s+[^:]+\s*:\s*\n\s*)(while\s+)",
            "Nested while loops - consider extracting method",
        ),
        (r"^\s{8,}", "Deep indentation - consider extracting method"),
    ]

    for pattern, message in refactor_patterns:
        matches = re.finditer(pattern, code, re.MULTILINE)
        for match in matches:
            line_num = code[: match.start()].count("\n") + 1
            suggestions.append(
                {
                    "line": line_num,
                    "type": "refactor",
                    "message": message,
                    "severity": "info",
                }
            )

    # Check for duplicate code (simple heuristic)
    lines = code.split("\n")
    line_counts: dict[str, list[int]] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            if stripped not in line_counts:
                line_counts[stripped] = []
            line_counts[stripped].append(i + 1)

    for _line_text, occurrences in line_counts.items():
        if len(occurrences) > 2:
            suggestions.append(
                {
                    "line": occurrences[0],
                    "type": "duplicate",
                    "message": f"Code appears to be duplicated on lines: {occurrences}",
                    "severity": "info",
                }
            )

    return {
        "success": True,
        "type": "refactor",
        "issues_found": len(suggestions) > 0,
        "issues": suggestions,
        "summary": f"Found {len(suggestions)} refactoring opportunities",
        "recommendations": (
            [s["message"] for s in suggestions[:5]]
            if suggestions
            else ["Code structure looks good!"]
        ),
    }


async def _analyze_test(code: str, focus: str | None, depth: str) -> dict[str, Any]:
    """Perform test coverage analysis."""
    issues = []

    # Test patterns
    test_patterns = [
        (r"def\s+test_\w+\s*\(", "Test function found"),
        (r"assert\s+", "Assertion found"),
        (r"@pytest", "pytest decorator found"),
        (r"@unittest", "unittest decorator found"),
        (r"import\s+unittest", "unittest module imported"),
        (r"import\s+pytest", "pytest module imported"),
    ]

    test_indicators = 0
    for pattern, message in test_patterns:
        matches = list(re.finditer(pattern, code))
        if matches:
            test_indicators += len(matches)
            for match in matches:
                line_num = code[: match.start()].count("\n") + 1
                issues.append(
                    {
                        "line": line_num,
                        "type": "test",
                        "message": message,
                        "severity": "info",
                    }
                )

    # Check for missing test patterns
    if "def " in code and test_indicators == 0:
        issues.append(
            {
                "line": 1,
                "type": "test",
                "message": "No test functions found - consider adding tests",
                "severity": "warning",
            }
        )

    return {
        "success": True,
        "type": "test",
        "issues_found": test_indicators == 0,
        "issues": issues,
        "summary": f"Found {test_indicators} test indicators",
        "recommendations": (
            ["Add more test coverage"]
            if test_indicators < 3
            else ["Good test coverage!"]
        ),
    }


def _format_actionable(result: dict[str, Any]) -> str:
    """Format result as actionable items."""
    lines = []
    lines.append(f"## Analysis: {result.get('type', 'unknown')}")
    lines.append(f"**Summary:** {result.get('summary', 'No summary')}")
    lines.append("")

    recommendations = result.get("recommendations", [])
    if recommendations:
        lines.append("### Action Items:")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

    issues = result.get("issues", [])
    if issues:
        lines.append("")
        lines.append("### Issues Found:")
        for issue in issues[:10]:
            lines.append(
                f"- Line {issue.get('line', '?')}: [{issue.get('severity', 'info')}] {issue.get('message', '')}"
            )

    return "\n".join(lines)
