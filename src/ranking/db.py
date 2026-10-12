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
    return con
