#!/usr/bin/env python3
"""Resolve every PMID in the templates and the profile data against PubMed.

Ten of the eleven citations proposed during the v1 build were fabricated: real
identifiers pointing at unrelated papers (docs/findings.md section 4). This
script exists so that failure mode is caught by a command rather than by a
reader. It touches the network and is therefore excluded from `make test`.
"""
from __future__ import annotations
import json, pathlib, re, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PMID = re.compile(r"PMID:(\d+)")
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def sources() -> list[pathlib.Path]:
    return sorted(
        list((ROOT / "src" / "templates").glob("*.tsv"))
        + list((ROOT / "data" / "raw").glob("*.csv"))
    )


def main() -> int:
    found: dict[str, list[str]] = {}
    for path in sources():
        for pmid in PMID.findall(path.read_text()):
            found.setdefault(pmid, []).append(path.name)
    if not found:
        print("no PMIDs found")
        return 0
    query = urllib.parse.urlencode({"db": "pubmed", "retmode": "json",
                                    "id": ",".join(sorted(found))})
    with urllib.request.urlopen(f"{ESUMMARY}?{query}", timeout=30) as response:
        payload = json.load(response)
    result = payload.get("result", {})
    failures = 0
    for pmid in sorted(found):
        record = result.get(pmid)
        if not record or record.get("error"):
            print(f"UNRESOLVED  PMID:{pmid}  cited in {', '.join(found[pmid])}")
            failures += 1
            continue
        print(f"OK          PMID:{pmid}  {record.get('title', '')[:90]}")
        print(f"                        cited in {', '.join(found[pmid])}")
    print(f"\n{failures} unresolved of {len(found)}")
    print("Resolution is necessary, not sufficient: read each title above and "
          "confirm it supports the claim that cites it.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
