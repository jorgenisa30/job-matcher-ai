-- Esquema de Job Matcher AI
-- Compatible con SQLite. Migrable a PostgreSQL/SQL Server casi sin cambios
-- (sustituir AUTOINCREMENT por SERIAL/IDENTITY según el motor).

CREATE TABLE IF NOT EXISTS cv_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    summary TEXT,
    skills TEXT,           -- JSON-encoded list
    experience TEXT,       -- JSON-encoded list
    education TEXT,        -- JSON-encoded list
    languages TEXT,        -- JSON-encoded list
    raw_text TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,
    salary_min REAL,
    salary_max REAL,
    url TEXT,
    source TEXT,            -- e.g. 'adzuna'
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cv_id INTEGER NOT NULL REFERENCES cv_profiles(id),
    job_id INTEGER NOT NULL REFERENCES job_postings(id),
    match_score REAL NOT NULL,
    cover_letter TEXT,
    status TEXT DEFAULT 'matched',   -- matched | reviewed | applied | discarded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cv_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_cv ON matches(cv_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(match_score DESC);
