# school_ranking

Build a US college ranking from Parchment's "cross-admit" (revealed preference) data:
for two schools, among students admitted to both, what share enrolled at each.

## Pipeline
1. `data/schools_seed.csv` – school list (name, category). **Seed only**: 165 national universities from
   the 2027 US News ranking (via frishberg/Archive-of-US-News-College-Rankings, top ~165 only) + ~110 liberal
   arts colleges typed by hand. usnews.com is not reachable from the sandbox, so replace this with the full
   US News export (all ranked National Universities + National Liberal Arts Colleges).
2. `python3 resolve_schools.py data/schools_seed.csv data/schools_resolved.csv` – maps names to Parchment's
   institution names (uses `data/name_overrides.csv` for hard cases). Review `fuzzy` rows.
3. `python3 scrape_pairs.py data/schools_resolved.csv data/matchups.db --workers 6` – all unordered pairs into
   SQLite, resumable. ~2.6 req/s with 4 workers; N schools => N(N-1)/2 requests.

Set `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt` when running inside the sandbox.

## Gotchas
- Unknown names make Parchment silently show UCLA vs Berkeley; `parse_matchup` rejects name mismatches.
- Pairs without enough overlap return an empty page -> stored with `has_data=0`.
- Duplicate institution names exist (two "Wheaton College"), so those are excluded.
- Only a rounded percent and a 95% Wilson CI are published (no sample size); n can be backed out of the CI.
