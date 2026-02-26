#!/usr/bin/env python3
"""Stop any running axom-mcp processes so DB and files can be released.

Run at the start of make clean-all so the MCP server releases the database
before we try to remove it.
"""

import os
import subprocess
import sys
import time

import typer


def main() -> int:
    killed = 0
    try:
        if os.name == "nt":
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'axom-mcp' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            pids = [
                x.strip()
                for x in (result.stdout or "").strip().splitlines()
                if x.strip()
            ]
            killed = len(pids)
        else:
            result = subprocess.run(
                ["pkill", "-f", "axom-mcp"],
                capture_output=True,
                timeout=5,
            )
            killed = 1 if result.returncode == 0 else 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if killed:
        typer.secho(
            f"  [OK] Stopped {killed} axom-mcp process(es)", fg=typer.colors.GREEN
        )
        time.sleep(2)  # Let handles release before clean-all continues
    return 0


if __name__ == "__main__":
    sys.exit(main())
