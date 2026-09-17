#!/usr/bin/env python3
"""Encode published group-level taste threshold data with HTO.

Demonstrates that the schema fits literature data, not only sheets we collect.
Each row becomes a detection threshold datum attached to a diplotype group --
unless the row carries no sourced numeric value, in which case the diplotype
group and its provenance are still recorded but no threshold datum is
fabricated. See data/raw/published_tas2r38_prop.csv for why the TAS2R38/PROP
rows currently have no sourced value: the cited study (PMID:37242298, Aoki
et al. 2023, Nutrients 15(10):2415, PMC10222862 -- open access, full text
read) groups subjects by TAS2R38 diplotype and reports significant
between-group differences in PROP threshold, but its full text states no
numeric per-diplotype threshold value anywhere -- those values appear only
in log-scale figure images that could not be fetched from this environment.
Real per-diplotype sample sizes (n) from the paper's Table 2 are recorded.
"""
from __future__ import annotations
import argparse, csv, pathlib
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

OBO = Namespace("http://purl.obolibrary.org/obo/")
EX = Namespace("https://w3id.org/hto/data/published/")
DCTERMS = Namespace("http://purl.org/dc/terms/")


def convert(csv_path: pathlib.Path, out_path: pathlib.Path) -> int:
    g = Graph()
    g.bind("obo", OBO); g.bind("ex", EX); g.bind("dcterms", DCTERMS)
    n = 0
    for row in csv.DictReader(open(csv_path)):
        slug = row["diplotype"].replace("/", "_")
        group = EX[f"group/{slug}"]
        datum = EX[f"threshold/{slug}"]
        diplotype = EX[f"diplotype/{slug}"]

        g.add((diplotype, RDF.type, OBO["HTO_0000015"]))
        g.add((diplotype, RDFS.label, Literal(row["diplotype"])))
        group_n = (row.get("n") or "").strip()
        group_label = f'{row["population"]}, TAS2R38 {row["diplotype"]}'
        if group_n:
            group_label += f' (n={group_n})'
        g.add((group, RDFS.label, Literal(group_label)))
        g.add((group, OBO["HTO_0000058"], diplotype))
        g.add((group, DCTERMS.source, Literal(row["citation"])))

        value = (row.get("threshold_mmol_per_l") or "").strip()
        if value:
            g.add((datum, RDF.type, OBO["HTO_0000009"]))
            g.add((datum, OBO["HTO_0000052"], OBO["HTO_0000131"]))   # thiourea bitterness
            g.add((datum, OBO["HTO_0000070"],
                   Literal(float(value), datatype=XSD.decimal)))
            g.add((datum, OBO["HTO_0000058"], diplotype))
            g.add((datum, DCTERMS.source, Literal(row["citation"])))
            note = (row.get("scale_note") or row.get("note") or "").strip()
            if note:
                g.add((datum, RDFS.comment, Literal(note)))
            n += 1
        else:
            # No sourced numeric value for this row: record why, on the group
            # itself, instead of inventing a threshold datum.
            note = (row.get("note") or row.get("scale_note") or "").strip()
            if note:
                g.add((group, RDFS.comment, Literal(note)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=out_path, format="turtle")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=pathlib.Path)
    ap.add_argument("out_path", type=pathlib.Path)
    args = ap.parse_args()
    print(f"wrote {args.out_path}: {convert(args.csv_path, args.out_path)} threshold data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
