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

-- cohort size (number of graduates) for a source's period, when the source states it
CREATE TABLE IF NOT EXISTS cohort_sizes (
  source_id    INTEGER NOT NULL REFERENCES sources(source_id),
  period_start INTEGER,
  period_end   INTEGER,
  graduates    REAL,
  PRIMARY KEY (source_id, period_start, period_end)
);

-- UC Information Center "Admissions by source school" (freshmen). Blank cells in the source (fewer than 3-5 students,
-- or suppressed to avoid back-calculation) are stored as NULL / simply absent.
CREATE TABLE IF NOT EXISTS uc_schools (
  ceeb         TEXT PRIMARY KEY,     -- 6-digit CEEB/ACT code used by UC as the school key
  name         TEXT NOT NULL,
  city         TEXT,
  region       TEXT,                 -- county (CA), state (other US) or country
  school_type  TEXT,                 -- California public / private high school, Non-CA domestic, Foreign institution
  school_id    INTEGER REFERENCES schools(school_id),   -- link to our schools table when matched
  match_method TEXT
);
CREATE TABLE IF NOT EXISTS uc_ethnicity (
  ceeb TEXT NOT NULL REFERENCES uc_schools(ceeb), fall_term INTEGER NOT NULL, campus TEXT NOT NULL,
  measure TEXT NOT NULL,               -- App | Adm | Enr
  ethnicity TEXT NOT NULL,             -- All, African American, American Indian, Hispanic/Latinx, Pacific Islander, Asian, White, Domestic Unknown, Int'l
  count INTEGER,
  PRIMARY KEY (ceeb, fall_term, campus, measure, ethnicity)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS uc_gender (
  ceeb TEXT NOT NULL REFERENCES uc_schools(ceeb), fall_term INTEGER NOT NULL, campus TEXT NOT NULL,
  measure TEXT NOT NULL, gender TEXT NOT NULL, count INTEGER,
  PRIMARY KEY (ceeb, fall_term, campus, measure, gender)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS uc_gpa (
  ceeb TEXT NOT NULL REFERENCES uc_schools(ceeb), fall_term INTEGER NOT NULL, campus TEXT NOT NULL,
  measure TEXT NOT NULL,               -- App | Adm | Enrl  (mean unweighted? GPA as published by UC)
  gpa REAL,
  PRIMARY KEY (ceeb, fall_term, campus, measure)
) WITHOUT ROWID;
