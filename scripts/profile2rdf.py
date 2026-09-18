#!/usr/bin/env python3
"""Convert a taste profile CSV into RDF instance data typed by HTO.

Each row becomes one HTO:0000400 taste profile entry: a single quality, at a
single ordinal level, at a single phase, holding for a single taster group,
from a single named source. Two rows differing only in taster group are how a
food that tastes different to different people is written down.

Vocabularies are resolved from the templates rather than from the built
ontology, so the converter runs without Java and without a build.
"""
from __future__ import annotations
import argparse, csv, pathlib, re, sys
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

ROOT = pathlib.Path(__file__).resolve().parent.parent
OBO = Namespace("http://purl.obolibrary.org/obo/")
EX = Namespace("https://w3id.org/hto/data/")

LEVELS = {"absent": "0000201", "slight": "0000202", "moderate": "0000203",
          "strong": "0000204", "intense": "0000205"}
PHASES = {"attack": "0000211", "mid-palate": "0000212", "finish": "0000213",
          "overall": "0000214"}
# The ontology labels the seeded groups with a "taster group" / "group" suffix
# ("TAS2R38 PAV/PAV taster group", "PROP super-taster group"), but a shorter
# form is easier to type by hand. Controller ruling R2: accept both forms and
# map them to the same individual; "general population" carries no suffix in
# either form, so it needs only one key.
GROUPS = {"general population": "0000221",
          "tas2r38 pav/pav": "0000224", "tas2r38 pav/pav taster group": "0000224",
          "tas2r38 pav/avi": "0000225", "tas2r38 pav/avi taster group": "0000225",
          "tas2r38 avi/avi": "0000226", "tas2r38 avi/avi taster group": "0000226",
          "prop non-taster": "0000227", "prop non-taster group": "0000227",
          "prop medium-taster": "0000228", "prop medium-taster group": "0000228",
          "prop super-taster": "0000229", "prop super-taster group": "0000229"}
EVIDENCE = {"literature": "0000241", "panel data": "0000242",
            "expert assertion": "0000243", "personal tasting": "0000244"}

# Accepted for continuity, rewritten to the post-coordinated form. See the
# rdfs:comment on each term in src/templates/qualities.tsv. Checked before the
# ordinary quality lookup: both terms are also ordinary entries in
# qualities.tsv (HTO:0000153, HTO:0000154), so a naive label lookup would
# match them as themselves and silently skip this normalisation.
PRECOORDINATED = {"lingering bitterness": ("0000114", "finish"),
                  "delayed bitterness": ("0000114", "finish")}

PMID_RE = re.compile(r"^PMID:\d+$")
DOI_RE = re.compile(r"^doi:10\.\d{4,9}/\S+$", re.IGNORECASE)
FOODON_RE = re.compile(r"^FOODON:\d+$")
CHEBI_RE = re.compile(r"^CHEBI:\d+$")

COLUMNS = ("food_id", "food_label", "quality", "level", "phase", "taster_group",
           "source_type", "source", "explained_by")


class ProfileError(Exception):
    pass


def hto(local: str) -> URIRef:
    return OBO[f"HTO_{local}"]


def curie_to_iri(curie: str) -> URIRef:
    prefix, local = curie.split(":", 1)
    return OBO[f"{prefix}_{local}"]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


class _CommentStrippingReader:
    """Feed ``csv.DictReader`` while remembering where each record really began.

    The ``#`` comment lines are dropped here rather than by a generator wrapped
    around the file, so that the line numbers in error messages are the ones a
    person sees in their editor. ``data/profile_sheet.csv`` ships with thirteen
    comment lines, so numbering the post-filter stream would misdirect every
    error a newcomer filling in the shipped template ever gets.
    """

    def __init__(self, handle):
        self._handle = handle
        self._pending: list[int] = []

    def __iter__(self):
        for number, line in enumerate(self._handle, start=1):
            if line.lstrip().startswith("#"):
                continue
            self._pending.append(number)
            yield line

    def take(self) -> int:
        """The physical file line on which the record just parsed began."""
        number = self._pending[0] if self._pending else 0
        self._pending.clear()
        return number


def sheet_rows(handle):
    """Return (fieldnames, iterator of (physical line number, row dict))."""
    tracker = _CommentStrippingReader(handle)
    reader = csv.DictReader(tracker)
    fieldnames = list(reader.fieldnames or ())
    tracker.take()                     # discard the header's own line number

    def rows():
        for row in reader:
            yield tracker.take(), row

    return fieldnames, rows()


def template_rows(name: str) -> list[dict]:
    path = ROOT / "src" / "templates" / name
    if not path.exists():
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))[1:]


def load_qualities() -> dict[str, str]:
    """label (lowercased) and CURIE -> local id, for every HTO quality."""
    index: dict[str, str] = {}
    for row in template_rows("qualities.tsv"):
        local = row["ID"].split(":", 1)[1]
        index[row["LABEL"].strip().lower()] = local
        index[row["ID"].strip()] = local
    return index


def load_interactions() -> dict[str, str]:
    """interaction CURIE -> its target quality CURIE, for rule V7."""
    return {row["ID"].strip(): (row.get("target") or "").strip()
            for row in template_rows("interactions.tsv")}


def convert(profiles_csv: pathlib.Path, out_path: pathlib.Path,
            tastants_csv: pathlib.Path | None = None,
            gap_report: pathlib.Path | None = None) -> int:
    qualities, interactions = load_qualities(), load_interactions()
    errors: list[str] = []
    graph = Graph()
    graph.bind("hto", OBO)
    graph.bind("ex", EX)
    seen: set[tuple] = set()
    unmapped: dict[str, str] = {}
    written = 0

    def food_node(row: dict, where: str) -> tuple[URIRef, str] | None:
        """The food's IRI, and the key any IRI derived from that food must use.

        V9 keys an entry's identity on the food *node*, so anything else keying
        the entry IRI can collapse two foods onto one entry: two rows labelled
        "pear juice", one carrying a FoodOn id and one not, resolve to different
        nodes, pass V9, and then meet again on a label-derived IRI. The key
        therefore comes from the same node V9 keys on.
        """
        label = (row.get("food_label") or "").strip()
        if not label:
            errors.append(f"{where}: food_label is empty")
            return None
        food_id = (row.get("food_id") or "").strip()
        if food_id:
            if not FOODON_RE.match(food_id):
                errors.append(f"{where}: food_id {food_id!r} is not a FOODON CURIE")
                return None
            prefix, local = food_id.split(":", 1)
            return curie_to_iri(food_id), f"{prefix.lower()}-{local}"
        unmapped[slug(label)] = label
        return EX[f"food/{slug(label)}"], slug(label)

    with open(profiles_csv) as fh:
        fieldnames, rows = sheet_rows(fh)
        missing = [c for c in COLUMNS if c not in fieldnames]
        if missing:
            raise ProfileError(f"{profiles_csv}: missing column(s): {', '.join(missing)}")

        for line, row in rows:
            resolved = food_node(row, f"line {line}")
            food, food_key = resolved if resolved is not None else (None, None)

            raw_quality = (row.get("quality") or "").strip()
            phase_text = (row.get("phase") or "").strip().lower() or "overall"
            key = raw_quality.lower()
            if key in PRECOORDINATED:
                quality_local, phase_text = PRECOORDINATED[key]
            else:
                quality_local = qualities.get(key) or qualities.get(raw_quality)
                if quality_local is None:
                    errors.append(f"line {line}: quality {raw_quality!r} is not an HTO quality")

            level_local = LEVELS.get((row.get("level") or "").strip().lower())
            if level_local is None:
                errors.append(f"line {line}: level {row.get('level')!r} is not one of "
                              f"{', '.join(LEVELS)}")
            phase_local = PHASES.get(phase_text)
            if phase_local is None:
                errors.append(f"line {line}: phase {phase_text!r} is not one of "
                              f"{', '.join(PHASES)}")
            group_text = (row.get("taster_group") or "").strip().lower() or "general population"
            group_local = GROUPS.get(group_text)
            if group_local is None:
                errors.append(f"line {line}: taster_group {group_text!r} is not one of "
                              f"{', '.join(GROUPS)}")

            evidence_text = (row.get("source_type") or "").strip().lower()
            evidence_local = EVIDENCE.get(evidence_text)
            if evidence_local is None:
                errors.append(f"line {line}: source_type {evidence_text!r} is not one of "
                              f"{', '.join(EVIDENCE)}")
            source = (row.get("source") or "").strip()
            if not source:
                errors.append(f"line {line}: source is empty; every claim names where it came from")
            elif evidence_text == "literature" and not (PMID_RE.match(source)
                                                        or DOI_RE.match(source)):
                errors.append(f"line {line}: source {source!r} claims to be literature but is "
                              f"neither a PMID: nor a doi:")

            interaction = (row.get("explained_by") or "").strip()
            if interaction:
                if interaction not in interactions:
                    errors.append(f"line {line}: explained_by {interaction} is not a known "
                                  f"interaction")
                elif quality_local and interactions[interaction] != f"HTO:{quality_local}":
                    errors.append(f"line {line}: explained_by {interaction} targets "
                                  f"{interactions[interaction]}, not this row's quality "
                                  f"HTO:{quality_local}")

            if None in (food, quality_local, level_local, phase_local, group_local,
                        evidence_local):
                continue

            identity = (str(food), quality_local, phase_local, group_local)
            if identity in seen:
                errors.append(f"line {line}: duplicate entry for the same food, quality, phase "
                              f"and taster group; two levels for one claim is a contradiction")
                continue
            seen.add(identity)

            entry = EX[f"profile/{food_key}/{quality_local}/"
                       f"{phase_local}/{group_local}"]
            graph.add((food, RDFS.label, Literal(row["food_label"].strip())))
            graph.add((food, hto("0000080"), entry))
            graph.add((entry, RDF.type, hto("0000400")))
            graph.add((entry, hto("0000081"), hto(quality_local)))
            graph.add((entry, hto("0000082"), hto(level_local)))
            graph.add((entry, hto("0000083"), hto(phase_local)))
            graph.add((entry, hto("0000084"), hto(group_local)))
            graph.add((entry, hto("0000093"), Literal(source)))
            graph.add((entry, hto("0000094"), hto(evidence_local)))
            if interaction:
                graph.add((entry, hto("0000091"), curie_to_iri(interaction)))
            written += 1

    if tastants_csv is not None:
        with open(tastants_csv) as fh:
            _, rows = sheet_rows(fh)
            for line, row in rows:
                where = f"{tastants_csv.name} line {line}"
                resolved = food_node(row, where)
                food = resolved[0] if resolved is not None else None
                bad = food is None
                tastant = (row.get("tastant") or "").strip()
                if not CHEBI_RE.match(tastant):
                    errors.append(f"{where}: tastant {tastant!r} is not a CHEBI CURIE")
                    bad = True
                # The same provenance discipline the profile sheet gets from V5
                # and V6. Without it a food-composition claim could name an
                # evidence type that does not exist, or -- worse -- declare
                # itself literature and then carry free text, which V6 forbids
                # one sheet over. Two sheets describing the same foods should
                # not hold their sources to two different standards.
                evidence_text = (row.get("source_type") or "").strip().lower()
                if evidence_text not in EVIDENCE:
                    errors.append(f"{where}: source_type {evidence_text!r} is not one of "
                                  f"{', '.join(EVIDENCE)}")
                    bad = True
                source = (row.get("source") or "").strip()
                if not source:
                    errors.append(f"{where}: source is empty; every claim names where "
                                  f"it came from")
                    bad = True
                elif evidence_text == "literature" and not (PMID_RE.match(source)
                                                            or DOI_RE.match(source)):
                    errors.append(f"{where}: source {source!r} claims to be literature "
                                  f"but is neither a PMID: nor a doi:")
                    bad = True
                if bad:
                    continue
                graph.add((food, RDFS.label, Literal(row["food_label"].strip())))
                graph.add((food, hto("0000086"), curie_to_iri(tastant)))

    if errors:
        raise ProfileError("\n".join(errors))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=out_path, format="turtle")

    if gap_report is not None:
        lines = ["# Foods with no FoodOn term", "",
                 "Generated by `scripts/profile2rdf.py`. Each food below is described in HTO",
                 "but has no FoodOn identifier, so it carries a local IRI and cannot yet be",
                 "joined against the wider food ecosystem. These are candidates for a FoodOn",
                 "new-term request; see `docs/term-requests/`.", ""]
        lines += [f"- {label} (`{key}`)" for key, label in sorted(unmapped.items())] or \
                 ["_None: every food carries a FoodOn identifier._"]
        gap_report.parent.mkdir(parents=True, exist_ok=True)
        gap_report.write_text("\n".join(lines) + "\n")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles_csv", type=pathlib.Path)
    parser.add_argument("out_path", type=pathlib.Path)
    parser.add_argument("--tastants", type=pathlib.Path, default=None)
    parser.add_argument("--gap-report", type=pathlib.Path,
                        default=ROOT / "docs" / "needs-foodon.md")
    args = parser.parse_args()
    try:
        n = convert(args.profiles_csv, args.out_path, args.tastants, args.gap_report)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out_path}: {n} profile entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
