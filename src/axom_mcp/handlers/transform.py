"""Transform tool handler for Axom MCP.

This module handles transformation operations between formats:
- json: JSON objects and arrays
- yaml: YAML documents
- csv: Comma-separated values
- markdown: Markdown documents
- code: Source code (with language detection)
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from typing import Any

from ..schemas import TransformInput

logger = logging.getLogger(__name__)


async def handle_transform(arguments: dict[str, Any]) -> str:
    """Handle axom_mcp_transform tool calls.

    Args:
        arguments: Tool arguments containing input data and format parameters

    Returns:
        JSON string with transformation result
    """
    # Validate input
    input_data = TransformInput(**arguments)
    input_str = input_data.input
    input_format = input_data.input_format
    output_format = input_data.output_format
    rules = input_data.rules or []
    template = input_data.template

    try:
        # Auto-detect input format if not specified
        if input_format is None:
            input_format = _detect_format(input_str)

        # Parse input to Python object
        parsed = _parse_input(input_str, input_format)

        # Apply transformation rules
        for rule in rules:
            parsed = _apply_rule(parsed, rule)

        # Convert to output format
        result = _format_output(parsed, output_format, template)

        return json.dumps(
            {
                "success": True,
                "input_format": input_format,
                "output_format": output_format,
                "result": result,
            }
        )

    except Exception as e:
        logger.error(f"Transform failed: {e}")
        return json.dumps({"error": str(e)})


def _detect_format(input_str: str) -> str:
    """Auto-detect input format based on content."""
    stripped = input_str.strip()

    # Check for JSON
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            pass

    # Check for YAML (basic heuristics)
    yaml_indicators = [
        r"^\w+:\s*",  # key: value
        r"^-\s+",  # - list item (can be at start of line)
        r"^\s+-\s+",  # - list item (with indentation)
        r"^---\s*$",  # YAML document separator
    ]
    for pattern in yaml_indicators:
        if re.search(pattern, stripped, re.MULTILINE):
            return "yaml"

    # Check for CSV
    lines = stripped.split("\n")
    if len(lines) > 1:
        # Check if all lines have similar number of commas
        comma_counts = [line.count(",") for line in lines[:5]]
        if len(set(comma_counts)) == 1 and comma_counts[0] > 0:
            return "csv"

    # Check for Markdown
    md_indicators = [
        r"^#+\s+",  # Headers
        r"^\*\s+",  # Unordered lists
        r"^\d+\.\s+",  # Ordered lists
        r"\[.*\]\(.*\)",  # Links
        r"```",  # Code blocks
    ]
    for pattern in md_indicators:
        if re.search(pattern, stripped, re.MULTILINE):
            return "markdown"

    # Default to code
    return "code"


def _parse_input(input_str: str, input_format: str) -> Any:
    """Parse input string to Python object."""
    if input_format == "json":
        return json.loads(input_str)

    elif input_format == "yaml":
        try:
            import yaml

            return yaml.safe_load(input_str)
        except ImportError:
            # Fallback: simple YAML parsing for basic structures
            return _parse_simple_yaml(input_str)

    elif input_format == "csv":
        reader = csv.DictReader(io.StringIO(input_str))
        return list(reader)

    elif input_format == "markdown":
        return _parse_markdown(input_str)

    elif input_format == "code":
        return {"code": input_str, "language": _detect_language(input_str)}

    else:
        raise ValueError(f"Unknown input format: {input_format}")


def _parse_simple_yaml(yaml_str: str) -> Any:
    """Simple YAML parser for basic structures."""
    result: dict[str, Any] = {}
    current_key: str | None = None

    for line in yaml_str.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for key: value
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            val_str = parts[1].strip() if len(parts) > 1 else None
            parsed_value: Any = val_str

            if val_str:
                # Try to parse value
                if val_str.lower() == "true":
                    parsed_value = True
                elif val_str.lower() == "false":
                    parsed_value = False
                elif val_str.isdigit():
                    parsed_value = int(val_str)
                elif val_str.replace(".", "").isdigit():
                    parsed_value = float(val_str)
                elif (
                    val_str.startswith('"')
                    and val_str.endswith('"')
                    or val_str.startswith("'")
                    and val_str.endswith("'")
                ):
                    parsed_value = val_str[1:-1]

                result[key] = parsed_value
            else:
                current_key = key
                result[current_key] = {}

        # Check for list item
        elif stripped.startswith("- "):
            value = stripped[2:].strip()
            if current_key:
                if not isinstance(result[current_key], list):
                    result[current_key] = []
                result[current_key].append(value)

    return result


def _parse_markdown(md_str: str) -> dict[str, Any]:
    """Parse markdown to structured data."""
    result: dict[str, Any] = {
        "sections": [],
        "headers": [],
        "lists": [],
        "code_blocks": [],
        "links": [],
    }

    current_section: dict[str, Any] = {"title": None, "content": [], "level": 0}
    in_code_block = False
    code_content: list[str] = []
    code_language = None

    for line in md_str.split("\n"):
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                result["code_blocks"].append(
                    {
                        "language": code_language,
                        "content": "\n".join(code_content),
                    }
                )
                code_content = []
                in_code_block = False
            else:
                in_code_block = True
                code_language = line.strip()[3:].strip() or None
            continue

        if in_code_block:
            code_content.append(line)
            continue

        # Headers
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2)
            result["headers"].append({"level": level, "title": title})
            if current_section["content"]:
                result["sections"].append(current_section)
            current_section = {"title": title, "content": [], "level": level}
            continue

        # Lists
        list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", line)
        if list_match:
            result["lists"].append(
                {
                    "indent": len(list_match.group(1)),
                    "item": list_match.group(3),
                }
            )
            continue

        # Links
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
            result["links"].append(
                {
                    "text": match.group(1),
                    "url": match.group(2),
                }
            )

        # Regular content
        if not in_code_block and line.strip():
            current_section["content"].append(line)

    if current_section["content"]:
        result["sections"].append(current_section)

    return result


def _detect_language(code: str) -> str:
    """Detect programming language from code content."""
    patterns = {
        "python": [
            r"\bdef\s+\w+\s*\(",
            r"\bimport\s+\w+",
            r"\bfrom\s+\w+\s+import",
            r"\bclass\s+\w+:",
        ],
        "javascript": [
            r"\bfunction\s+\w+\s*\(",
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\b=>\s*{",
        ],
        "typescript": [r"\binterface\s+\w+", r"\btype\s+\w+\s*=", r":\s*\w+\s*[;=]"],
        "java": [
            r"\bpublic\s+class\s+",
            r"\bprivate\s+\w+\s+\w+",
            r"\bSystem\.out\.println",
        ],
        "go": [r"\bfunc\s+\w+\s*\(", r"\bpackage\s+\w+", r"\bimport\s*\("],
        "rust": [r"\bfn\s+\w+\s*\(", r"\blet\s+mut\s+", r"\bimpl\s+\w+"],
        "ruby": [r"\bdef\s+\w+", r"\bend\b", r"\bclass\s+\w+", r"\bmodule\s+\w+"],
        "php": [r"<\?php", r"\$\w+\s*=", r"\bfunction\s+\w+\s*\("],
        "c": [r"#include\s*<", r"\bint\s+main\s*\(", r"\bprintf\s*\("],
        "cpp": [
            r"#include\s*<",
            r"\bstd::",
            r"\bclass\s+\w+\s*{",
            r"\bnamespace\s+\w+",
        ],
    }

    for lang, lang_patterns in patterns.items():
        for pattern in lang_patterns:
            if re.search(pattern, code):
                return lang

    return "unknown"


def _apply_rule(data: Any, rule: dict[str, Any]) -> Any:
    """Apply a transformation rule to data."""
    rule_type = rule.get("type")

    if rule_type == "field_mapping":
        # Rename fields
        if isinstance(data, dict):
            mapping = rule.get("mapping", {})
            return {mapping.get(k, k): v for k, v in data.items()}
        elif isinstance(data, list):
            mapping = rule.get("mapping", {})
            return [{mapping.get(k, k): v for k, v in item.items()} for item in data]

    elif rule_type == "filter":
        # Filter fields
        fields = rule.get("fields", [])
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k in fields}
        elif isinstance(data, list):
            return [{k: v for k, v in item.items() if k in fields} for item in data]

    elif rule_type == "sort":
        # Sort array by field
        field = rule.get("field")
        reverse = rule.get("reverse", False)
        if isinstance(data, list) and field:
            return sorted(data, key=lambda x: x.get(field, ""), reverse=reverse)

    elif rule_type == "aggregate":
        # Group and aggregate
        group_by = rule.get("group_by")
        agg_field = rule.get("aggregate_field")
        agg_func = rule.get("function", "count")

        if isinstance(data, list) and group_by:
            groups: dict[Any, list[dict[str, Any]]] = {}
            for item in data:
                key = item.get(group_by)
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)

            result = []
            for key, items in groups.items():
                agg_value = (
                    len(items)
                    if agg_func == "count"
                    else sum(item.get(agg_field, 0) for item in items)
                )
                result.append({group_by: key, agg_func: agg_value})
            return result

    return data


def _format_output(data: Any, output_format: str, template: str | None = None) -> str:
    """Format Python object to output format."""
    if output_format == "json":
        return json.dumps(data, indent=2, default=str)

    elif output_format == "yaml":
        try:
            import yaml

            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            return _format_simple_yaml(data)

    elif output_format == "csv":
        return _format_csv(data)

    elif output_format == "markdown":
        return _format_markdown(data, template)

    elif output_format == "code":
        if isinstance(data, dict) and "code" in data:
            return data["code"]
        return str(data)

    else:
        raise ValueError(f"Unknown output format: {output_format}")


def _format_simple_yaml(data: Any, indent: int = 0) -> str:
    """Format data as simple YAML."""
    lines = []
    prefix = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_format_simple_yaml(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(_format_simple_yaml(item, indent + 1))
            else:
                lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{data}")

    return "\n".join(lines)


def _format_csv(data: Any) -> str:
    """Format data as CSV."""
    if not isinstance(data, list):
        data = [data]

    if not data:
        return ""

    # Get all field names
    if isinstance(data[0], dict):
        fieldnames = list(data[0].keys())
    else:
        fieldnames = ["value"]
        data = [{"value": item} for item in data]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue()


def _format_markdown(data: Any, template: str | None = None) -> str:
    """Format data as Markdown."""
    if template:
        # Simple template substitution
        result = template
        if isinstance(data, dict):
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    lines = []

    if isinstance(data, dict):
        # Format as key-value pairs
        lines.append("# Data")
        lines.append("")
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"## {key}")
                for item in value:
                    lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(f"## {key}")
                for k, v in value.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(f"- **{key}**: {value}")

    elif isinstance(data, list):
        # Format as list
        lines.append("# Items")
        lines.append("")
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"## Item {i}")
                for key, value in item.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            else:
                lines.append(f"{i}. {item}")

    else:
        lines.append(str(data))

    return "\n".join(lines)
