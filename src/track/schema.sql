PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL UNIQUE,
    managed_path TEXT NOT NULL,
    is_latest INTEGER NOT NULL DEFAULT 0 CHECK (is_latest IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_text TEXT NOT NULL,
    resume_id INTEGER NOT NULL REFERENCES resumes(id),
    applied_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_role_text_nocase
    ON applications(role_text COLLATE NOCASE);
