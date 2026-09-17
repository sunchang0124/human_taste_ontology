import pathlib, subprocess, sys
import rdflib
ROOT = pathlib.Path(__file__).resolve().parent.parent
HTO = "http://purl.obolibrary.org/obo/HTO_"

# NOTE on deviation from the task-9 brief (per controller ruling C3):
# the brief's test asserted >= 3 HTO:0000009 threshold data, one per
# TAS2R38 diplotype, with the group means it supplied. Those group means
# were attributed to PMID:37432335, which does not exist as a PROP/TAS2R38
# paper (it resolves to an unrelated detoxification-supplement study).
# A real, on-topic paper was found (PMID:20980355, Mennella et al. 2011,
# Chem Senses, "Psychophysical dissection of genotype effects on human
# bitter perception"), which does group PROP thresholds by TAS2R38
# diplotype, but its abstract does not state the per-diplotype numeric
# threshold values or group sample sizes, and its full text is not open
# access. Per C3's third path, data/raw/published_tas2r38_prop.csv leaves
# threshold_mmol_per_l empty for all three rows with a note explaining why,
# and scripts/published2rdf.py must not emit a threshold datum for a row
# with no sourced value. This test checks that behaviour instead of the
# brief's literal row count.


def test_published_graph_has_diplotype_groups_and_citation(tmp_path):
    out = tmp_path / "published.ttl"
    r = subprocess.run([sys.executable, "scripts/published2rdf.py",
                        "data/raw/published_tas2r38_prop.csv", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    diplotypes = list(g.subjects(rdflib.RDF.type, rdflib.URIRef(HTO + "0000015")))
    assert len(diplotypes) >= 3, "expected one diplotype group per row"
    ttl = g.serialize(format="turtle")
    assert "PAV/PAV" in ttl and "AVI/AVI" in ttl
    assert "PMID" in ttl or "pubmed" in ttl.lower(), "provenance citation is required"


def test_published_graph_does_not_fabricate_threshold_values(tmp_path):
    """No numeric per-diplotype PROP threshold could be sourced from the
    cited paper's abstract (full text is not open access), so the converter
    must not invent HTO:0000009 threshold data for these rows."""
    out = tmp_path / "published.ttl"
    subprocess.run([sys.executable, "scripts/published2rdf.py",
                    "data/raw/published_tas2r38_prop.csv", str(out)],
                   cwd=ROOT, check=True)
    g = rdflib.Graph(); g.parse(out, format="turtle")
    thresholds = list(g.subjects(rdflib.RDF.type, rdflib.URIRef(HTO + "0000009")))
    assert len(thresholds) == 0
