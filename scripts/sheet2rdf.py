#!/usr/bin/env python3
"""Convert a tasting sheet CSV into RDF instance data typed by HTO.

Every rated quality becomes one HTO:0000005 taste percept assertion so that a
single person's single perception of a single sample is addressable.
"""
from __future__ import annotations
import argparse, csv, pathlib, sys
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD

OBO = Namespace("http://purl.obolibrary.org/obo/")
EX = Namespace("https://w3id.org/hto/data/")
HTO = {n: OBO[f"HTO_{n}"] for n in (
    "0000001", "0000005", "0000006", "0000007", "0000011", "0000012", "0000013",
    "0000014", "0000017", "0000021", "0000022", "0000023", "0000050", "0000051",
    "0000052", "0000053", "0000054", "0000055", "0000056", "0000057", "0000063",
    "0000070", "0000073", "0000076", "0000300", "0000302")}

QUALITY_COLUMNS = {
    "sweetness":   OBO["HTO_0000111"],
    "sourness":    OBO["HTO_0000112"],
    "bitterness":  OBO["HTO_0000114"],
    "astringency": OBO["HTO_0000141"],
}
PROP_STATUS = {"none": HTO["0000012"], "medium": HTO["0000013"], "strong": HTO["0000014"]}


class SheetError(Exception):
    pass


def check_range(row: dict, col: str, lo: float, hi: float) -> float:
    raw = (row.get(col) or "").strip()
    try:
        val = float(raw)
    except ValueError as exc:
        raise SheetError(f"row {row['participant_id']}/{row['sample_id']}: "
                         f"{col} is {raw!r}, expected a number") from exc
    if not lo <= val <= hi:
        raise SheetError(f"row {row['participant_id']}/{row['sample_id']}: "
                         f"{col} is {val:g}, outside the permitted range {lo:g}-{hi:g}")
    return val


def convert(csv_path: pathlib.Path, out_path: pathlib.Path, session_id: str) -> int:
    g = Graph()
    g.bind("hto", OBO)
    g.bind("ex", EX)
    session = EX[f"session/{session_id}"]
    g.add((session, RDF.type, HTO["0000017"]))

    written = 0
    with open(csv_path) as fh:
        reader = csv.DictReader(l for l in fh if not l.lstrip().startswith("#"))
        for row in reader:
            if (row.get("consent") or "").strip().lower() != "yes":
                continue
            pid, sid = row["participant_id"].strip(), row["sample_id"].strip()
            person = EX[f"participant/{session_id}/{pid}"]
            event = EX[f"event/{session_id}/{pid}/{sid}"]
            sample = EX[f"sample/{session_id}/{sid}"]

            g.add((event, RDF.type, HTO["0000001"]))
            g.add((event, HTO["0000050"], person))
            g.add((event, HTO["0000051"], sample))
            g.add((event, HTO["0000056"], session))
            g.add((event, HTO["0000073"],
                   Literal(int(check_range(row, "sample_order", 1, 99)), datatype=XSD.integer)))
            g.add((event, HTO["0000076"],
                   Literal(check_range(row, "minutes_since_opening", 0, 10000), datatype=XSD.decimal)))

            status = PROP_STATUS.get((row.get("prop_strip") or "").strip().lower())
            if status is not None:
                g.add((person, HTO["0000057"], status))
            if (row.get("current_smoker") or "").strip().lower() == "yes":
                g.add((person, RDF.type, HTO["0000022"]))
            if (row.get("recent_smell_loss") or "").strip().lower() == "yes":
                g.add((person, RDF.type, HTO["0000023"]))

            for col, quality in QUALITY_COLUMNS.items():
                value = check_range(row, col, 0, 100)
                assertion = EX[f"assertion/{session_id}/{pid}/{sid}/{col}"]
                rating = EX[f"rating/{session_id}/{pid}/{sid}/{col}"]
                g.add((assertion, RDF.type, HTO["0000005"]))
                g.add((assertion, HTO["0000052"], quality))
                g.add((assertion, HTO["0000053"], rating))
                g.add((rating, RDF.type, HTO["0000006"]))
                g.add((rating, HTO["0000070"], Literal(value, datatype=XSD.decimal)))
                g.add((rating, HTO["0000054"], HTO["0000300"]))
                g.add((event, HTO["0000063"], assertion))
                written += 1

            liking = EX[f"liking/{session_id}/{pid}/{sid}"]
            g.add((liking, RDF.type, HTO["0000007"]))
            g.add((liking, HTO["0000070"],
                   Literal(check_range(row, "liking", 1, 9), datatype=XSD.decimal)))
            g.add((liking, HTO["0000054"], HTO["0000302"]))
            g.add((event, HTO["0000055"], liking))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=out_path, format="turtle")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=pathlib.Path)
    ap.add_argument("out_path", type=pathlib.Path)
    ap.add_argument("--session", required=True)
    args = ap.parse_args()
    try:
        n = convert(args.csv_path, args.out_path, args.session)
    except SheetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out_path}: {n} percept assertions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
