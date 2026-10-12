# school_ranking

Bay Area public high school college matriculation data → SQLite with unified school/college IDs.

    pip install -r requirements.txt
    PYTHONPATH=src python3 -m ranking build-reference   # IPEDS colleges + CDE Bay Area public high schools
    PYTHONPATH=src python3 -m ranking ingest             # fetch (cached in data/raw) + parse + resolve all rows of data/sources.csv

- `schools.school_id` (CDS code), `colleges.college_id` (IPEDS UNITID; non-US colleges have `unitid` NULL).
- Add a school: one row in `data/sources.csv` (parser: `html_table` or `pdf_list`).
- Fix college naming: add a row to `data/aliases/college_aliases.csv`; see `data/export/unresolved.csv`.
- Pooled windows (e.g. Lynbrook 2022-2025) overlap and must not be summed; use `period_start/period_end`.

Ingested so far (per-college counts only): Henry M. Gunn, Palo Alto, Lynbrook, Los Gatos, Leigh, Menlo-Atherton, Dublin, Northgate.
Sources without per-college counts or that could not be fetched are listed in `data/LEADS_NOT_INGESTED.md`.
Discovery tooling: `tools/discover.py`, `tools/deep_crawl.py`, `tools/probe_candidates.py`.

Also imported: the user's spreadsheet (`data/user_data/bay_area_hs_sheet.xlsx`, sheet 原始升学) via
`python -m ranking import-user-sheet`; those rows have `sources.origin = 'user_sheet'` and cover a curated subset of ~95 colleges.
Private schools have `schools.sector = 'private'`.  Official sources: Marin Academy, Urban, Head-Royce, Menlo, Lick-Wilmerding, Branson.
