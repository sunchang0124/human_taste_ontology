#!/usr/bin/env python3
"""Convert the SSSOM mapping tables into RDF so they can be queried.

The SSSOM TSVs under ``mappings/`` are the authoritative bridge layer, but a
TSV cannot be joined against the ontology in SPARQL. This script emits one
triple per mapping row -- subject IRI, SKOS mapping predicate, object IRI --
into ``mappings/mappings.ttl``, which ``scripts/validate.py`` loads alongside
``hto.owl`` and the instance data. Competency questions cq04, cq05 and cq08
depend on it.

Nothing else is carried over: the justification, label and comment columns
stay in the TSVs, which remain the source of truth.
"""
from __future__ import annotations
import csv, pathlib, sys
from rdflib import Graph, Namespace, URIRef

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAPDIR = ROOT / "mappings"
OUT = MAPDIR / "mappings.ttl"

OBO = "http://purl.obolibrary.org/obo/"
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# Every prefix used as a subject or object in mappings/*.sssom.tsv. NCIT is
# listed explicitly because it is the one prefix whose OBO-library form is not
# obvious from the CURIE alone.
PREFIXES = {
    "HTO": OBO + "HTO_",
    "PATO": OBO + "PATO_",
    "GO": OBO + "GO_",
    "CHEBI": OBO + "CHEBI_",
    "OBA": OBO + "OBA_",
    "NCIT": OBO + "NCIT_",
    "FOODON": OBO + "FOODON_",
    "UBERON": OBO + "UBERON_",
    "OBI": OBO + "OBI_",
    "IAO": OBO + "IAO_",
    "HP": OBO + "HP_",
    "CL": OBO + "CL_",
}

PREDICATES = {
    "skos:exactMatch": SKOS.exactMatch,
    "skos:closeMatch": SKOS.closeMatch,
    "skos:broadMatch": SKOS.broadMatch,
    "skos:relatedMatch": SKOS.relatedMatch,
    "skos:narrowMatch": SKOS.narrowMatch,
}


class MappingError(Exception):
    pass


def expand(curie: str) -> URIRef:
    curie = curie.strip()
    if ":" not in curie:
        raise MappingError(f"{curie!r} is not a CURIE")
    prefix, local = curie.split(":", 1)
    base = PREFIXES.get(prefix)
    if base is None:
        raise MappingError(f"unknown prefix {prefix!r} in {curie!r}")
    return URIRef(base + local)


def convert(mapdir: pathlib.Path = MAPDIR, out: pathlib.Path = OUT) -> int:
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("obo", Namespace(OBO))

    written = 0
    for path in sorted(mapdir.glob("*.sssom.tsv")):
        with open(path) as fh:
            reader = csv.DictReader(
                (l for l in fh if not l.lstrip().startswith("#")), delimiter="\t")
            for row in reader:
                predicate = PREDICATES.get((row.get("predicate_id") or "").strip())
                if predicate is None:
                    raise MappingError(
                        f"{path.name}: unsupported predicate_id "
                        f"{row.get('predicate_id')!r} for {row.get('subject_id')}")
                g.add((expand(row["subject_id"]), predicate, expand(row["object_id"])))
                written += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=out, format="turtle")
    return written


def main() -> int:
    try:
        n = convert()
    except MappingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {OUT.relative_to(ROOT)}: {n} mapping triples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
