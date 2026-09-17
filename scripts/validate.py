#!/usr/bin/env python3
"""Run the competency questions against the ontology plus the instance data.

A competency question that returns nothing means the ontology cannot answer a
question it was built to answer, so this exits non-zero. The two qc_*.rq
queries are the inverse: they must return nothing.
"""
from __future__ import annotations
import pathlib, sys
from rdflib import Graph

ROOT = pathlib.Path(__file__).resolve().parent.parent
ONTOLOGY = ROOT / "hto.owl"
DATA = ROOT / "data" / "rdf" / "example.ttl"


def main() -> int:
    g = Graph()
    g.parse(ONTOLOGY, format="xml")
    if DATA.exists():
        g.parse(DATA, format="turtle")
    else:
        print(f"note: {DATA} absent; competency questions over instance data will be empty")

    failures = 0
    for path in sorted((ROOT / "queries").glob("*.rq")):
        rows = list(g.query(path.read_text()))
        must_be_empty = path.name.startswith("qc_")
        ok = (len(rows) == 0) if must_be_empty else (len(rows) > 0)
        print(f"{'PASS' if ok else 'FAIL'}  {path.name:18s} {len(rows):4d} rows"
              f"{'  (expected none)' if must_be_empty else ''}")
        if not ok:
            failures += 1
            for row in rows[:5]:
                print(f"        {row}")
    print(f"\n{failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
