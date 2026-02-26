-- Main memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    name TEXT,
    memory_type TEXT NOT NULL,
    importance TEXT NOT NULL DEFAULT 'high',
    content TEXT NOT NULL,
    summary TEXT,
    tags TEXT DEFAULT '[]',
    source_agent TEXT,
    source_context TEXT,
    source_tool TEXT,
    parent_memory_id TEXT,
    associated_memories TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    accessed_at TEXT,
    expires_at TEXT,
    access_count INTEGER DEFAULT 0
);

-- Full Text Search table using FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    id UNINDEXED,
    name,
    content,
    tags,
    tokenize='porter'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(id, name, content, tags) VALUES (new.id, new.name, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  DELETE FROM memories_fts WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
  DELETE FROM memories_fts WHERE id = old.id;
  INSERT INTO memories_fts(id, name, content, tags) VALUES (new.id, new.name, new.content, new.tags);
END;

-- Access Log table
CREATE TABLE IF NOT EXISTS memory_access_log (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    accessed_by TEXT,
    access_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- Trigger to update access stats on memory when accessed
CREATE TRIGGER IF NOT EXISTS log_access_update_memory AFTER INSERT ON memory_access_log BEGIN
    UPDATE memories
    SET access_count = access_count + 1,
        accessed_at = new.created_at
    WHERE id = new.memory_id;
END;
