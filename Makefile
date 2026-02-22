# Axom MCP Server Makefile

MAKEFLAGS += --no-print-directory

# =============================================================================
# OS DETECTION - Must be at top before any shell commands
# =============================================================================
ifeq ($(OS),Windows_NT)
    IS_WINDOWS := 1
    NULL := nul
else
    IS_WINDOWS :=
    NULL := /dev/null
endif

# =============================================================================
# SHELL CONFIGURATION - Conditional based on OS
# =============================================================================
# Only override shell on Windows; use default (sh/bash) on Unix
ifeq ($(IS_WINDOWS),1)
    SHELL := cmd.exe
    .SHELLFLAGS := /c
endif

.PHONY: help install install-dry-run venv run clean clean-all install-help clean-help agents-help install-link
.PHONY: test test-help

# Detect virtual environment - cross-platform using Make conditionals
ifeq ($(OS),Windows_NT)
	# Windows
	VENV_PYTHON=venv\\Scripts\\python.exe
	ifeq ($(wildcard venv/Scripts/python.exe),venv/Scripts/python.exe)
		PYTHON=venv\\Scripts\\python.exe
	else
		PYTHON=python
	endif
else
	# Unix-like
	VENV_PYTHON=./venv/bin/python
	ifeq ($(wildcard ./venv/bin/python),./venv/bin/python)
		PYTHON=./venv/bin/python
	else
		PYTHON=python3
	endif
endif
# Determine Python interpreter - cross-platform detection
PYTHON := $(shell command -v python3 2>$(NULL) || command -v python 2>$(NULL) || echo python)
SYSTEM_PYTHON=$(PYTHON)
export PYTHONPATH := $(PYTHONPATH):.

# Colors and Styles
ifeq ($(OS),Windows_NT)
	# Windows colors (basic)
	GREEN  := $(shell echo [38;5;114m)
	RED    := $(shell echo [38;5;167m)
	YELLOW := $(shell echo [38;5;221m)
	BLUE   := $(shell echo [38;5;45m)
	MAGENTA:= $(shell echo [38;5;171m)
	CYAN   := $(shell echo [38;5;81m)
	WHITE  := $(shell echo [38;5;15m)
	GREY   := $(shell echo [38;5;244m)
	BOLD   := $(shell echo [1m)
	DIM    := $(shell echo [2m)
	RESET  := $(shell echo [0m)
else
	GREEN  := $(shell tput -T xterm setaf 2)
	RED    := $(shell tput -T xterm setaf 1)
	YELLOW := $(shell tput -T xterm setaf 3)
	BLUE   := $(shell tput -T xterm setaf 4)
	MAGENTA:= $(shell tput -T xterm setaf 5)
	CYAN   := $(shell tput -T xterm setaf 6)
	WHITE  := $(shell tput -T xterm setaf 7)
	GREY   := $(shell tput -T xterm setaf 8)
	BOLD   := $(shell tput -T xterm bold)
	DIM    := $(shell tput -T xterm dim)
	RESET  := $(shell tput -T xterm sgr0)
endif

# Icons
CHECK  := ✅
INFO   := ℹ️
WARN   := ⚠️
ERROR  := ❌
STEP   := 🚀
CLEAN  := 🧹
DB_ICON:= 🗄️
AGENT  := 🤖

# Logging Helpers - cross-platform
# Always use echo since Windows cmd.exe doesn't have printf reliably available
define LOG_STEP
	echo
endef
define LOG_SUCCESS
	echo   [OK]
endef
define LOG_INFO
	echo   [INFO]
endef
define LOG_WARN
	echo   [WARN]
endef
define LOG_ERROR
	echo   [ERROR]
endef
define LOG_HEADER
	echo
endef

DRY_RUN ?= 0
INSTALLER_ARGS :=
ifeq ($(DRY_RUN),1)
INSTALLER_ARGS += --dry-run
endif

.DEFAULT_GOAL := help

# =============================================================================
# MAIN HELP
# =============================================================================

help:
ifeq ($(OS),Windows_NT)
	@echo   Axom MCP Server - Persistent memory MCP server
	@echo   ---------------------------------------------
	@echo   Setup Commands
	@echo     make install   Full install
	@echo     make db        Check SQLite database status
	@echo     make agents    Auto-apply MCP configs
	@echo     make test      Run tests
	@echo     make run       Manually run MCP server
else
	@set -e; \
	if [ -z "$$NO_COLOR" ]; then \
		H_RESET='$(RESET)'; H_BOLD='$(BOLD)'; H_DIM='$(DIM)'; H_SECTION='$(BOLD)'; H_TARGET='$(CYAN)'; H_NOTE='$(BLUE)'; \
	else H_RESET=''; H_BOLD=''; H_DIM=''; H_SECTION=''; H_TARGET=''; H_NOTE=''; fi; \
	printf '%b\n' ""; \
	printf '%b\n' "  $${H_BOLD}Axom MCP Server$${H_RESET}$${H_DIM} - Persistent memory MCP server$${H_RESET}"; \
	printf '%b\n' "  $${H_DIM}---------------------------------------------$${H_RESET}"; \
	printf '%b\n' "  $${H_DIM}More info and options: make <command>[-help]$${H_RESET}"; \
	printf '%b\n' ""; \
	printf '%b\n' "$${H_SECTION}  Setup Commands$${H_RESET}"; \
	printf '%b\n' "    $${H_TARGET}make install$${H_RESET}   $${H_DIM}[-dry-run]$${H_RESET}  Full install"; \
	printf '%b\n' ""; \
	printf '%b\n' "    $${H_TARGET}make db$${H_RESET}                        Check SQLite database status"; \
	printf '%b\n' "    $${H_TARGET}make agents$${H_RESET}    $${H_DIM}[-dry-run]$${H_RESET}    Auto-apply MCP configs for detected agents"; \
	printf '%b\n' "    $${H_TARGET}make test$${H_RESET}      $${H_DIM}[-core|-int]$${H_RESET}  Run core/integration tests"; \
	printf '%b\n' ""; \
	printf '%b\n' "$${H_SECTION}  Cleanup$${H_RESET}"; \
	printf '%b\n' "    $${H_TARGET}make clean$${H_RESET}     $${H_DIM}[-all]$${H_RESET}    Remove venv + agent configs"; \
	printf '%b\n' ""; \
	printf '%b\n' "$${H_SECTION}  Debug$${H_RESET}"; \
	printf '%b\n' "    $${H_TARGET}make run$${H_RESET}       Manually run MCP server (stdio)"; \
	printf '%b\n' "";
endif

# =============================================================================
# INSTALL (complete start-to-finish) - simplified for Windows
# =============================================================================

install:
	@echo === Axom MCP - Complete Install ===
	@echo Step 1: Installing Python dependencies
	@$(PYTHON) -m pip install -r requirements.txt --quiet
	@$(PYTHON) -m pip install -e . --quiet
	@echo   Dependencies installed
	@echo Step 2: Installing MCP Configuration
	@$(PYTHON) scripts/install_agent_config.py $(INSTALLER_ARGS)
	@echo === INSTALL COMPLETE ===
	@echo Run 'make run' to start the server

install-dry-run:
	@$(MAKE) install DRY_RUN=1

venv: python-deps

python-deps:
	@$(LOG_INFO) "Installing Python dependencies..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && pip install -r requirements.txt -q && pip install -e . -q; \
	elif python3 -m venv --help >/dev/null 2>&1; then \
		python3 -m venv venv; \
		. venv/bin/activate && pip install -r requirements.txt -q && pip install -e . -q; \
	else \
		pip3 install -r requirements.txt -q && pip install -e . -q; \
	fi
	@$(LOG_SUCCESS) "Python dependencies installed"

system-deps:
	@$(LOG_INFO) "Installing system dependencies..."
	@if [ "$(AUTO_SYSTEM_DEPS)" != "1" ]; then \
		$(LOG_ERROR) "Require: AUTO_SYSTEM_DEPS=1 make install"; exit 1; \
	fi
	@command -v apt-get >/dev/null 2>&1 && sudo apt-get update && sudo apt-get install -y build-essential python3-venv python3-pip; \
	command -v dnf >/dev/null 2>&1 && sudo dnf install -y gcc python3-pip python3-devel; \
	command -v pacman >/dev/null 2>&1 && sudo pacman -S --needed base-devel python python-pip; \
	command -v brew >/dev/null 2>&1 && brew install python3; \
	@$(LOG_SUCCESS) "System dependencies installed"

db-config:
	@./configure-env.sh

# =============================================================================
# DB GROUP (make db-help)
# =============================================================================
# Database - SQLite (no Docker required)
# =============================================================================

db: db-check

db-help:
	@printf "\n"
	@printf "  $(BOLD)Database Commands (SQLite)$(RESET)\n"
	@printf "    make db-check     Verify database connectivity\n"
	@printf "\n"

db-check:
	@$(LOG_INFO) "SQLite database file will be created on first use"
	@$(LOG_INFO) "Default location: ~/.axom/axom.db"

# =============================================================================
# TEST GROUP (make test-help)
# =============================================================================

test:
	@$(PYTHON) -m pytest tests/test_axom_mcp/ -v

test-help:
ifeq ($(OS),Windows_NT)
	@echo   Test Commands
	@echo     make test        Run all tests
	@echo     make test-core   Run core unit tests only
	@echo     make test-int    Run integration tests
else
	@printf "\n"
	@printf "  $(BOLD)Test Commands$(RESET)\n"
	@printf "    make test        Run all tests (core + integration)\n"
	@printf "    make test-core   Run core unit tests only\n"
	@printf "    make test-int    Run integration tests\n"
	@printf "\n"
endif

test-core:
	@$(PYTHON) -m pytest tests/test_axom_mcp/ -v \
		--ignore=tests/test_axom_mcp/test_integration.py

test-int:
	@$(PYTHON) -m pytest tests/test_axom_mcp/test_integration.py -v

# =============================================================================
# AGENTS GROUP (make agents-help)
# =============================================================================

agents:
	@$(PYTHON) scripts/install_agent_config.py

agents-scan:
	@$(PYTHON) scripts/install_agent_config.py --scan

agents-dry-run:
	@$(PYTHON) scripts/install_agent_config.py --dry-run

agents-clean:
	@if [ -n "$(CUSTOM)" ]; then \
		echo "  [INFO] Cleaning custom server: $(CUSTOM)"; \
		$(PYTHON) scripts/install_agent_config.py --custom $(CUSTOM); \
	else \
		echo "  [INFO] Cleaning Axom configurations"; \
		$(PYTHON) scripts/install_agent_config.py --clean; \
	fi

agents-help:
ifeq ($(OS),Windows_NT)
	@echo   Agents Commands
	@echo     make agents             Auto-apply MCP configs
	@echo     make agents-scan        Scan for unregistered agents
	@echo     make agents-dry-run     Preview without changes
	@echo     make agents-clean       Remove Axom configurations
else
	@printf "\n"
	@printf "  $(BOLD)Agents Commands$(RESET)\n"
	@printf "    make agents             Auto-apply MCP configs for detected agents\n"
	@printf "    make agents-scan        Scan for unregistered agents as well\n"
	@printf "    make agents-dry-run     Preview without making changes\n"
	@printf "    make agents-clean       Remove Axom configurations\n"
	@printf "\n"
	@printf "  $(BOLD)Dev Commands$(RESET)\n"
	@printf "    make agents-clean <custom>   Remove custom MCP configs, skills, and rules\n"
	@printf "\n"
endif

# =============================================================================
# RUN & CLEAN
# =============================================================================

run:
	@$(PYTHON) -m axom_mcp

clean:
	@$(LOG_INFO) "Cleaning temporary files..."
	@if [ "$(CLEAN_ALL)" = "1" ]; then \
		$(MAKE) clean-all CLEAN_ALL=1; \
	else \
		rm -rf __pycache__ *.egg-info .pytest_cache venv/ 2>/dev/null || true; \
		find . -name "*.pyc" -delete 2>/dev/null || true; \
		find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true; \
		$(LOG_SUCCESS) "Cleanup complete"; \
	fi

# Clean everything including database and MCP configs
# Use CLEAN_ALL=1 to skip confirmation (for CI/testing)
clean-all:
ifeq ($(IS_WINDOWS),1)
	@echo === Axom - Full System Reset ===
	@echo [1/4] Removing SQLite database and data...
	@if exist "%USERPROFILE%\.axom" (rmdir /s /q "%USERPROFILE%\.axom" 2>nul && echo   [OK] Database cleanup complete) else (echo   [SKIP] No database found)
	@echo [2/4] Cleaning Axom configurations from agents...
	@$(PYTHON) scripts/install_agent_config.py --clean
	@echo [3/4] Wiping local data and environments...
	@if exist venv (rmdir /s /q venv 2>nul && echo   [OK] venv removed)
	@if exist __pycache__ (rmdir /s /q __pycache__ 2>nul && echo   [OK] __pycache__ removed)
	@if exist .pytest_cache (rmdir /s /q .pytest_cache 2>nul && echo   [OK] .pytest_cache removed)
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
	@for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f" 2>nul
	@for %%i in (*.egg-info) do @if exist "%%i" rmdir /s /q "%%i" 2>nul
	@echo   [OK] Local data wiped
	@echo [4/4] Deleting environment file...
	@if exist .env (del /q .env && echo   [OK] .env removed) else (echo   [SKIP] No .env file found)
	@echo === SYSTEM RESET COMPLETE ===
	@echo Run 'make install' to start fresh.
else
	@echo "=== Axom - Full System Reset ==="
	@echo "[1/4] Removing SQLite database and data..."
	@if [ -d ~/.axom ]; then \
		rm -rf ~/.axom 2>/dev/null || true; \
		echo "  [OK] Database cleanup complete"; \
	else \
		echo "  [SKIP] No database found"; \
	fi
	@echo "[2/4] Cleaning Axom configurations from agents..."
	@$(PYTHON) scripts/install_agent_config.py --clean
	@echo "[3/4] Wiping local data and environments..."
	@rm -rf venv __pycache__ .pytest_cache .ruff_cache 2>/dev/null || true; \
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
	find . -name "*.pyc" -delete 2>/dev/null || true; \
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true; \
	echo "  [OK] Local data wiped"
	@echo "[4/4] Deleting environment file..."
	@if [ -f .env ]; then \
		rm -f .env 2>/dev/null || true; \
		echo "  [OK] .env removed"; \
	else \
		echo "  [SKIP] No .env file found"; \
	fi
	@echo "=== SYSTEM RESET COMPLETE ==="
	@echo "Run 'make install' to start fresh."
endif

# Backward-compat aliases
check-db: db-check
install-agents: agents
install-link:
	@$(PYTHON) scripts/install_agent_config.py --link-only

# =============================================================================
# HELP TARGETS
# =============================================================================

install-help:
ifeq ($(OS),Windows_NT)
	@echo   Install Options
	@echo     DRY_RUN=1           Preview install without changes
	@echo     AUTO_SYSTEM_DEPS=1  Auto-install system dependencies
else
	@printf "\n"
	@printf "  $(BOLD)Install Options$(RESET)\n"
	@printf "    DRY_RUN=1           Preview install without changes\n"
	@printf "    AUTO_SYSTEM_DEPS=1 Auto-install system dependencies\n"
	@printf "\n"
endif

clean-help:
ifeq ($(OS),Windows_NT)
	@echo   Clean Options
	@echo     CLEAN_ALL=1         Full reset (DB + MCP + .env)
else
	@printf "\n"
	@printf "  $(BOLD)Clean Options$(RESET)\n"
	@printf "    CLEAN_ALL=1         Full reset (DB + MCP + .env)\n"
	@printf "\n"
endif
