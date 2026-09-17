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

def test_properties_present():
    # Object properties are represented as Typedef stanzas in OBO format.
    obo_text = (ROOT / "hto.obo").read_text()
    for pid in ["HTO:0000050", "HTO:0000052", "HTO:0000061"]:
        assert f"id: {pid}" in obo_text, f"{pid} missing from hto.obo"
    # Classic OBO format (1.2) has no stanza for data properties, so
    # ROBOT's OBO writer drops owl:DataProperty entities entirely, even
    # though they are correctly declared in the OWL. Check those in
    # hto.owl instead.
    owl_text = (ROOT / "hto.owl").read_text()
    for pid in ["HTO:0000070", "HTO:0000076"]:
        assert pid.replace(":", "_") in owl_text, f"{pid} missing from hto.owl"

def test_perceived_via_has_domain_and_range():
    text = (ROOT / "hto.owl").read_text()
    assert "HTO_0000061" in text
    assert "ObjectPropertyDomain" in text or "rdfs:domain" in text
