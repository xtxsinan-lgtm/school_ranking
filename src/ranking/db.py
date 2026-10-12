import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "school_ranking.db"
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"


def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript((Path(__file__).parent / "schema.sql").read_text())
    _migrate(con)
    return con


def _migrate(con):
    """Additive column migrations for databases created by earlier versions."""
    def cols(t):
        return {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
    if "sector" not in cols("schools"):
        con.execute("ALTER TABLE schools ADD COLUMN sector TEXT DEFAULT 'public'")
    if "origin" not in cols("sources"):
        con.execute("ALTER TABLE sources ADD COLUMN origin TEXT DEFAULT 'official'")  # official | user_sheet
    con.commit()
