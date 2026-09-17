import pathlib, csv, subprocess, sys
import rdflib

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPORTS = ROOT / "src" / "imports" / "hto_imports.ttl"
TERMS = ROOT / "src" / "external_terms.tsv"

def curies():
    with open(TERMS) as fh:
        return [r["curie"] for r in csv.DictReader(fh, delimiter="\t")]

def test_every_listed_term_is_imported():
    g = rdflib.Graph(); g.parse(IMPORTS, format="turtle")
    subjects = {str(s) for s in g.subjects()}
    missing = []
    for c in curies():
        pfx, local = c.split(":")
        iri = f"http://purl.obolibrary.org/obo/{pfx}_{local}"
        if iri not in subjects:
            missing.append(c)
    assert not missing, f"not imported: {missing}"

def test_every_imported_term_has_a_label():
    g = rdflib.Graph(); g.parse(IMPORTS, format="turtle")
    RDFS = rdflib.RDFS
    unlabelled = [str(s) for s in set(g.subjects()) if (s, RDFS.label, None) not in g]
    assert not unlabelled, f"no label: {unlabelled[:5]}"

def test_script_is_idempotent():
    before = IMPORTS.read_bytes()
    subprocess.run([sys.executable, "scripts/build_imports.py"], cwd=ROOT, check=True)
    assert IMPORTS.read_bytes() == before, "build_imports.py is not deterministic"
