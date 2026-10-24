# school_ranking

Bay Area public high school college matriculation data → SQLite with unified school/college IDs.

**Website (GitHub Pages):** https://xtxsinan-lgtm.github.io/school_ranking/ — static site in `docs/` with three parts
(湾区高中研究 / 美国大学排名研究 / 中国大学高考分数排名研究). After changing any result CSV, refresh the site data with
`python3 tools/build_site_data.py` (stdlib only; writes `docs/data/*.json`). Preview locally: `python3 -m http.server -d docs`.

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

## UC admissions by source school
`tools/uc_fetch.py` downloads the UC Information Center "Admissions by source school" crosstabs (Tableau server, CSV export; sheets
FREthbyYr = by race/ethnicity, FRGndbyYr = by gender, FRGPAbyYr = mean GPA) for every school type x fall term x UC campus into
`data/raw_uc/` (git-ignored, re-runnable). `python -m ranking load-uc` loads them into `uc_schools`, `uc_ethnicity`, `uc_gender`, `uc_gpa`
(keyed by 6-digit CEEB code; `uc_schools.school_id` links to our `schools` table when matched). Measures: App = applicants, Adm = admits,
Enr = enrolled freshmen. Cells with too few students are blank in the source and not stored.

### Where the data lives
The SQLite file `data/school_ranking.db` is git-ignored (rebuild: `build-reference`, `ingest`, `import-user-sheet`, `load-uc`).
Committed full exports are in `data/export/*.csv.gz` (schools, colleges, matriculation_full, uc_schools, uc_ethnicity, uc_gender, uc_gpa).

## College cross-admit ranking (Parchment)


Build a US college ranking from Parchment's "cross-admit" (revealed preference) data:
for two schools, among students admitted to both, what share enrolled at each.

### Pipeline
1. `data/schools_seed.csv` – school list (name, category). **Seed only**: 165 national universities from
   the 2027 US News ranking (via frishberg/Archive-of-US-News-College-Rankings, top ~165 only) + ~110 liberal
   arts colleges typed by hand. usnews.com is not reachable from the sandbox, so replace this with the full
   US News export (all ranked National Universities + National Liberal Arts Colleges).
2. `python3 resolve_schools.py data/schools_seed.csv data/schools_resolved.csv` – maps names to Parchment's
   institution names (uses `data/name_overrides.csv` for hard cases). Review `fuzzy` rows.
3. `python3 scrape_pairs.py data/schools_resolved.csv data/matchups.db --workers 6` – all unordered pairs into
   SQLite, resumable. ~2.6 req/s with 4 workers; N schools => N(N-1)/2 requests.

Set `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt` when running inside the sandbox.

### Gotchas
- Unknown names make Parchment silently show UCLA vs Berkeley; `parse_matchup` rejects name mismatches.
- Pairs without enough overlap return an empty page -> stored with `has_data=0`.
- Duplicate institution names exist (two "Wheaton College"), so those are excluded.
- Only a rounded percent and a 95% Wilson CI are published (no sample size); n can be backed out of the CI.

## China university Gaokao score ranking (2006–2012)

Transcribed and verified from the 10 tables in https://www.zhihu.com/question/28340072/answer/85457689:
- `data/cn_2011_top30.csv` – Top 30 summary table (`img_01`)
- `data/cn_2007_top20_freq.csv` – 2007 Science cutoff Top-20 appearance matrix across 30 provinces × 26 schools (`img_02`)
- `data/cn_2006_2007_3prov.csv` – 2006–2007 3-province (山东/江苏/广东) Science average score Top 50 (`img_03`)
- `data/cn_2006_2007_4prov.csv` – 2006–2007 4-province (江苏/河北/湖北/广东, with 广东06 converted via $\sqrt{x}\times 22.5$) Top 50 (`img_04`)
- `data/cn_2010_sichuan_raw_sample.csv` – 2010 Sichuan raw Sina Education scrape sample (`img_05`)
- `data/cn_2011_raw_cutoff_23prov.csv` – 2010/2011 raw Science batch-1 cutoff scores across 23 provinces for 50 schools (`img_06`)
- `data/cn_2011_std_top100.csv` – 2011 equal-variance standardized & enrollment-weighted Top 100 (+2 medical faculties) across 23 provinces in 6 tiers (`img_07`)
- `data/cn_2011_city_bias.csv` – 23 provinces × 29 university cities regional attractiveness bias matrix (`img_08`)
- `data/cn_2012_sci_top50.csv` – 2012 5-province (河南/广东/山东/四川/安徽) Science average score Top 50 (`img_09`)
- `data/cn_2012_arts_top50.csv` – 2012 5-province (河南/广东/山东/四川/安徽) Liberal Arts average score Top 50 (`img_10`)
