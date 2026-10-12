import argparse

from . import import_user_sheet, ingest, reference, uc

ap = argparse.ArgumentParser(prog="ranking")
ap.add_argument("cmd", choices=["build-reference", "ingest", "import-user-sheet", "load-uc"])
ap.add_argument("--force-fetch", action="store_true")
a = ap.parse_args()
if a.cmd == "build-reference":
    reference.build_all()
elif a.cmd == "load-uc":
    uc.load()
elif a.cmd == "import-user-sheet":
    import_user_sheet.run()
else:
    ingest.ingest_all(a.force_fetch)
