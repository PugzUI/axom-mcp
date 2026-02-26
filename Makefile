# Axom MCP Server Makefile

MAKEFLAGS += --no-print-directory

# =============================================================================
# OS DETECTION - Must be at top before any shell commands
# =============================================================================
ifeq ($(OS),Windows_NT)
    IS_WINDOWS := 1
else
    IS_WINDOWS :=
endif

# =============================================================================
# SHELL CONFIGURATION - Conditional based on OS
# =============================================================================
# Only override shell on Windows; use default (sh/bash) on Unix
ifeq ($(IS_WINDOWS),1)
    SHELL := cmd.exe
    .SHELLFLAGS := /c
endif

# =============================================================================
# PYTHON CONFIGURATION - Cross-platform virtual environment detection
# =============================================================================
PYTHON := $(shell \
    if [ -f ./venv/bin/python ]; then \
        echo "./venv/bin/python"; \
    elif [ -f "./venv/Scripts/python.exe" ]; then \
        echo "./venv/Scripts/python.exe"; \
    else \
        echo "python3"; \
    fi)

# =============================================================================
# COLORS AND STYLES - Only if NO_COLOR not set
# =============================================================================
ifeq ($(NO_COLOR)z,z)  # z suffix ensures empty NO_COLOR matches
    # Check if terminal supports colors (tput available)
    COLOR_TEST := $(shell command -v tput >/dev/null 2>&1 && echo yes || echo no)
    ifeq ($(IS_WINDOWS),1)
        GREEN  := $(shell echo [@] )
        RED    := $(shell echo [X])
        YELLOW := $(shell echo [!])
        BLUE   := $(shell echo [i])
        RESET  := 
        BOLD   := 
    else
        ifeq ($(COLOR_TEST),yes)
            GREEN  := $(shell tput -T xterm setaf 2)
            RED    := $(shell tput -T xterm setaf 1)
            YELLOW := $(shell tput -T xterm setaf 3)
            BLUE   := $(shell tput -T xterm setaf 4)
            CYAN   := $(shell tput -T xterm setaf 6)
            GREY   := $(shell tput -T xterm setaf 8)
            BOLD   := $(shell tput -T xterm bold)
            DIM    := $(shell tput -T xterm dim)
            RESET  := $(shell tput -T xterm sgr0)
        else
            GREEN  := [@]
            RED    := [X]
            YELLOW := [!]
            BLUE   := [i]
            CYAN   := [>]
            GREY   := [~]
            BOLD   := 
            DIM    := 
            RESET  := 
        endif
    endif
else
    GREEN  := [@]
    RED    := [X]
    YELLOW := [!]
    BLUE   := [i]
    CYAN   := [>]
    GREY   := [~]
    BOLD   := 
    DIM    := 
    RESET  := 
endif

# =============================================================================
# LOGGING HELPERS
# =============================================================================
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

# =============================================================================
# MAIN HELP
# =============================================================================

.PHONY: help h make-h make-help install install-dry-run venv run clean clean-all
.PHONY: install-help install-h clean-help clean-h agents-help agents-h db-help db-h
.PHONY: test test-help test-h lint format lint-help lint-h format-help format-h install-link
.PHONY: db db-check db-help db-config seed-generate seed-db
.PHONY: python-deps system-deps agents agents-scan agents-dry-run agents-clean
.PHONY: lint format lint-help format-help
.PHONY: check-db install-agents install-link

# Default target
.DEFAULT_GOAL := help

# Optional: dry-run for installer
DRY_RUN ?= 0
INSTALLER_ARGS :=
ifeq ($(DRY_RUN),1)
INSTALLER_ARGS += --dry-run
endif

help:
	@printf "\n"
	@printf "  $(BOLD)Axom MCP Server$(RESET) - Persistent memory MCP server\n"
	@printf "  --------------------------------------------------\n"
	@printf "  make make-h / make make-help / make h / make help  (make -h shows Make built-in)\n"
	@printf "\n"
	@printf "  $(BOLD)Setup$(RESET)\n"
	@printf "    $(CYAN)make install$${RESET}       Full install (venv + deps + MCP config)\n"
	@printf "    $(CYAN)make install-h$${RESET} / $(CYAN)make install-help$${RESET}  Install options (DRY_RUN, etc.)\n"
	@printf "    $(CYAN)make db$${RESET}            Check SQLite database status\n"
	@printf "    $(CYAN)make db-h$${RESET} / $(CYAN)make db-help$${RESET}  Database commands\n"
	@printf "    $(CYAN)make seed-db$${RESET}      Generate and load dev_seed\n"
	@printf "\n"
	@printf "  $(BOLD)Agents$(RESET)\n"
	@printf "    $(CYAN)make agents$${RESET}        Auto-apply MCP, rules, skills, subagents\n"
	@printf "    $(CYAN)make agents-h$${RESET} / $(CYAN)make agents-help$${RESET}  Agents commands\n"
	@printf "\n"
	@printf "  $(BOLD)Dev$(RESET)\n"
	@printf "    $(CYAN)make test$${RESET}          Run tests (see also: test-core, test-int, test-cov)\n"
	@printf "    $(CYAN)make lint$${RESET}          Run ruff linter\n"
	@printf "    $(CYAN)make format$${RESET}        Format and fix with ruff\n"
	@printf "    $(CYAN)make run$${RESET}            Manually run MCP server\n"
	@printf "\n"
	@printf "  $(BOLD)Cleanup$(RESET)\n"
	@printf "    $(CYAN)make clean$${RESET}         Remove venv, caches\n"
	@printf "    $(CYAN)make clean-all$${RESET}    Full reset (DB + configs + venv)\n"
	@printf "    $(CYAN)make clean-h$${RESET} / $(CYAN)make clean-help$${RESET}  Clean options\n"
	@printf "\n"

h: help
make-h: help
make-help: help
install-h: install-help
clean-h: clean-help
agents-h: agents-help
db-h: db-help
test-h: test-help
lint-h: lint-help
format-h: format-help

# =============================================================================
# INSTALL (complete start-to-finish) - uses project venv, no global install
# =============================================================================

install:
ifeq ($(IS_WINDOWS),1)
	@echo === Axom MCP - Complete Install ===
	@echo Step 1: Creating venv if needed...
	@if not exist venv\Scripts\python.exe (python -m venv venv && echo   [OK] venv created) else (echo   [OK] venv exists)
	@echo Step 2: Installing Python dependencies into venv...
	@venv\Scripts\python.exe -m pip install -r requirements.txt -q
	@venv\Scripts\python.exe -m pip install -e . -q
	@echo   Dependencies installed
	@echo Step 3: Installing MCP Configuration
	@venv\Scripts\python.exe scripts/install_agent_config.py $(INSTALLER_ARGS)
	@echo === INSTALL COMPLETE ===
	@echo Run 'make run' to start the server
else
	@echo "=== Axom MCP - Complete Install ==="
	@echo "Step 1: Creating venv if needed..."
	@if [ ! -f venv/bin/python ]; then python3 -m venv venv && echo "  [OK] venv created"; else echo "  [OK] venv exists"; fi
	@echo "Step 2: Installing Python dependencies into venv..."
	@./venv/bin/pip install -r requirements.txt -q
	@./venv/bin/pip install -e . -q
	@echo "  Dependencies installed"
	@echo "Step 3: Installing MCP Configuration"
	@./venv/bin/python scripts/install_agent_config.py $(INSTALLER_ARGS)
	@echo "=== INSTALL COMPLETE ==="
	@echo "Run 'make run' to start the server"
endif

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
	@$(LOG_INFO) "Verifying SQLite database connectivity and schema"
	@$(PYTHON) scripts/verify_db.py

# =============================================================================
# LINT & FORMAT (ruff) - make lint-help, make format-help
# =============================================================================

lint:
	@$(PYTHON) -m ruff check src tests scripts

format:
	@$(PYTHON) -m ruff format src tests scripts
	@$(PYTHON) -m ruff check src tests scripts --fix

lint-help:
	@printf "\n"
	@printf "  $(BOLD)Lint Commands (ruff)$(RESET)\n"
	@printf "    make lint    Run ruff linter (check only)\n"
	@printf "    make format Format code and auto-fix lint issues\n"
	@printf "\n"

format-help: lint-help

# =============================================================================
# TEST GROUP (make test-help)
# =============================================================================

test:
	@$(PYTHON) -m pytest tests/test_axom_mcp/ -v

test-help:
	@printf "\n"
	@printf "  $(BOLD)Test Commands$(RESET)\n"
	@printf "    make test        Run all tests (core + integration)\n"
	@printf "    make test-core   Run core unit tests only\n"
	@printf "    make test-int    Run integration tests\n"
	@printf "    make test-cov    Run tests with coverage gate\n"
	@printf "\n"

test-core:
	@$(PYTHON) -m pytest tests/test_axom_mcp/ -v \
		--ignore=tests/test_axom_mcp/test_integration.py

test-int:
	@$(PYTHON) -m pytest tests/test_axom_mcp/test_integration.py -v

test-cov:
	@$(PYTHON) -m pytest tests/test_axom_mcp/ -v \
		--cov=src/axom_mcp \
		--cov-report=term-missing \
		--cov-fail-under=100

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
	@printf "\n"
	@printf "  $(BOLD)Agents Commands$(RESET)\n"
	@printf "    make agents             Auto-apply MCP, rules, skills, subagents\n"
	@printf "    make agents-scan        Scan for unregistered agents as well\n"
	@printf "    make agents-dry-run     Preview without making changes\n"
	@printf "    make agents-clean      Remove Axom configurations\n"
	@printf "\n"
	@printf "  $(BOLD)Dev Commands$(RESET)\n"
	@printf "    make agents-clean <custom>   Remove custom MCP configs, skills, and rules\n"
	@printf "\n"

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
	@echo [1/6] Stopping axom-mcp (releases DB lock)...
	@python scripts/kill_axom_mcp.py
	@echo [2/6] Uninstalling global axom-mcp...
	@python -m pip uninstall -y axom-mcp 2>nul || echo   [SKIP] No global axom-mcp
	@echo [3/6] Removing SQLite database and data...
	@if exist "%USERPROFILE%\.axom" (rmdir /s /q "%USERPROFILE%\.axom" 2>nul && echo   [OK] Database cleanup complete) else (echo   [SKIP] No database found)
	@echo [4/6] Cleaning Axom configurations from agents...
	@python scripts/install_agent_config.py --clean
	@echo [5/6] Wiping local data and environments...
	@if exist venv (rmdir /s /q venv 2>nul && echo   [OK] venv removed)
	@if exist __pycache__ (rmdir /s /q __pycache__ 2>nul && echo   [OK] __pycache__ removed)
	@if exist .pytest_cache (rmdir /s /q .pytest_cache 2>nul && echo   [OK] .pytest_cache removed)
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
	@for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f" 2>nul
	@for %%i in (*.egg-info) do @if exist "%%i" rmdir /s /q "%%i" 2>nul
	@echo   [OK] Local data wiped
	@echo [6/6] Deleting environment file...
	@if exist .env (del /q .env && echo   [OK] .env removed) else (echo   [SKIP] No .env file found)
	@echo === SYSTEM RESET COMPLETE ===
	@echo Run 'make install' to start fresh.
else
	@echo "=== Axom - Full System Reset ==="
	@echo "[1/6] Stopping axom-mcp (releases DB lock)..."
	@python3 scripts/kill_axom_mcp.py
	@sleep 2 2>/dev/null || true
	@echo "[2/6] Uninstalling global axom-mcp..."
	@python3 -m pip uninstall -y axom-mcp 2>/dev/null || echo "  [SKIP] No global axom-mcp"
	@echo "[3/6] Removing SQLite database and data..."
	@if [ -d ~/.axom ]; then \
		rm -rf ~/.axom 2>/dev/null || true; \
		echo "  [OK] Database cleanup complete"; \
	else \
		echo "  [SKIP] No database found"; \
	fi
	@echo "[4/6] Cleaning Axom configurations from agents..."
	@$(PYTHON) scripts/install_agent_config.py --clean
	@echo "[5/6] Wiping local data and environments..."
	@rm -rf venv __pycache__ .pytest_cache .ruff_cache 2>/dev/null || true; \
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
	find . -name "*.pyc" -delete 2>/dev/null || true; \
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true; \
	echo "  [OK] Local data wiped"
	@echo "[6/6] Deleting environment file..."
	@if [ -f .env ]; then \
		rm -f .env 2>/dev/null || true; \
		echo "  [OK] .env removed"; \
	else \
		echo "  [SKIP] No .env file found"; \
	fi
	@echo "=== SYSTEM RESET COMPLETE ==="
	@echo "Run 'make install' to start fresh."
endif

# =============================================================================
# DEV SEED (db/dev_seed/ - gitignored)
# =============================================================================

seed-generate:
	@$(PYTHON) scripts/dev_seed_from_md.py

seed-db: seed-generate
	@$(PYTHON) scripts/load_dev_seed.py --clear

# Backward-compat aliases
check-db: db-check
install-agents: agents
install-link:
	@$(PYTHON) scripts/install_agent_config.py --link-only

# =============================================================================
# HELP TARGETS
# =============================================================================

install-help:
	@printf "\n"
	@printf "  $(BOLD)Install Options$(RESET)\n"
	@printf "    DRY_RUN=1           Preview install without changes\n"
	@printf "    AUTO_SYSTEM_DEPS=1 Auto-install system dependencies\n"
	@printf "\n"

clean-help:
	@printf "\n"
	@printf "  $(BOLD)Clean Options$(RESET)\n"
	@printf "    CLEAN_ALL=1         Full reset (DB + MCP + .env)\n"
	@printf "\n"
