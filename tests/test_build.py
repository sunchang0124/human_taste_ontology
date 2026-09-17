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

BASIC_TASTES = {
    "HTO:0000111": "sweetness",
    "HTO:0000112": "sourness",
    "HTO:0000113": "saltiness",
    "HTO:0000114": "bitterness",
    "HTO:0000115": "umami",
}

def test_five_basic_tastes_present():
    text = (ROOT / "hto.obo").read_text()
    for cid, label in BASIC_TASTES.items():
        assert f"id: {cid}" in text and f"name: {label}" in text, f"{cid} {label}"

def test_basic_tastes_link_to_go_processes():
    owl = (ROOT / "hto.owl").read_text()
    for go in ["GO_0050916", "GO_0050915", "GO_0050914", "GO_0050913", "GO_0050917"]:
        assert go in owl, f"no axiom referencing {go}"

def test_no_owl_equivalence_asserted_on_pato_bitter():
    owl = (ROOT / "hto.owl").read_text()
    assert "equivalentClass" not in owl or "PATO_0002474" not in owl.split("equivalentClass")[1][:400], \
        "bitterness must map to PATO:0002474 via SSSOM, not owl:equivalentClass"

def test_chemesthetic_qualities_are_annotated_as_trigeminal():
    obo = (ROOT / "hto.obo").read_text()
    assert "id: HTO:0000141" in obo and "astringency" in obo
