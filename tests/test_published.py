import pathlib, subprocess, sys
import rdflib
ROOT = pathlib.Path(__file__).resolve().parent.parent
HTO = "http://purl.obolibrary.org/obo/HTO_"

# NOTE on deviations from the task-9 brief (per controller rulings C3 and the
# coordinator's fix-round-1 message):
#
# The brief's test asserted >= 3 HTO:0000009 threshold data, one per TAS2R38
# diplotype, with the group means the brief supplied. Those group means were
# attributed to PMID:37432335, which does not exist as a PROP/TAS2R38 paper
# (it resolves to an unrelated detoxification-supplement study) -- the
# numbers were fabricated.
#
# Fix round 1: the coordinator pointed at PMC10222862 (PMID:37242298; Aoki
# et al. 2023, "Association between Genetic Variation in the TAS2R38 Bitter
# Taste Receptor and Propylthiouracil Bitter Taste Thresholds among Adults
# Living in Japan Using the Modified 2AFC Procedure with the Quest Method",
# Nutrients 15(10):2415, doi:10.3390/nu15102415), open access, full text
# fetched via `efetch db=pmc id=10222862`. This is a real, on-topic study:
# 79 Japanese adults phenotyped for PROP threshold by the modified 2AFC/
# QUEST method and genotyped for TAS2R38, with the three diplotype groups
# PAV/PAV (n=24), PAV/AVI (n=43) and AVI/AVI (n=12) from Table 2, and
# significant pairwise threshold differences between all three groups
# (Results 3.2, one-way ANOVA F(2,76)=163.32, p<0.001).
#
# However, having read the full text (both tables, the whole Results and
# Discussion sections, and all four figure captions), no numeric per-
# diplotype mean/median threshold value (in mM or otherwise) is stated
# anywhere in extractable text -- only in Figure 3 (log-scale scatter plot)
# and Figure 4 (log-scale boxplot), which are images. This environment's
# network access is restricted to eutils.ncbi.nlm.nih.gov; attempts to fetch
# those figure images from www.ncbi.nlm.nih.gov, pmc.ncbi.nlm.nih.gov and
# mdpi.com all failed (redirects/403), so even an approximate visual read
# was not possible, and an approximate read would not have been "record them
# exactly" in any case. Per the coordinator's own fallback ("if the paper
# genuinely does not report per-group numeric thresholds in any table, say
# so with the evidence and keep your path-3 version"), threshold_mmol_per_l
# remains empty for all three rows and scripts/published2rdf.py still skips
# emitting a threshold datum for a row with no value. What changed from the
# first pass: the citation is now the real, correct PMID (37242298, not the
# fabricated 37432335 or the less-precisely-matched 20980355 used in the
# first draft), and the per-diplotype n values (24/43/12) are now the real
# ones from the paper's Table 2 rather than left blank.
#
# Fix round 2: independent review found that the brief's original script
# linked each literature group (and, in the unexercised `if value:` branch,
# each threshold datum) to its TAS2R38 diplotype with HTO:0000058 "has
# genotype assertion". That property's declared range is HTO:0000016 "taste
# genotype assertion" and its declared meaning is "relates a PERSON to a
# recorded assertion about their genotype" -- but the object emitted is
# typed HTO:0000015 "TAS2R38 diplotype" (not HTO:0000016), and the subject
# is a cohort group (or a threshold datum), not a person. That triple was
# live and semantically wrong in every published.ttl this script produced.
# The related issue in the `if value:` branch (HTO:0000052 "asserts
# quality", domain HTO:0000005 "taste percept assertion", applied to a
# HTO:0000009 "detection threshold datum") was latent because no threshold
# is currently emitted, but would have been wrong the moment real numbers
# were filled in. Per controller ruling, fixed both by adding two new
# properties (HTO:0000065 "has diplotype", no domain restriction, range
# HTO:0000015; HTO:0000066 "threshold for quality", domain HTO:0000009,
# range HTO:0000100) rather than bending the existing ones, and switched
# scripts/published2rdf.py to use them. This test asserts the fix: the
# graph uses HTO:0000065 and never emits HTO:0000058.


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
    assert "PMID:37242298" in ttl, "provenance citation must be the real, verified PMID"


def test_published_graph_links_diplotype_with_the_correct_property(tmp_path):
    """HTO:0000058 'has genotype assertion' relates a person to a taste
    genotype assertion (range HTO:0000016); it must not be used to relate a
    literature cohort group to a diplotype (HTO:0000015). The converter must
    use HTO:0000065 'has diplotype' instead."""
    out = tmp_path / "published.ttl"
    subprocess.run([sys.executable, "scripts/published2rdf.py",
                    "data/raw/published_tas2r38_prop.csv", str(out)],
                   cwd=ROOT, check=True)
    g = rdflib.Graph(); g.parse(out, format="turtle")
    has_diplotype = rdflib.URIRef(HTO + "0000065")
    has_genotype_assertion = rdflib.URIRef(HTO + "0000058")
    assert list(g.triples((None, has_diplotype, None))), \
        "expected at least one HTO:0000065 has-diplotype triple"
    assert list(g.triples((None, None, has_genotype_assertion))) == [] and \
        list(g.triples((None, has_genotype_assertion, None))) == [], \
        "HTO:0000058 has genotype assertion must not be used to link a group or datum to a diplotype"


def test_published_graph_does_not_fabricate_threshold_values(tmp_path):
    """No numeric per-diplotype PROP threshold could be sourced from the
    cited paper's full text (the values exist only in log-scale figure
    images, unreadable from this environment), so the converter must not
    invent HTO:0000009 threshold data for these rows."""
    out = tmp_path / "published.ttl"
    subprocess.run([sys.executable, "scripts/published2rdf.py",
                    "data/raw/published_tas2r38_prop.csv", str(out)],
                   cwd=ROOT, check=True)
    g = rdflib.Graph(); g.parse(out, format="turtle")
    thresholds = list(g.subjects(rdflib.RDF.type, rdflib.URIRef(HTO + "0000009")))
    assert len(thresholds) == 0
