import argparse

from . import ingest, reference

ap = argparse.ArgumentParser(prog="ranking")
ap.add_argument("cmd", choices=["build-reference", "ingest"])
ap.add_argument("--force-fetch", action="store_true")
a = ap.parse_args()
if a.cmd == "build-reference":
    reference.build_all()
else:
    ingest.ingest_all(a.force_fetch)
