-- Unified IDs: schools.school_id and colleges.college_id are the project's own stable keys.
CREATE TABLE IF NOT EXISTS schools (
  school_id   INTEGER PRIMARY KEY,
  cds_code    TEXT UNIQUE,          -- California CDS code (14 digits)
  ncessch     TEXT,
  name        TEXT NOT NULL,
  district    TEXT,
  city        TEXT,
  county      TEXT,
  zip         TEXT,
  website     TEXT,
  charter     INTEGER,
  soc_type    TEXT,
  grades      TEXT
);
CREATE TABLE IF NOT EXISTS colleges (
  college_id  INTEGER PRIMARY KEY,
  unitid      INTEGER UNIQUE,       -- IPEDS id; NULL for non-US / not in IPEDS
  name        TEXT NOT NULL,
  city        TEXT,
  state       TEXT,
  country     TEXT DEFAULT 'US',
  sector      INTEGER,              -- IPEDS SECTOR (1-6 = public/private x 4yr/2yr/<2yr)
  iclevel     INTEGER,
  website     TEXT
);
CREATE TABLE IF NOT EXISTS college_aliases (
  alias_norm  TEXT NOT NULL,        -- normalized form (see normalize.py)
  college_id  INTEGER NOT NULL REFERENCES colleges(college_id),
  alias_raw   TEXT,
  origin      TEXT,                 -- ipeds | manual | auto
  PRIMARY KEY (alias_norm, college_id)
);
CREATE TABLE IF NOT EXISTS sources (
  source_id   INTEGER PRIMARY KEY,
  school_id   INTEGER NOT NULL REFERENCES schools(school_id),
  url         TEXT NOT NULL,
  source_type TEXT NOT NULL,        -- html | pdf
  parser      TEXT,
  fetched_at  TEXT,
  raw_path    TEXT,
  sha256      TEXT,
  notes       TEXT,
  UNIQUE (school_id, url)
);
CREATE TABLE IF NOT EXISTS matriculation (
  id            INTEGER PRIMARY KEY,
  school_id     INTEGER NOT NULL REFERENCES schools(school_id),
  source_id     INTEGER NOT NULL REFERENCES sources(source_id),
  grad_year     INTEGER,            -- single graduating class, or NULL when pooled
  period_start  INTEGER,            -- pooled range (e.g. 2024-2026); equals grad_year when single
  period_end    INTEGER,
  college_id    INTEGER REFERENCES colleges(college_id),  -- NULL = unresolved
  college_raw   TEXT NOT NULL,
  section       TEXT,               -- heading in source (e.g. "Community Colleges")
  count         INTEGER,
  match_method  TEXT,               -- exact | key | manual | fuzzy | none
  match_score   REAL,
  UNIQUE (source_id, period_start, period_end, college_raw, section)
);
CREATE INDEX IF NOT EXISTS idx_mat_school ON matriculation(school_id);
CREATE INDEX IF NOT EXISTS idx_mat_college ON matriculation(college_id);
CREATE VIEW IF NOT EXISTS unresolved AS
  SELECT college_raw, section, COUNT(*) n, SUM(count) total FROM matriculation
  WHERE college_id IS NULL GROUP BY college_raw, section ORDER BY total DESC;
