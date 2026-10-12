# Leads that are NOT in the database

Rule: only sources with **per-college counts** are ingested. Everything below was either unreachable from the
crawling environment, or reachable but has no per-college counts. (Generated 2026-10-12.)

## A. Found a profile/matriculation lead but could not access it (need manual download)

| School(s) | Link | Problem | What it should contain |
|---|---|---|---|
| Mission San Jose High (Fremont) | https://fremontunified.org/msjhs/about/welcome/ (page lists "Mission San Jose High School Profile 2025-2026") | HTTP 403 (site blocks this environment) | School profile; unknown whether it lists colleges with counts |
| Mission San Jose High | https://fremontunified.org/msjhs/students-community/student-support/counselors-overview/counselor-presentations/ | HTTP 403 | counselor presentations, possibly college outcomes |
| American High (Fremont) | https://fremontunified.org/wp-content/uploads/sites/4/2023/05/7344875500926176662.pdf (2023, appeared in search) ; https://fremontunified.org/american/ | HTTP 403 | profile (unverified) |
| Irvington High (Fremont) | https://fremontunified.org/irvington/ | HTTP 403 | no profile URL found; need to open the site manually |
| Washington High, John F. Kennedy High (Fremont) | https://fremontunified.org/washington/ ; https://fremontunified.org/kennedy/ | HTTP 403 | no profile URL found |
| Los Altos High, Mountain View High (MVLA) | https://lahs.mvla.net/school-profile ; https://mvhs.mvla.net/school-profile | page reachable but profile is an embedded/JS widget, no file link extractable | profile with "Post High School Plans" (the 2017 attendance PDFs only have rates, no college names) |
| Los Altos / Mountain View old profile PDFs | https://www.mvla.net/documents/Departments/Educational-Services/Plans-Reports/LAHS-School-Profile-2022-2023.pdf ; .../MVHS-School-Profile-2021-2022.pdf ; https://mvhs.mvla.net/documents/MVHS-School-Profile-2023-24-FINALrev3.6.24.pdf ; https://lahs.mvla.net/documents/About-Us/Site-Plans--Reports/College-Attendance-Data/Class%20of%202017%20College%20Attendance%20Data%20LAHS.pdf | HTTP 404 now (moved/removed) | profiles; Class-of-2017 attendance data (rates only) |
| Tamalpais High | https://www.tamdistrict.org/information/school-profile (404) ; https://www.tamhigh.org (TLS/connection error) | unreachable | school profile |
| Santa Rosa area (Santa Rosa, Maria Carrillo, Montgomery, Elsie Allen), Piner, Petaluma, Cloverdale | school sites on schoolloop / srcschools | 401/403/TLS errors | not investigated further |
| Lowell High (SF) and other SFUSD high schools | https://lowell.sfusd.edu/ | reachable, no matriculation/profile link found; SFUSD publishes SARC only | none known |

## B. Reachable, but only names / category percentages (no per-college counts) -> excluded by rule

Fremont High (Sunnyvale) 2022-25 and Monta Vista 26-27 (FUHSD profiles: names only); Cupertino and Homestead (FUHSD, no list found);
Aragon, Burlingame (SMUHSD profiles: names + rates); Carlmont (Class of 2023 / 2021 matriculation files: names only:
https://www.carlmonths.org/fs/resource-manager/view/912d95b6-cb01-40b3-8c70-5902821a66c4 and
https://www.carlmonths.org/fs/resource-manager/view/61b8f2f2-f8a4-4c53-97e2-4b105e7ed7b5);
Credo High (college-acceptances page, stars only); Jefferson/Terra Nova/Westmoor (Jefferson Union "College Acceptances" doc, names only);
Saratoga (percent by sector only); Dougherty Valley, Acalanes/Miramonte/Campolindo/Las Lomas, Berkeley High, Menlo-Atherton,
Piedmont, Alameda, Albany, Amador Valley, Livermore/Granada, Napa/Vintage, Redwood (profiles with rates only).

If you decide names-only sources are acceptable later, the first candidates are Carlmont, Fremont High, Monta Vista, Aragon, Burlingame.


## C. Status of the public schools in the user's sheet (湾区高中 / 升学) — updated

| School in sheet | Status | Source / reason |
|---|---|---|
| Gunn, Palo Alto, Lynbrook, Los Gatos | ingested earlier | see README |
| Leigh | ingested (pooled 2017-2026) | https://leigh.cuhsd.org/apps/pages/LeighGraduatesColleges (embedded published Google Sheet) |
| Menlo-Atherton | ingested 2022-2025 | https://www.mabears.org/about-ma/school-profile/where-do-our-grads-go -> CollegeDestinations22-25.pdf (a *selected* list of colleges, not exhaustive) |
| Dublin | ingested 2019-2022, 2024-2026 (no 2023 file found) | exit-survey PDFs on https://dhs.dublinusd.org (self-reported; unnumbered colleges counted as 1) |
| Northgate | ingested 2018-2020 | Northgate Sentinel "College Destinations" articles (counts = number of names listed per college; names not stored). 2017 article https://northgatesentinel.com/1898/college-destinations/college-destinations/ returns 403 here; 2016 article has a different layout (not parsed) |
| Mission San Jose, Irvington | NOT accessible | fremontunified.org returns 403 to this environment |
| Saratoga | no counts found | profiles on lgsuhsd.org only have category percentages; no 2017 file found |
| Dougherty Valley | no counts found | profiles (dvhs.srvusd.net / cloudfront) only have percentages; no per-year matriculation file on the college & career pages |
| Los Altos, Mountain View | no counts found | mvla.net old profile PDFs are 404; current profile page is an embedded widget; 2017 "College Attendance Data" PDFs have rates only |
| Leland | no counts found | https://leland.sjusd.org 2024-25 profile has no college list |
| Milpitas | no counts found | profile (Google doc) only has 4yr/2yr/work percentages |

Please send the original links for the "no counts found / not accessible" schools if you have them.


## D. Follow-up: historical profiles checked (2026-10-12)

- **Mission San Jose** — user-provided index page https://fremontunified.org/msjhs/students-community/student-support/counselors-overview/school-profiles/ is behind a Cloudflare interactive challenge ("Just a moment…"): HTTP 403 for curl, WebFetch and a real headless Chromium. Not bypassed. Needs a manual download of the profile PDFs (any year that lists colleges with counts) into the repo, then add a row to `data/sources.csv`. The same applies to Irvington / American / Washington / Kennedy (same district site).
- **Saratoga** — only 2023-24 and 2026-27 profiles + the 2019-20 WASC self-study are published; none lists colleges.
- **Leland** — only the 2024-25 profile is published (https://leland.sjusd.org/about/school-performance); no college list.
- **Dougherty Valley** — profiles 2022-23, 2023-24, 2026-27 exist; they only give percentages (4-year / 2-year / other). Older profiles not found.
- **Mountain View / Los Altos (MVLA)** — only the MVHS 2023-24 profile (thrillshare copy) is still downloadable; it has no college list. The older mvla.net PDFs (2017-18 … 2022-23, LAHS 2019-2023) return 404.
- **Milpitas** — 2024-25 profile (Google doc) only has percentages.


## E. Private schools (checked 2026-10-12)

Ingested with per-college counts: Marin Academy (2023-26, 2026), Urban School of SF (2022-26), Head-Royce (2021-25),
Menlo School (2024-26), Lick-Wilmerding (2023-26), Branson (2024-26).  The 13 private schools in the user's sheet
(Nueva, Harker, Crystal Springs, Branson, SFUHS, LWHS, Menlo, Head-Royce, Quarry Lane, International HS/"SF International",
Urban, Bellarmine, St. Francis) are also in the DB from the user's sheet (origin = user_sheet).

Found but NOT ingested (no per-college counts):
- Names only: SFUHS https://www.sfuhs.org/learning/college-counseling/college-matriculation ; Crystal Springs profile https://www.crystal.org/ftpimages/350/download/download_11136711.pdf ; Sacred Heart Prep profile https://shschools.myschoolapp.com/ftpimages/783/download/download_2023011.pdf ; Castilleja profile ; Pinewood profile ; Marin Catholic profile ; Valley Christian / San Domenico / Presentation / Quarry Lane / Harker "college acceptances" pages (acceptances, not matriculation).
- Tiers only ("10 or more", "5 or more"): Nueva https://www.nuevaschool.org/fs/resource-manager/view/40e38c23-2bd7-486a-b402-33e68739b9fe
- Acceptances with counts, matriculation only starred: Archbishop Mitty profile https://www.mitty.com/assets/files/academics/schoolprofile.pdf
- Not machine-readable / not reachable: Woodside Priory lists (Adobe Acrobat share links on prioryca.org); Convent & Stuart Hall (issuu profiles); St. Francis HS profile https://www.sfhs.com/ams/SchoolProfile_202526-1206.pdf (HTTP 400); Bellarmine / SI profiles (no list with counts); College Prep, Athenian, Bishop O'Dowd, Drew, Kehillah, Notre Dame Belmont, Mercy Burlingame, De La Salle, Sacred Heart Cathedral: no college list found on their sites.
