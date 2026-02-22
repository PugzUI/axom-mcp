"""Exec tool handler for Axom MCP.

This module handles execution operations:
- read: Read file contents from allowed directories
- write: Write data to files
- shell: Execute shell commands
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas import ExecInput

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 10_000_000  # 10MB max file size


def _env_flag_enabled(name: str, default: bool = False) -> bool:
    """Return True if env var is set to a truthy value."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _validate_path(target: str) -> Path:
    """Validate path is within allowed directories."""
    # Resolve to absolute path
    path = Path(target).resolve()

    # Define allowed base directories
    allowed_bases = [
        Path(os.getcwd()).resolve(),  # Current working directory
        Path.home(),  # User home directory
    ]

    # Check if path is within any allowed base
    for base in allowed_bases:
        try:
            path.relative_to(base)
            return path
        except ValueError:
            continue

    raise ValueError(f"Path {target} is outside allowed directories")


async def handle_exec(arguments: Dict[str, Any]) -> str:
    """Handle axom_mcp_exec tool calls.
    
    Args:
        arguments: Tool arguments containing operation and parameters
        
    Returns:
        JSON string with operation result
    """
    # Validate input
    input_data = ExecInput(**arguments)
    operation = input_data.operation
    target = input_data.target
    
    try:
        if operation == "read":
            return await _handle_read(target)
        elif operation == "write":
            return await _handle_write(target, input_data.data)
        elif operation == "shell":
            return await _handle_shell(target)
        else:
            return json.dumps({"error": f"Unknown operation: {operation}"})
    except Exception as e:
        logger.error(f"Exec operation failed: {e}")
        return json.dumps({"error": str(e)})


async def _handle_read(target: str) -> str:
    """Read file contents."""
    try:
        path = _validate_path(target)
        
        if not path.exists():
            return json.dumps({"error": f"File not found: {target}"})
        
        if not path.is_file():
            return json.dumps({"error": f"Not a file: {target}"})
        
        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE:
            return json.dumps({
                "error": f"File too large: {target} (max {MAX_FILE_SIZE} bytes)"
            })
        
        # Read file content
        content = path.read_text(encoding="utf-8", errors="replace")
        
        return json.dumps({
            "success": True,
            "operation": "read",
            "target": str(path),
            "content": content,
            "size": len(content),
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return json.dumps({"error": str(e)})


async def _handle_write(target: str, data: Optional[str]) -> str:
    """Write data to file."""
    # Check if write operations are allowed (AXOM_READ_ONLY defaults to False)
    if _env_flag_enabled("AXOM_READ_ONLY", default=False):
        return json.dumps({
            "error": "Write operations disabled. AXOM_READ_ONLY is enabled."
        })
    
    if data is None:
        return json.dumps({"error": "data is required for write operation"})
    
    try:
        path = _validate_path(target)
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        path.write_text(data, encoding="utf-8")
        
        return json.dumps({
            "success": True,
            "operation": "write",
            "target": str(path),
            "size": len(data),
            "message": f"Successfully wrote {len(data)} bytes to {path}",
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return json.dumps({"error": str(e)})


async def _handle_shell(command: str) -> str:
    """Execute shell command."""
    # Check if shell operations are allowed (AXOM_READ_ONLY defaults to False)
    if _env_flag_enabled("AXOM_READ_ONLY", default=False):
        return json.dumps({
            "error": "Shell operations disabled. AXOM_READ_ONLY is enabled."
        })
    
    try:
        # Execute command with timeout
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0  # 60 second timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return json.dumps({
                "error": "Command timed out after 60 seconds",
                "command": command,
            })
        
        # Decode output
        stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
        
        return json.dumps({
            "success": process.returncode == 0,
            "operation": "shell",
            "command": command,
            "exit_code": process.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
        })
    except Exception as e:
        logger.error(f"Failed to execute shell command: {e}")
        return json.dumps({"error": str(e)})


class ChainEngine:
    """Engine for executing chain reactions."""

    def __init__(self, handlers: Optional[Dict[str, Any]] = None):
        self.handlers = handlers or {}

    async def execute_chain(
        self,
        initial_result: Dict[str, Any],
        chain: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a chain of operations."""
        variables = {"_result": initial_result}
        steps = []
        current_result = initial_result

        for step in chain:
            tool_name = step.get("tool")
            args = step.get("args", {})
            condition = step.get("condition")

            # Check condition
            if condition:
                if not self._evaluate_condition(condition, variables):
                    steps.append({
                        "tool": tool_name,
                        "skipped": True,
                        "reason": "Condition not met",
                    })
                    continue

            # Substitute variables in args
            resolved_args = self._substitute_variables(args, variables)

            # Execute tool
            try:
                if tool_name in self.handlers:
                    result = await self.handlers[tool_name](resolved_args)
                    if isinstance(result, str):
                        result = json.loads(result)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                steps.append({
                    "tool": tool_name,
                    "args": resolved_args,
                    "result": result,
                })

                # Update variables for next step
                current_result = result
                variables["_result"] = result

            except Exception as e:
                steps.append({
                    "tool": tool_name,
                    "args": resolved_args,
                    "error": str(e),
                })
                break

        return {
            "success": True,
            "steps": steps,
            "final_result": current_result,
        }

    def _evaluate_condition(
        self, condition: str, variables: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition expression."""
        try:
            # Simple condition evaluation
            # Support: ${_result.property} == value
            pattern = r"\$\{([^}]+)\}\s*==\s*(.+)"
            match = re.match(pattern, condition.strip())
            if match:
                var_path = match.group(1)
                expected = match.group(2).strip().strip("\"'")

                # Get variable value
                value = self._get_variable(var_path, variables)
                return str(value) == expected

            # Support: ${_result.property} (truthy check)
            pattern = r"\$\{([^}]+)\}"
            match = re.match(pattern, condition.strip())
            if match:
                var_path = match.group(1)
                value = self._get_variable(var_path, variables)
                return bool(value)

            return False
        except Exception:
            return False

    def _get_variable(self, path: str, variables: Dict[str, Any]) -> Any:
        """Get a variable value by path."""
        parts = path.split(".")
        value = variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _substitute_variables(
        self, obj: Any, variables: Dict[str, Any]
    ) -> Any:
        """Substitute ${var} patterns in object."""
        if isinstance(obj, str):
            result = obj
            pattern = r"\$\{([^}]+)\}"

            def replace_var(match):
                var_path = match.group(1)
                value = self._get_variable(var_path, variables)
                if value is None:
                    return match.group(0)
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                return str(value)

            result = re.sub(pattern, replace_var, result)
            return result
        elif isinstance(obj, dict):
            return {k: self._substitute_variables(v, variables) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_variables(item, variables) for item in obj]
        else:
            return obj
