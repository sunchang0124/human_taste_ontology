import csv, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
MAPDIR = ROOT / "mappings"
REQUIRED = ["subject_id", "predicate_id", "object_id", "mapping_justification"]

def rows(name):
    with open(MAPDIR / name) as fh:
        return list(csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t"))

def test_all_mapping_files_have_sssom_columns():
    for f in MAPDIR.glob("*.sssom.tsv"):
        with open(f) as fh:
            header = next(l for l in fh if not l.startswith("#")).rstrip("\n").split("\t")
        for col in REQUIRED:
            assert col in header, f"{f.name} lacks {col}"

def test_bitterness_maps_to_pato_bitter():
    hits = [r for r in rows("hto-pato.sssom.tsv")
            if r["subject_id"] == "HTO:0000114" and r["object_id"] == "PATO:0002474"]
    assert hits and hits[0]["predicate_id"] == "skos:exactMatch"

def test_gap_report_lists_the_four_missing_basic_tastes(tmp_path):
    out = tmp_path / "pato-gap-report.md"
    subprocess.run([sys.executable, "scripts/gap_report.py", str(out)],
                   cwd=ROOT, check=True)
    text = out.read_text()
    for label in ["sweetness", "sourness", "saltiness", "umami"]:
        assert label in text, f"{label} should be reported as absent from PATO"
    assert "bitterness" in text
