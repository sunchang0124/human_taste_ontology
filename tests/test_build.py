"""Build-level tests: the ontology exists, reasons, and passes ROBOT report."""
import subprocess, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def run(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)

def test_build_produces_owl():
    r = run("make", "build")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (ROOT / "hto.owl").exists()

def test_report_has_no_errors():
    r = run("java", "-jar", "bin/robot.jar", "report",
            "--input", "hto.owl", "--profile", "src/report_profile.txt",
            "--base-iri", "http://purl.obolibrary.org/obo/HTO_",
            "--output", "tmp/report.tsv", "--fail-on", "ERROR")
    assert r.returncode == 0, r.stdout + r.stderr

def test_ontology_has_required_metadata():
    text = (ROOT / "hto.owl").read_text()
    for needle in ("Human Taste Ontology", "creativecommons.org/licenses/by/4.0", "hto.owl"):
        assert needle in text, f"missing {needle}"
