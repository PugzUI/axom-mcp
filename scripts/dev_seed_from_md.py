"""Generate dev seed SQL from .md files under C:\\dev\\src\\user.

Collects all .md files (excluding .pytest_cache),
splits each into section/paragraph chunks, and outputs raw SQL INSERT
statements for fast database seeding.

Seeds all schema attributes (memory_type, importance, summary, source_*,
associated_memories, etc.) with varied values for integration testing.

Output: db/dev_seed/seed.sql, db/dev_seed/manifest.json
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import typer

ROOT = Path(r"C:\dev\src\user")
EXCLUDE_DIRS = (".pytest_cache",)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "db" / "dev_seed"
MAX_CONTENT_LEN = 50_000
MIN_CHUNK_LEN = 50
SLUG_MAX = 40
SUMMARY_MAX = 200

# Schema attribute values for salting (ensures integration tests hit all paths)
MEMORY_TYPES = ("long_term", "short_term", "reflex", "dreams")
IMPORTANCE_LEVELS = ("low", "high", "critical")

# Keywords to infer memory_type from section/content
DREAMS_KEYWORDS = ("dream", "idea", "creative", "explore", "experiment", "brainstorm")
REFLEX_KEYWORDS = ("reflex", "heuristic", "always", "check", "pattern", "rule")


def _slug(text: str) -> str:
    """Lowercase, replace non-alnum with _, truncate."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:SLUG_MAX] if len(s) > SLUG_MAX else s or "untitled"


def _escape_sql(s: str) -> str:
    """Escape single quotes and remove null bytes for SQL string literal."""
    s = str(s).replace("\x00", "").replace("\r", "").replace("'", "''")
    return s


def _should_skip(path: Path) -> bool:
    """Skip paths containing excluded dirs."""
    parts = path.parts
    return any(excl in parts for excl in EXCLUDE_DIRS)


def _collect_md_files(root: Path) -> list[Path]:
    """Collect .md files, excluding hidden dirs."""
    files: list[Path] = []
    for p in root.rglob("*.md"):
        if _should_skip(p):
            continue
        if p.is_file():
            files.append(p)
    return sorted(files)


def _parse_chunks(file_path: Path, text: str) -> list[tuple[str, str]]:
    """Split markdown into (section_header, content) chunks.

    Sections are ## or ### headers. Paragraphs are blocks between blank lines.
    Merge small chunks (< MIN_CHUNK_LEN) under same section to avoid micro-chunks.
    """
    chunks: list[tuple[str, str]] = []
    lines = text.splitlines()
    current_section = ""
    current_block: list[str] = []
    pending: list[str] = []

    def flush_block(force: bool = False):
        nonlocal current_block, pending
        if not current_block:
            return
        content = "\n".join(current_block).strip()
        if content:
            pending.append(content)
        current_block = []
        # Emit when we have enough content or at section boundary
        if (force or sum(len(p) for p in pending) >= MIN_CHUNK_LEN) and pending:
            merged = "\n\n".join(pending)
            chunks.append((current_section, merged))
            pending = []

    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            flush_block(force=True)
            current_section = line.lstrip("# ").strip()
            current_block = []
        elif line.strip() == "":
            flush_block(force=False)
            current_block = []
        else:
            current_block.append(line)

    flush_block(force=True)

    # Handle content before first section (e.g. title + intro)
    if not chunks and text.strip():
        chunks.append(("", text.strip()[:MAX_CONTENT_LEN]))

    return chunks


def _infer_memory_type(section: str, content: str, idx: int) -> str:
    """Infer memory_type from section/content for varied seeding."""
    combined = f"{section} {content}".lower()
    if any(kw in combined for kw in DREAMS_KEYWORDS):
        return "dreams"
    if any(kw in combined for kw in REFLEX_KEYWORDS):
        return "reflex"
    # Rotate: short_term for every 4th chunk, else long_term
    return "short_term" if idx % 4 == 3 else "long_term"


def _infer_importance(idx: int, memory_type: str) -> str:
    """Infer importance for varied seeding."""
    if memory_type == "reflex":
        return "critical"
    if memory_type == "dreams":
        return "low"
    # Rotate across low/high/critical for long_term/short_term
    return IMPORTANCE_LEVELS[idx % 3]


def _build_memory(
    file_path: Path,
    root: Path,
    section: str,
    content: str,
    idx: int,
    seen_names: set[str],
) -> tuple[dict, str]:
    """Build memory dict with all schema attributes (salted for integration tests)."""
    rel_path = str(file_path.relative_to(root)).replace("\\", "/")
    file_slug = _slug(file_path.stem)
    section_slug = _slug(section) if section else "intro"
    base_name = f"seed_{file_slug}_{section_slug}_{idx:03d}"
    name = base_name
    v = 1
    while name in seen_names:
        v += 1
        name = f"{base_name}_v{v}"
    seen_names.add(name)

    content_trunc = content[:MAX_CONTENT_LEN].replace("\x00", "")
    if len(content) > MAX_CONTENT_LEN:
        content_trunc += "\n...[truncated]"

    full_content = f"SOURCE: {rel_path}\n"
    if section:
        full_content += f"SECTION: {section}\n"
    full_content += f"CONTENT: {content_trunc}"

    tags = ["seed", "docs", file_slug]
    if section_slug and section_slug != "intro":
        tags.append(section_slug)
    tags = sorted(set(tags))

    memory_type = _infer_memory_type(section, content, idx)
    importance = _infer_importance(idx, memory_type)

    # Summary: first SUMMARY_MAX chars of content (schema supports it)
    raw_summary = content[:SUMMARY_MAX].strip()
    if not raw_summary:
        summary = None
    elif len(content) > SUMMARY_MAX:
        summary = (
            raw_summary.rsplit(maxsplit=1)[0] + "..."
            if " " in raw_summary
            else raw_summary + "..."
        )
    else:
        summary = raw_summary

    memory_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"axom.dev_seed.{name}"))
    metadata = {"source_file": rel_path, "section": section}

    return (
        {
            "id": memory_id,
            "name": name,
            "memory_type": memory_type,
            "importance": importance,
            "content": full_content,
            "summary": summary or None,
            "tags": json.dumps(tags),
            "source_agent": "dev_seed_generator",
            "source_context": "dev_seed",
            "source_tool": "dev_seed_from_md.py",
            "parent_memory_id": None,
            "associated_memories": "[]",
            "metadata": json.dumps(metadata),
            "expires_at": None,
            "access_count": 0,
        },
        name,
    )


def _sql_val(v: str | int | None) -> str:
    """Format value for SQL: NULL or quoted string."""
    if v is None:
        return "NULL"
    s = str(v)
    return f"'{_escape_sql(s)}'" if isinstance(v, str) else str(v)


def _to_sql_row(m: dict) -> str:
    """Format memory dict as SQL VALUES tuple (all schema columns)."""
    return (
        f"({_sql_val(m['id'])}, {_sql_val(m['name'])}, "
        f"'{m['memory_type']}', '{m['importance']}', "
        f"{_sql_val(m['content'])}, {_sql_val(m.get('summary'))}, "
        f"{_sql_val(m['tags'])}, {_sql_val(m['source_agent'])}, "
        f"{_sql_val(m['source_context'])}, {_sql_val(m['source_tool'])}, "
        f"{_sql_val(m.get('parent_memory_id'))}, {_sql_val(m['associated_memories'])}, "
        f"{_sql_val(m['metadata'])}, datetime('now'), datetime('now'), "
        f"datetime('now'), {_sql_val(m.get('expires_at'))}, {m.get('access_count', 0)})"
    )


def generate(
    root: Path | None = None, output_dir: Path | None = None
) -> tuple[list[dict], list[dict], Path, Path]:
    """Generate memories and manifest. Returns (memories, manifest, sql_path, manifest_path)."""
    root = root or ROOT
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_md_files(root)
    memories: list[dict] = []
    manifest: list[dict] = []
    seen_names: set[str] = set()

    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            text = text.replace("\x00", "")
        except Exception as e:
            typer.secho(f"[WARN] Skip {file_path}: {e}", fg=typer.colors.YELLOW)
            continue

        chunks = _parse_chunks(file_path, text)
        for idx, (section, content) in enumerate(chunks):
            if not content.strip():
                continue
            mem, name = _build_memory(
                file_path, root, section, content, idx, seen_names
            )
            memories.append(mem)
            manifest.append(
                {
                    "name": name,
                    "source_file": str(file_path.relative_to(root)).replace("\\", "/"),
                    "section": section,
                    "memory_type": mem["memory_type"],
                    "importance": mem["importance"],
                }
            )

    # Write seed.sql (all schema columns for integration test coverage)
    sql_path = output_dir / "seed.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- Dev seed: generated from C:\\dev\\src\\user\\*.md\n")
        f.write("-- Excludes: .pytest_cache\n")
        f.write(
            "-- Includes all schema attributes (memory_type, importance, summary, etc.)\n"
        )
        f.write("BEGIN TRANSACTION;\n")
        if memories:
            f.write(
                "INSERT INTO memories (id, name, memory_type, importance, content, "
                "summary, tags, source_agent, source_context, source_tool, "
                "parent_memory_id, associated_memories, metadata, created_at, "
                "updated_at, accessed_at, expires_at, access_count) VALUES\n"
            )
            rows = [_to_sql_row(m) for m in memories]
            f.write(",\n".join(rows))
            f.write("\n")
        f.write(";\nCOMMIT;\n")

    # Write manifest.json
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return memories, manifest, sql_path, manifest_path


def main() -> int:
    """CLI entry: generate seed.sql and manifest.json."""
    memories, manifest, sql_path, manifest_path = generate()
    typer.secho(f"[OK] Generated {len(memories)} memories", fg=typer.colors.GREEN)
    typer.secho(f"[OK] {sql_path}", fg=typer.colors.GREEN)
    typer.secho(f"[OK] {manifest_path}", fg=typer.colors.GREEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
