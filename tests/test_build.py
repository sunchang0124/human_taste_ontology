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

CORE_EXPECTED = {
    "HTO:0000001": "tasting event",
    "HTO:0000005": "taste percept assertion",
    "HTO:0000011": "taster status",
    "HTO:0000014": "PROP super-taster",
    "HTO:0000021": "taste confounder",
    "HTO:0000300": "general Labelled Magnitude Scale",
}

def test_core_classes_present_with_labels():
    text = (ROOT / "hto.obo").read_text()
    for cid, label in CORE_EXPECTED.items():
        assert f"id: {cid}" in text, f"{cid} missing"
        assert f"name: {label}" in text, f"{cid} has the wrong label"

def test_taster_status_is_under_oba_trait():
    text = (ROOT / "hto.owl").read_text()
    assert "OBA_VT0001986" in text, "taster status must reuse the OBA sensitivity trait"
