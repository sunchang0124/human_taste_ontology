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

# Each basic taste and the GO perception process its HTO:0000061 restriction
# must point at. Grepping for the five GO identifiers anywhere in the file, as
# this test used to, passes even if the pairings are crossed -- sweetness
# pointing at the bitter process would have gone unnoticed.
GO_PAIRINGS = {
    "HTO_0000111": "GO_0050916",   # sweetness  -> sensory perception of sweet taste
    "HTO_0000112": "GO_0050915",   # sourness   -> sensory perception of sour taste
    "HTO_0000113": "GO_0050914",   # saltiness  -> sensory perception of salty taste
    "HTO_0000114": "GO_0050913",   # bitterness -> sensory perception of bitter taste
    "HTO_0000115": "GO_0050917",   # umami      -> sensory perception of umami taste
}

def test_basic_tastes_link_to_the_right_go_processes():
    import rdflib
    OBO = "http://purl.obolibrary.org/obo/"
    g = rdflib.Graph(); g.parse(ROOT / "hto.owl", format="xml")
    perceived_via = rdflib.URIRef(OBO + "HTO_0000061")

    found = {}
    for taste, restriction in g.subject_objects(rdflib.RDFS.subClassOf):
        if (restriction, rdflib.OWL.onProperty, perceived_via) not in g:
            continue
        for filler in g.objects(restriction, rdflib.OWL.someValuesFrom):
            found.setdefault(str(taste).replace(OBO, ""), set()).add(
                str(filler).replace(OBO, ""))

    for taste, go in GO_PAIRINGS.items():
        assert taste in found, f"{taste} has no HTO:0000061 restriction at all"
        assert found[taste] == {go}, \
            f"{taste} perceived-via should be exactly {{{go}}}, found {found[taste]}"

def test_no_owl_equivalence_asserted_on_pato_bitter():
    owl = (ROOT / "hto.owl").read_text()
    assert "equivalentClass" not in owl or "PATO_0002474" not in owl.split("equivalentClass")[1][:400], \
        "bitterness must map to PATO:0002474 via SSSOM, not owl:equivalentClass"

def test_chemesthetic_qualities_are_annotated_as_trigeminal():
    obo = (ROOT / "hto.obo").read_text()
    assert "id: HTO:0000141" in obo and "astringency" in obo

def test_intensity_and_hedonic_rating_share_a_common_rating_superclass():
    # HTO:0000070 rating value applies to any rating, but intensity rating
    # (HTO:0000006) and hedonic rating (HTO:0000007) are siblings, not one a
    # subclass of the other, so the property's domain had to name a common
    # parent rather than either sibling directly (see fix round 3).
    obo = (ROOT / "hto.obo").read_text()
    assert "id: HTO:0000026" in obo, "HTO:0000026 rating must exist"
    assert "name: rating" in obo.split("id: HTO:0000026")[1][:200], \
        "HTO:0000026 must be labelled 'rating'"

    def stanza(cid: str) -> str:
        return obo.split(f"id: {cid}\n")[1].split("\n\n")[0]

    assert "is_a: HTO:0000026" in stanza("HTO:0000006"), \
        "HTO:0000006 intensity rating must be a subclass of HTO:0000026 rating"
    assert "is_a: HTO:0000026" in stanza("HTO:0000007"), \
        "HTO:0000007 hedonic rating must be a subclass of HTO:0000026 rating"


def test_no_hto_iri_is_both_an_object_and_a_data_property():
    """Punning an IRI as both an object property and a data property makes the
    ontology OWL 2 DL invalid. HTO:0000061 was punned this way because
    qualities.tsv's `SC HTO:0000061 some %` column was templated without the
    properties module for context, so ROBOT emitted a bare datatype
    declaration; the Makefile now passes tmp/properties.owl as --input.
    Computed by parsing so the whole class of defect is guarded, not one IRI."""
    import rdflib
    HTO = "http://purl.obolibrary.org/obo/HTO_"
    g = rdflib.Graph(); g.parse(ROOT / "hto.owl", format="xml")

    def declared_as(kind):
        return {str(s) for s in g.subjects(rdflib.RDF.type, kind)
                if str(s).startswith(HTO)}

    object_props = declared_as(rdflib.OWL.ObjectProperty)
    data_props = declared_as(rdflib.OWL.DatatypeProperty)
    assert object_props and data_props, "expected HTO to declare both kinds"
    assert not (object_props & data_props), \
        f"declared as both an object and a data property: {sorted(object_props & data_props)}"
