#!/usr/bin/env python3
"""
Axom Agent Configuration Installer
Uses agent-registry.json for configuration discovery and installation.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# Markers for single-file configs
START_MARKER = "<!-- AXOM_AGENT_CONFIG_START -->"
END_MARKER = "<!-- AXOM_AGENT_CONFIG_END -->"

# Source files mapping: Name -> Relative Path
RULES = {
    "axom-core": "docs/agents/rules/axom-rule.md",
}

SKILLS = {
    "axom-memory": "docs/agents/skills/axom-memory/SKILL.md",
    "axom-exec": "docs/agents/skills/axom-exec/SKILL.md",
    "axom-discover": "docs/agents/skills/axom-discover/SKILL.md",
    "axom-analyze": "docs/agents/skills/axom-analyze/SKILL.md",
    "axom-transform": "docs/agents/skills/axom-transform/SKILL.md",
}

SKILL_DESCRIPTIONS = {
    "axom-memory": (
        "Memory tool that challenges itself, other agents, and users to re-think, "
        "seek optimal solutions, and improve creativity and focus."
    ),
    "axom-exec": (
        "Atomic chains and tool abstraction for efficient file operations and shell "
        "workflows with minimal wasted steps."
    ),
    "axom-discover": (
        "Map files, tools, memories, and capabilities before acting to reduce blind "
        "execution and improve precision."
    ),
    "axom-analyze": (
        "Deep analysis workflow for debugging, review, audit, refactor, and test "
        "coverage with actionable output."
    ),
    "axom-transform": (
        "Format conversion, templating, and rule-based data transformation for "
        "pipeline and chain-reaction workflows."
    ),
}

PALETTE = {
    "header": "\033[38;5;214m",
    "info": "\033[38;5;221m",
    "success": "\033[38;5;114m",
    "warn": "\033[38;5;179m",
    "error": "\033[38;5;167m",
    "dry": "\033[38;5;221m",
    "skip": "\033[38;5;244m",
}
RESET = "\033[0m"


def _supports_color() -> bool:
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


def _colorize(text: str, tone: str) -> str:
    if not _supports_color():
        return text
    color = PALETTE.get(tone)
    if not color:
        return text
    return f"{color}{text}{RESET}"


def _print(message: str, tone: str = "info") -> None:
    print(_colorize(message, tone))


def _print_header(message: str) -> None:
    _print(message, "header")


def _print_info(message: str) -> None:
    _print(message, "info")


def _print_success(message: str) -> None:
    _print(message, "success")


def _print_warning(message: str) -> None:
    _print(f"[Warning] {message}", "warn")


def _print_error(message: str) -> None:
    _print(f"[Error] {message}", "error")


def _print_dry_run(message: str) -> None:
    _print(f"[DRY RUN] {message}", "dry")


def get_project_root():
    return Path(__file__).parent.parent


def get_registry():
    """Load the agent registry."""
    root = get_project_root()
    registry_path = root / "agent-registry.json"
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def expand_path(path_str: str) -> Path:
    """Expand ~ and environment variables in path."""
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    # On Windows, os.path.expanduser("~") might return C:\Users\User
    # but some paths might use forward slashes or different separators.
    # We normalize to ensure consistency.
    return Path(expanded).resolve()


def _has_yaml_frontmatter(content: str) -> bool:
    """Check whether content starts with a YAML frontmatter block."""
    stripped = content.lstrip()
    if not stripped.startswith("---"):
        return False
    return re.match(r"^---\s*\n.*?\n---\s*(\n|$)", stripped, re.DOTALL) is not None


def _ensure_skill_frontmatter(content: str, skill_name: str) -> str:
    """Add required SKILL.md frontmatter when it is missing."""
    if _has_yaml_frontmatter(content):
        return content

    description = SKILL_DESCRIPTIONS.get(skill_name, f"Axom skill: {skill_name}.")
    frontmatter = (
        f"---\n"
        f"name: {skill_name}\n"
        f"description: {json.dumps(description, ensure_ascii=True)}\n"
        f"---\n\n"
    )
    return frontmatter + content.lstrip("\n")


def get_ide_installed_extensions(ide_name: str) -> set[str]:
    """
    Get the set of installed extension IDs for a given IDE by reading its extension cache.

    This prevents detecting stale/leftover extension directories from uninstalled extensions.

    Returns a set of extension IDs (e.g., {'kilocode.kilo-code', 'saoudrizwan.claude-dev'})
    """
    home = Path.home()
    installed_extensions: set[str] = set()

    # Platform-specific paths for IDE extension caches
    if os.name == "nt":  # Windows
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            base_path = Path(appdata)

            if ide_name.lower() == "cursor":
                # Cursor extension cache locations on Windows
                cache_paths = [
                    base_path
                    / "Cursor"
                    / "CachedProfilesData"
                    / "__default__profile__"
                    / "extensions.user.cache",
                    base_path
                    / "Cursor"
                    / "CachedProfilesData"
                    / "default"
                    / "extensions.user.cache",
                ]
            elif ide_name.lower() == "trae":
                cache_paths = [
                    base_path
                    / "Trae"
                    / "CachedProfilesData"
                    / "__default__profile__"
                    / "extensions.user.cache",
                    base_path
                    / "Trae"
                    / "CachedProfilesData"
                    / "default"
                    / "extensions.user.cache",
                ]
            elif ide_name.lower() == "vscode" or ide_name.lower() == "code":
                cache_paths = [
                    base_path
                    / "Code"
                    / "CachedProfilesData"
                    / "__default__profile__"
                    / "extensions.user.cache",
                    base_path
                    / "Code"
                    / "CachedProfilesData"
                    / "default"
                    / "extensions.user.cache",
                ]
            else:
                cache_paths = []

            for cache_path in cache_paths:
                if cache_path.exists():
                    try:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)

                        # The cache has a 'result' array with extension info
                        if "result" in cache_data:
                            for ext in cache_data["result"]:
                                if "identifier" in ext and "id" in ext["identifier"]:
                                    installed_extensions.add(ext["identifier"]["id"])
                    except (json.JSONDecodeError, IOError, KeyError):
                        # If we can't parse the cache, continue to next path
                        continue
    else:
        # Unix-like systems (macOS, Linux)
        config_home = os.environ.get("XDG_CONFIG_HOME", "") or (home / ".config")
        config_path = Path(config_home)

        if ide_name.lower() == "cursor":
            cache_paths = [
                config_path / "Cursor" / "User" / "extensions.json",
                home / ".cursor" / "extensions.json",
            ]
        elif ide_name.lower() == "trae":
            cache_paths = [
                config_path / "Trae" / "User" / "extensions.json",
                home / ".trae" / "extensions.json",
            ]
        elif ide_name.lower() == "vscode" or ide_name.lower() == "code":
            cache_paths = [
                config_path / "Code" / "User" / "extensions.json",
                home / ".vscode" / "extensions.json",
            ]
        else:
            cache_paths = []

        for cache_path in cache_paths:
            if cache_path.exists():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        ext_data = json.load(f)

                    # VSCode-style extensions.json has an 'extensions' array
                    if "extensions" in ext_data:
                        for ext in ext_data["extensions"]:
                            if "id" in ext:
                                installed_extensions.add(ext["id"])
                except (json.JSONDecodeError, IOError, KeyError):
                    continue

    return installed_extensions


def get_database_url(root_path: Path) -> str | None:
    """Extract DATABASE_URL from environment or local .env file."""
    # PostgreSQL is deprecated. We only support SQLite now.
    return None


def detect_installed_agents(registry: dict, scan: bool = False) -> list[dict]:
    """Detect which agents are installed on the system."""
    home = Path.home()
    installed = []

    for agent_id, agent_data in registry.get("agents", {}).items():
        # Track which variants are active for this agent
        active_variants = []

        for variant_id, variant in agent_data.get("variants", {}).items():
            detection = variant.get("detection", {})
            is_installed = False

            # 1. Check executables (Primary and ONLY method for IDE/CLI agents)
            # Directory fallbacks create false positives, so only use shutil.which
            executables = detection.get("executables", [])
            for exe in executables:
                if shutil.which(exe):
                    is_installed = True
                    break

            # For IDE/CLI agents: ONLY use executable detection - no directory fallback
            # This prevents false positives from leftover directories
            is_extension_variant = variant_id in ["extension", "cursor_extension"]

            # 2. For extension variants: check IDE extension cache
            if not is_installed and variant_id == "cursor_extension":
                # Only cursor_extension variants use IDE extension cache for verification
                extension_id = variant.get("extension_id")
                if extension_id:
                    ide_map = {
                        "cursor": "Cursor",
                        "kilo": "Cursor",
                    }
                    ide_to_check = ide_map.get(agent_id, "Cursor")
                    installed_in_ide = get_ide_installed_extensions(ide_to_check)

                    if extension_id in installed_in_ide:
                        is_installed = True

            # 3. For general "extension" variants (non-cursor_extension): check IDE extension cache
            if not is_installed and variant_id == "extension":
                extension_id = variant.get("extension_id")
                if extension_id:
                    # Map agent IDs to their corresponding IDE names for extension cache lookup
                    ide_map = {
                        "cursor": "Cursor",
                        "cline": "Cursor",
                        "roo": "Cursor",
                        "trae": "Trae",
                        "vscode": "VSCode",
                    }
                    ide_to_check = ide_map.get(agent_id, "Cursor")
                    installed_in_ide = get_ide_installed_extensions(ide_to_check)

                    if extension_id in installed_in_ide:
                        is_installed = True

            # 4. Additional check: if extension is detected, also verify the config path exists
            # This is a secondary check for extension variants to ensure the extension has config
            if not is_installed and is_extension_variant:
                extension_id = variant.get("extension_id")
                if extension_id:
                    for path_pattern in detection.get("paths", []):
                        path = expand_path(path_pattern)
                        if path.exists() and path.is_dir():
                            try:
                                if any(path.iterdir()):
                                    is_installed = True
                                    break
                            except (PermissionError, OSError):
                                continue

            # 5. SPECIAL CASE: If rules or skills are already installed in the target path,
            # we should consider it "installed" for the purpose of CLEANING.
            # This handles cases where the IDE might have been uninstalled but configs remain.
            # However, we only do this if we are in CLEAN mode (handled by clean_configs).
            # For INSTALL mode, we still want to verify the agent is active.

            if is_installed:
                active_variants.append(
                    {
                        "agent_id": agent_id,
                        "variant_id": variant_id,
                        "name": agent_data.get("name", agent_id),
                        "variant": variant,
                    }
                )

        # If we found active variants, add them all (allowing multiple versions)
        if active_variants:
            installed.extend(active_variants)

    # Handle --scan flag
    if scan:
        scanned = scan_for_unregistered_agents(registry)
        for agent in scanned:
            if agent not in installed:
                installed.append(agent)

    return installed


def scan_for_unregistered_agents(registry: dict) -> list[dict]:
    """Scan system for MCP configs from unregistered agents."""
    home = Path.home()
    found = []

    scan_patterns = registry.get("scan_patterns", {})

    # Scan for MCP config files using glob
    for pattern in scan_patterns.get("mcp_configs", []):
        # Handle ** glob pattern
        if "**" in pattern:
            base_pattern = pattern.replace("**/", "").replace("**", "")
            base_path = expand_path(base_pattern)
            if base_path.exists() and base_path.is_dir():
                for match in base_path.rglob("*mcp*.json"):
                    if match.is_file():
                        agent_info = infer_agent_from_path(match)
                        if agent_info and agent_info not in found:
                            found.append(agent_info)
        else:
            expanded = expand_path(pattern)
            if expanded.is_file():
                agent_info = infer_agent_from_path(expanded)
                if agent_info and agent_info not in found:
                    found.append(agent_info)

    # Scan for rules in common locations
    for rule_name in RULES.keys():
        for ext in [".md", ".mdc"]:
            # Check local .cursor/rules
            local_rule = Path(".cursor") / "rules" / f"{rule_name}{ext}"
            if local_rule.exists():
                found.append(
                    {
                        "agent_id": "cursor-local",
                        "variant_id": "ide",
                        "name": "Cursor (Local Workspace)",
                        "variant": {
                            "configs": {
                                "rules": {
                                    "path": ".cursor/rules",
                                    "format": "flat",
                                    "ext": ext,
                                }
                            }
                        },
                    }
                )

            # Check for global rules in ~/.cursorrules (legacy)
            home_rule = Path.home() / ".cursorrules"
            if home_rule.exists():
                found.append(
                    {
                        "agent_id": "cursor-global-legacy",
                        "variant_id": "ide",
                        "name": "Cursor (Global Legacy)",
                        "variant": {
                            "configs": {
                                "rules": {
                                    "path": str(Path.home()),
                                    "format": "flat",
                                    "ext": ".cursorrules",
                                }
                            }
                        },
                    }
                )

    # Check for .cursor/rules in all parent directories (orphaned workspace rules)
    curr = Path(os.getcwd()).resolve()
    while True:
        # Skip current directory as it's handled by "cursor-local"
        if curr != Path(os.getcwd()).resolve():
            rules_dir = curr / ".cursor" / "rules"
            if rules_dir.exists() and rules_dir.is_dir():
                found_any_rule = False
                for rule_name in RULES.keys():
                    for ext in [".md", ".mdc"]:
                        if (rules_dir / f"{rule_name}{ext}").exists():
                            found_any_rule = True
                            break
                    if found_any_rule:
                        break

                if found_any_rule:
                    found.append(
                        {
                            "agent_id": f"cursor-orphaned-{curr.name}",
                            "variant_id": "ide",
                            "name": f"Cursor (Orphaned Workspace: {curr.name})",
                            "variant": {
                                "configs": {
                                    "rules": {
                                        "path": str(rules_dir),
                                        "format": "flat",
                                        "ext": ".mdc",
                                    }
                                }
                            },
                        }
                    )
        if curr == curr.parent:
            break
        curr = curr.parent

    # Scan for extensions
    for pattern in scan_patterns.get("extension_dirs", []):
        ext_dir = expand_path(pattern.replace("/*/package.json", ""))
        if ext_dir.exists():
            for ext in ext_dir.iterdir():
                if ext.is_dir() and (ext / "package.json").exists():
                    pkg = json.loads((ext / "package.json").read_text(encoding="utf-8"))
                    name = pkg.get("name", "")
                    publisher = pkg.get("publisher", "")

                    # Check if it's a known agent extension
                    indicators = scan_patterns.get("agent_indicators", {}).get(
                        "config_files", []
                    )
                    for indicator in indicators:
                        if indicator in str(ext):
                            found.append(
                                {
                                    "agent_id": f"unknown-{ext.name}",
                                    "variant_id": "extension",
                                    "name": f"Unknown ({pkg.get('displayName', ext.name)})",
                                    "variant": {
                                        "detection": {"paths": [str(ext)]},
                                        "configs": {
                                            "mcp": {
                                                "path": str(
                                                    ext
                                                    / "settings"
                                                    / "mcp_settings.json"
                                                ),
                                                "format": "json",
                                                "key": "mcpServers",
                                            }
                                        },
                                    },
                                }
                            )
                            break

    return found


def infer_agent_from_path(path: Path) -> dict | None:
    """Try to infer agent info from an MCP config path."""
    path_str = str(path)

    # Look for known patterns
    agents = {
        "cursor": ["cursor", ".cursor"],
        "codex": ["codex", ".codex"],
        "claude": ["claude", ".claude"],
        "cline": ["cline", ".cline"],
        "zed": ["zed", ".config/zed"],
        "qwen": ["qwen", ".qwen"],
        "gemini": ["gemini", ".gemini"],
        "kiro": ["kiro", ".kiro"],
        "kilo": ["kilo", ".kilocode"],
        "opencode": ["opencode", ".config/opencode"],
        "junie": ["junie", ".config/junie"],
        "vibe": ["vibe", ".config/vibe"],
        "trae": ["trae", ".trae"],
        "windsurf": ["windsurf", ".codeium/windsurf"],
        "roo": ["roo", ".roo"],
        "continue": ["continue", ".continue"],
        "augment": ["augment", ".augment"],
    }

    for agent_id, patterns in agents.items():
        for pattern in patterns:
            if pattern in path_str.lower():
                return {
                    "agent_id": agent_id,
                    "variant_id": "discovered",
                    "name": agent_id.title(),
                    "variant": {
                        "detection": {"paths": [str(path.parent)]},
                        "configs": {
                            "mcp": {
                                "path": str(path),
                                "format": "json",
                                "key": "mcpServers",
                            }
                        },
                    },
                }

    return None


def _strip_json_comments(content: str) -> str:
    """Strip comments from JSONC content."""

    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    return content


class JSONParseError(Exception):
    pass


def _load_json_path(path: Path) -> dict[str, Any]:
    """Load JSON/JSONC file."""
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return json.loads(_strip_json_comments(raw))
        except json.JSONDecodeError as e:
            raise JSONParseError(f"Cannot parse {path}: {e}") from e


def _write_json_path(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _inject_jsonc_value(content: str, key: str, value: Any, indent: int = 2) -> str:
    """Inject a JSON value into JSONC content while preserving comments."""

    value_str = json.dumps(value, indent=indent)
    key_pattern = rf'"{re.escape(key)}"\s*:'

    if re.search(key_pattern, content):
        match = re.search(key_pattern + r"(\s*)", content)
        if match:
            start = match.end()
            depth = 0
            in_string = False
            escape_next = False
            end = start

            for i, char in enumerate(content[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if char == "\\" and in_string:
                    escape_next = True
                    continue
                if char == '"' and not in_string:
                    in_string = True
                    continue
                if char == '"' and in_string:
                    in_string = False
                    continue
                if not in_string:
                    if char in "{[":
                        depth += 1
                    elif char in "}]":
                        depth -= 1
                        if depth < 0:
                            end = i
                            break
                    elif char in ",}]" and depth == 0:
                        end = i
                        break

            return content[:start] + value_str + content[end:]

    content = content.rstrip()
    if content.endswith("}"):
        indent_str = " " * indent
        formatted_value = json.dumps(value, indent=indent)
        formatted_lines = formatted_value.split("\n")
        if len(formatted_lines) > 1:
            indented_lines = [indent_str + line for line in formatted_lines]
            indented_value = "\n".join(indented_lines)
        else:
            indented_value = formatted_value

        before_closing = content[:-1].rstrip()
        needs_comma = before_closing and not before_closing.endswith(("{", "[", ","))

        if needs_comma:
            insertion = f',\n{indent_str}"{key}": {indented_value}'
        else:
            insertion = f'\n{indent_str}"{key}": {indented_value}'

        return before_closing + insertion + "\n}"

    return content


def _write_toml_mcp_server(
    path: Path, server_name: str, command: str, args: list, env: dict
) -> bool:
    """Write MCP config to TOML file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    original = path.read_text(encoding="utf-8") if path.exists() else ""

    # Remove existing server config

    pattern = rf"^\[mcp_servers\.{re.escape(server_name)}\].*?(?=^\[|\Z)"
    original = re.sub(pattern, "", original, flags=re.MULTILINE | re.DOTALL)
    pattern = rf"^\[mcp_servers\.{re.escape(server_name)}\.env\].*?(?=^\[|\Z)"
    original = re.sub(pattern, "", original, flags=re.MULTILINE | re.DOTALL)

    block_lines = [
        f"[mcp_servers.{server_name}]",
        f"command = {json.dumps(command)}",
        f"args = {json.dumps(args)}",
    ]
    if env:
        block_lines.append("")
        block_lines.append(f"[mcp_servers.{server_name}.env]")
        for k in sorted(env.keys()):
            block_lines.append(f"{k} = {json.dumps(env[k])}")

    updated = original.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"
    path.write_text(updated, encoding="utf-8")
    return True


def ensure_axom_in_path(root_path: Path) -> bool:
    """Create a symlink in ~/.local/bin to make 'axom' available in PATH.

    This is needed because pip install -e . installs the console script
    to venv/bin/axom which is not in the system PATH by default.
    """
    import platform

    # Check if we're on Windows (symlinks may require admin privileges)
    is_windows = platform.system() == "Windows"

    # Find the source script (prefer 'axom' if it exists, otherwise 'axom-mcp')
    axom_mcp = root_path / "venv" / "bin" / "axom-mcp"
    axom_script = root_path / "venv" / "bin" / "axom"

    # Determine source (prefer 'axom' if it exists, otherwise 'axom-mcp')
    if axom_script.exists():
        source = axom_script
    elif axom_mcp.exists():
        source = axom_mcp
    else:
        # No source to link - might not be in a venv yet
        return False

    # Create symlink in ~/.local/bin
    local_bin = Path.home() / ".local" / "bin"

    # Check if already in PATH (skip if so)
    if shutil.which("axom"):
        return True

    # Try to create the directory if it doesn't exist
    try:
        local_bin.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _print_warning(f"Could not create ~/.local/bin: {e}")
        return False

    link_path = local_bin / "axom"

    # Remove existing symlink/file if it exists
    try:
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
    except OSError:
        pass

    # Create symlink
    try:
        if is_windows:
            # On Windows, symlinks may require admin privileges
            # Try to use absolute path for hard link or copy as fallback
            try:
                os.symlink(source, link_path)
            except OSError:
                # Fallback: copy the file on Windows
                import shutil as shutil_mod

                shutil_mod.copy2(source, link_path)
        else:
            # Use relative path for portability on Unix
            try:
                os.symlink(source.resolve(), link_path)
            except OSError:
                # Fallback: try absolute path
                os.symlink(source, link_path)
        _print_success(f"Created symlink: {link_path} -> {source}")
        return True
    except OSError as e:
        _print_warning(f"Could not create symlink in ~/.local/bin: {e}")
        # Try to add a hint about PATH
        _print_info(
            f"Tip: Add {local_bin} to your PATH or run: export PATH=$PATH:{local_bin}"
        )
        return False


def get_mcp_config(root_path: Path) -> tuple[str, str, list[str], dict[str, str]]:
    """Get MCP command and args for the server."""
    server_name = "axom"

    # Check for symlink
    axom_mcp = root_path / "venv" / "bin" / "axom-mcp"

    # Ensure axom is in PATH by creating a symlink in ~/.local/bin
    # This is needed because pip install -e . installs to venv/bin which may not be in PATH
    ensure_axom_in_path(root_path)

    # Priority order:
    # 1. axom-mcp command in PATH (installed package entry point)
    # 2. axom command in PATH (legacy/global install)
    # 3. venv/bin/axom-mcp from local project install
    # 4. python -m axom_mcp.server (last resort)
    if shutil.which("axom-mcp"):
        command = "axom-mcp"
        args = []
    elif shutil.which("axom"):
        command = "axom"
        args = []
    elif axom_mcp.exists():
        command = str(axom_mcp)
        args = []
    else:
        command = "python"  # Uses PATH, not hardcoded sys.executable
        args = ["-m", "axom_mcp.server"]

    env = {}
    # SQLite is the only supported database.
    # AXOM_DB_PATH is handled by the server internally.
    # No need to pass DATABASE_URL anymore.

    return server_name, command, args, env


def install_mcp_config(
    config_spec: dict,
    server_name: str,
    command: str,
    args: list,
    env: dict,
    dry_run: bool = False,
) -> bool:
    """Install MCP configuration for a specific config spec."""
    path = expand_path(config_spec.get("path", ""))
    format_type = config_spec.get("format", "json")
    key = config_spec.get("key", "mcpServers")
    inject = config_spec.get("inject", False)

    if dry_run:
        _print_dry_run(f"Would install MCP to: {path}")
        return True

    if format_type == "json":
        if inject:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                modified = _inject_jsonc_value(
                    content,
                    key,
                    {
                        server_name: {
                            "command": command,
                            "args": args,
                            **({"env": env} if env else {}),
                        }
                    },
                )
                path.write_text(modified, encoding="utf-8")
            else:
                data = {
                    key: {
                        server_name: {
                            "command": command,
                            "args": args,
                            **({"env": env} if env else {}),
                        }
                    }
                }
                _write_json_path(path, data)
            _print(f"  [OK] Injected MCP config: {path}", "success")

        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = _load_json_path(path)
            servers = data.get(key, {})
            servers[server_name] = {
                "command": command,
                "args": args,
                **({"env": env} if env else {}),
            }
            data[key] = servers
            _write_json_path(path, data)
            _print(f"  [OK] Updated MCP config: {path}", "success")

    elif format_type == "toml":
        _write_toml_mcp_server(path, server_name, command, args, env)
        _print(f"  [OK] Updated MCP config: {path}", "success")

    elif format_type == "jsonc":
        content = path.read_text(encoding="utf-8") if path.exists() else "{}"
        modified = _inject_jsonc_value(
            content,
            key,
            {
                server_name: {
                    "command": command,
                    "args": args,
                    **({"env": env} if env else {}),
                }
            },
        )
        path.write_text(modified, encoding="utf-8")
        _print(f"  [OK] Injected MCP config: {path}", "success")

    return True


def install_rules_config(
    config_spec: dict, root_path: Path, agent_name: str, dry_run: bool = False
) -> bool:
    """Install Rules configuration."""
    path = expand_path(config_spec.get("path", ""))
    format_type = config_spec.get("format", "flat")
    ext = config_spec.get("ext", ".md")

    if dry_run:
        _print_dry_run(f"Would install Rules to: {path}")
        return True

    if format_type == "flat":
        path.mkdir(parents=True, exist_ok=True)
        for rule_name, rel_path in RULES.items():
            source = root_path / rel_path
            if source.exists():
                # For flat format, use the extension from config_spec (e.g., .mdc for Cursor)
                dest = path / f"{rule_name}{ext}"
                content = source.read_text(encoding="utf-8")

                # If it's an .mdc file, we need to ensure it has the proper frontmatter
                if ext == ".mdc":
                    # Check if it already has frontmatter
                    if not content.lstrip().startswith("---"):
                        # Add default frontmatter for .mdc files
                        frontmatter = "---\ndescription: Axom Agent Rule for knowledge retention and context recall\nglobs: \n---\n"
                        content = frontmatter + content

                dest.write_text(content, encoding="utf-8")
                _print(f"  [OK] Updated Rules: {dest}", "success")

    elif format_type == "dir":
        # Dir format: files go directly in the rules directory (not in subdirectories)
        # This is used by Kilo Code which expects rules/*.md files
        path.mkdir(parents=True, exist_ok=True)
        for rule_name, rel_path in RULES.items():
            source = root_path / rel_path
            if source.exists():
                # For dir format, put file directly in rules folder with .md extension
                dest = path / f"{rule_name}.md"
                dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                _print(f"  [OK] Updated Rules: {dest}", "success")

    elif format_type == "marker":
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""

        for rule_name, rel_path in RULES.items():
            source = root_path / rel_path
            if source.exists():
                content = source.read_text(encoding="utf-8")
                if START_MARKER not in existing:
                    new_content = f"{existing.rstrip()}\n\n{START_MARKER}\n{content}\n{END_MARKER}\n"
                    path.write_text(new_content, encoding="utf-8")
                else:
                    start_idx = existing.find(START_MARKER)
                    end_idx = existing.rfind(END_MARKER) + len(END_MARKER)
                    pre = existing[:start_idx].rstrip()
                    post = existing[end_idx:].lstrip()
                    updated = (
                        f"{pre}\n\n{START_MARKER}\n{content}\n{END_MARKER}\n{post}"
                    )
                    path.write_text(updated.strip() + "\n", encoding="utf-8")
                _print(f"  [OK] Updated Rules: {path}", "success")
                break

    return True


def install_skills_config(
    config_spec: dict, root_path: Path, agent_name: str, dry_run: bool = False
) -> bool:
    """Install Skills configuration."""
    path = expand_path(config_spec.get("path", ""))
    requires_frontmatter = bool(config_spec.get("requires_frontmatter", False))

    if dry_run:
        _print_dry_run(f"Would install Skills to: {path}")
        return True

    path.mkdir(parents=True, exist_ok=True)

    total_skills = len(SKILLS)
    installed_count = 0
    last_dest = ""

    for skill_name, rel_path in SKILLS.items():
        source = root_path / rel_path
        if source.exists():
            skill_dir = path / skill_name
            skill_dir.mkdir(exist_ok=True)
            dest = skill_dir / "SKILL.md"
            content = source.read_text(encoding="utf-8")
            if requires_frontmatter:
                content = _ensure_skill_frontmatter(content, skill_name)
            dest.write_text(content, encoding="utf-8")
            installed_count += 1
            last_dest = str(dest)

    if installed_count > 0:
        # Use the requested format: [X/X] Updated Skills: path/to/skills/axom-<...>/SKILL.md
        # We'll show the base path or the last installed skill path with a placeholder for the variable part
        display_path = str(path / "axom-<...>" / "SKILL.md")
        _print(
            f"  [{installed_count}/{total_skills}] Updated Skills: {display_path}",
            "success",
        )

    return True


def install_agent_configs(
    agent: dict,
    server_name: str,
    command: str,
    args: list,
    env: dict,
    root_path: Path,
    dry_run: bool = False,
) -> None:
    """Install all configs for an agent variant."""
    variant = agent.get("variant", {})
    configs = variant.get("configs", {})

    agent_name = agent.get("name", agent.get("agent_id", ""))

    # MCP
    if "mcp" in configs:
        install_mcp_config(configs["mcp"], server_name, command, args, env, dry_run)

    # Rules
    if "rules" in configs:
        install_rules_config(configs["rules"], root_path, agent_name, dry_run)

    # Skills
    if "skills" in configs:
        install_skills_config(configs["skills"], root_path, agent_name, dry_run)


def clean_configs(
    registry: dict, custom_server: str | None = None, dry_run: bool = False
) -> None:
    """Remove Axom configs, rules, and skills from all agents."""
    server_name = custom_server or "axom"
    server_name_lower = server_name.lower()

    if dry_run:
        _print(
            f"\n[DRY RUN] Would clean {server_name} configurations, rules, and skills",
            "dry",
        )
        return

    # Get all config paths from registry
    any_cleaned = False

    # We iterate through ALL agents in the registry for cleaning,
    # regardless of whether the executable is currently detected.
    for agent_id, agent_data in registry.get("agents", {}).items():
        agent_name = agent_data.get("name", agent_id)
        for variant_id, variant in agent_data.get("variants", {}).items():
            configs = variant.get("configs", {})
            agent_header_printed = False

            def _print_agent_header():
                nonlocal agent_header_printed
                if not agent_header_printed:
                    _print_header(f"\n--- {agent_name} [{variant_id.upper()}] ---")
                    agent_header_printed = True

            # 1. Clean MCP Config
            if "mcp" in configs:
                path = expand_path(configs["mcp"].get("path", ""))
                key = configs["mcp"].get("key", "mcpServers")
                if path.exists():
                    try:
                        format_type = "json"
                        path_str = str(path)
                        if path_str.endswith(".toml"):
                            format_type = "toml"
                        elif path_str.endswith(".jsonc") or "zed" in path_str:
                            format_type = "jsonc"

                        if format_type == "json":
                            data = _load_json_path(path)
                            servers = data.get(key, {})
                            if isinstance(servers, dict):
                                # Remove all matching keys case-insensitively.
                                to_remove = [
                                    name
                                    for name in servers.keys()
                                    if isinstance(name, str)
                                    and name.lower() == server_name_lower
                                ]
                            else:
                                to_remove = []
                            if to_remove:
                                for name in to_remove:
                                    del servers[name]
                                data[key] = servers
                                path.write_text(
                                    json.dumps(data, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8",
                                )
                                _print_agent_header()
                                _print(f"  [OK] Removed MCP config: {path}", "success")
                                any_cleaned = True
                        elif format_type == "jsonc":
                            content = path.read_text(encoding="utf-8")
                            pattern = rf'"{re.escape(server_name)}"\s*:\s*\{{[^}}]*\}}'
                            if re.search(pattern, content, flags=re.IGNORECASE):
                                content = re.sub(
                                    pattern, "", content, flags=re.IGNORECASE
                                )
                                content = re.sub(r",\s*,", ",", content)
                                content = re.sub(r"\{\s*,", "{", content)
                                content = re.sub(r",\s*\}", "}", content)
                                path.write_text(content, encoding="utf-8")
                                _print_agent_header()
                                _print(f"  [OK] Removed MCP config: {path}", "success")
                                any_cleaned = True
                        elif format_type == "toml":
                            content = path.read_text(encoding="utf-8")
                            pattern = rf"^\[{re.escape(key)}\.{re.escape(server_name)}\].*?(?=^\[|\Z)"
                            if re.search(
                                pattern,
                                content,
                                flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
                            ):
                                new_content = re.sub(
                                    pattern,
                                    "",
                                    content,
                                    flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
                                ).strip()
                                pattern_env = rf"^\[{re.escape(key)}\.{re.escape(server_name)}\.env\].*?(?=^\[|\Z)"
                                new_content = re.sub(
                                    pattern_env,
                                    "",
                                    new_content,
                                    flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
                                ).strip()
                                path.write_text(new_content + "\n", encoding="utf-8")
                                _print_agent_header()
                                _print(f"  [OK] Removed MCP config: {path}", "success")
                                any_cleaned = True
                    except Exception as e:
                        _print_error(
                            f"  [ERROR] Failed to clean MCP for {agent_name}: {e}"
                        )

            # 2. Clean Rules
            if "rules" in configs:
                path = expand_path(configs["rules"].get("path", ""))
                format_type = configs["rules"].get("format", "flat")
                ext = configs["rules"].get("ext", ".md")
                if path.exists():
                    try:
                        if format_type in ["flat", "dir"]:
                            removed_any = False
                            for rule_name in RULES.keys():
                                # Check for both .md and .mdc extensions
                                for e in [".md", ".mdc"]:
                                    rule_file = path / f"{rule_name}{e}"
                                    if rule_file.exists():
                                        rule_file.unlink()
                                        removed_any = True
                            if removed_any:
                                _print_agent_header()
                                _print(f"  [OK] Removed Rules: {path}", "success")
                                any_cleaned = True
                            # Clean up directory if empty
                            if path.is_dir() and not any(path.iterdir()):
                                path.rmdir()
                        elif format_type == "marker":
                            content = path.read_text(encoding="utf-8")
                            if START_MARKER in content:
                                start_idx = content.find(START_MARKER)
                                end_idx = content.rfind(END_MARKER) + len(END_MARKER)
                                pre = content[:start_idx].rstrip()
                                post = content[end_idx:].lstrip()
                                updated = f"{pre}\n{post}".strip() + "\n"
                                path.write_text(updated, encoding="utf-8")
                                _print_agent_header()
                                _print(
                                    f"  [OK] Removed Rules marker: {path}", "success"
                                )
                                any_cleaned = True
                    except Exception as e:
                        _print_error(
                            f"  [ERROR] Failed to clean Rules for {agent_name}: {e}"
                        )

            # 3. Clean Skills
            if "skills" in configs:
                path = expand_path(configs["skills"].get("path", ""))
                if path.exists():
                    try:
                        removed_count = 0
                        total_skills = len(SKILLS)
                        for skill_name in SKILLS.keys():
                            skill_dir = path / skill_name
                            if skill_dir.exists() and skill_dir.is_dir():
                                shutil.rmtree(skill_dir)
                                removed_count += 1
                        if removed_count > 0:
                            _print_agent_header()
                            _print(
                                f"  [{removed_count}/{total_skills}] Removed Skills: {path}",
                                "success",
                            )
                            any_cleaned = True
                        # Clean up directory if empty
                        if path.is_dir() and not any(path.iterdir()):
                            path.rmdir()
                    except Exception as e:
                        _print_error(
                            f"  [ERROR] Failed to clean Skills for {agent_name}: {e}"
                        )

    # 4. Clean Cursor Internal History (Orphaned Rules/Skills)
    if not dry_run:
        appdata = os.environ.get("APPDATA")
        if appdata:
            history_path = Path(appdata) / "Cursor" / "User" / "History"
            if history_path.exists():
                cleaned_history = False
                for entries_file in history_path.rglob("entries.json"):
                    try:
                        content = entries_file.read_text(
                            encoding="utf-8", errors="ignore"
                        )
                        # Check if this history entry refers to any of our rules or skills
                        found_match = False
                        for rule_name in RULES.keys():
                            if (
                                f"{rule_name}.mdc" in content
                                or f"{rule_name}.md" in content
                            ):
                                found_match = True
                                break
                        if not found_match:
                            for skill_name in SKILLS.keys():
                                if (
                                    f"{skill_name}.md" in content
                                    or f"{skill_name}/SKILL.md" in content
                                ):
                                    found_match = True
                                    break

                        if found_match:
                            # Found a reference. Delete the entire history directory for this resource.
                            shutil.rmtree(entries_file.parent)
                            cleaned_history = True
                    except:
                        continue
                if cleaned_history:
                    _print(
                        "  [OK] Cleaned Cursor internal rule/skill history", "success"
                    )
                    any_cleaned = True

    if not any_cleaned:
        _print(
            f"  {_colorize('[SKIP]', 'skip')} No agent configurations found to clean"
        )


def install_env_file(root_path: Path, dry_run: bool = False) -> None:
    """Ensure .env exists by copying .env.example if missing."""
    env_file = root_path / ".env"
    env_example = root_path / ".env.example"

    if env_file.exists():
        return

    if not env_example.exists():
        _print_warning(".env.example not found, skipping .env creation")
        return

    if dry_run:
        _print_dry_run("Would create .env from .env.example")
        return

    try:
        shutil.copy2(env_example, env_file)
        _print_success("Created .env from .env.example")
    except Exception as e:
        _print_error(f"Failed to create .env: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Install Axom config to agent platforms"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be installed"
    )
    parser.add_argument(
        "--scan", action="store_true", help="Scan for unregistered agents"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install to all known agents (even if not detected)",
    )
    parser.add_argument("--agent", help="Install only to specific agent")
    parser.add_argument(
        "--clean", action="store_true", help="Remove Axom configs from all agents"
    )
    parser.add_argument(
        "--custom", help="Remove specific server configs (e.g., --custom=mcp-name)"
    )
    args = parser.parse_args()

    root_path = get_project_root()
    registry = get_registry()

    # Handle clean mode
    if args.clean or args.custom:
        clean_configs(registry, args.custom, dry_run=args.dry_run)
        return

    _print_header("\nAxom Agent Installer")
    _print_info(f"Project Root: {root_path}")

    if args.dry_run:
        _print("[DRY RUN] No changes will be made\n")

    # Ensure .env exists
    install_env_file(root_path, dry_run=args.dry_run)

    server_name, command, args_list, env = get_mcp_config(root_path)

    _print_info(f"Server: {server_name}")
    _print_info(f"Command: {command}")
    _print_info(f"Args: {args_list}")
    if env:
        _print_info(f"Env: {env}")

    # Detect agents
    if args.all:
        # Install to all agents in registry
        agents = []
        for agent_id, agent_data in registry.get("agents", {}).items():
            if args.agent and agent_id != args.agent:
                continue
            for variant_id, variant in agent_data.get("variants", {}).items():
                agents.append(
                    {
                        "agent_id": agent_id,
                        "variant_id": variant_id,
                        "name": agent_data.get("name", agent_id),
                        "variant": variant,
                    }
                )
    else:
        agents = detect_installed_agents(registry, scan=args.scan)

    if not agents:
        _print_warning("No agents detected. Use --all to install to all agents.")
        return

    # Install to each agent
    for agent in agents:
        agent_name = agent.get("name", "")
        variant_id = agent.get("variant_id", "").upper()

        _print_header(f"\n--- {agent_name} [{variant_id}] ---")

        try:
            install_agent_configs(
                agent,
                server_name,
                command,
                args_list,
                env,
                root_path,
                dry_run=args.dry_run,
            )
        except Exception as e:
            _print_error(f"Failed to install to {agent_name}: {e}")

    _print_success("\nDone.")


if __name__ == "__main__":
    main()
