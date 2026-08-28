SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parcels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    tracking TEXT NOT NULL,
    carrier TEXT NOT NULL,
    source TEXT NOT NULL,
    parameters TEXT NOT NULL DEFAULT '{}',
    parser_state TEXT NOT NULL DEFAULT 'standard',
    file_id INTEGER NOT NULL,
    processed_file_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT,
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(processed_file_id) REFERENCES files(id)
);
"""
