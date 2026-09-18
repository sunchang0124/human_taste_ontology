"""The profile converter: one happy path, and every rejection path separately."""
import pathlib, subprocess, sys
import pytest
import rdflib
from rdflib.namespace import RDF, RDFS

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
HTO = "http://purl.obolibrary.org/obo/HTO_"

HEADER = ("food_id,food_label,quality,level,phase,taster_group,"
          "source_type,source,explained_by\n")
GOOD = HEADER + (
    "FOODON:03301710,satsuma juice,sweetness,strong,,,personal tasting,C. Sun 2026-09-18,\n"
    ",iyokan juice,bitterness,slight,finish,,personal tasting,C. Sun 2026-09-18,\n"
)


def write(tmp_path, text, name="profiles.csv"):
    path = tmp_path / name
    path.write_text(text)
    return path


def run(tmp_path, text, extra=()):
    csv_path = write(tmp_path, text)
    out = tmp_path / "profiles.ttl"
    return subprocess.run(
        [sys.executable, "scripts/profile2rdf.py", str(csv_path), str(out),
         "--gap-report", str(tmp_path / "gaps.md"), *extra],
        cwd=ROOT, capture_output=True, text=True), out


def test_a_valid_sheet_produces_one_entry_per_row(tmp_path):
    result, out = run(tmp_path, GOOD)
    assert result.returncode == 0, result.stdout + result.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    entries = list(g.subjects(RDF.type, rdflib.URIRef(HTO + "0000400")))
    assert len(entries) == 2


def test_defaults_are_applied_for_blank_phase_and_group(tmp_path):
    """A person writing a row by hand supplies neither. Blank must mean
    'overall' and 'general population', not 'absent from the graph'."""
    result, out = run(tmp_path, GOOD)
    assert result.returncode == 0
    g = rdflib.Graph(); g.parse(out, format="turtle")
    phases = set(g.objects(None, rdflib.URIRef(HTO + "0000083")))
    groups = set(g.objects(None, rdflib.URIRef(HTO + "0000084")))
    assert rdflib.URIRef(HTO + "0000214") in phases   # overall
    assert rdflib.URIRef(HTO + "0000221") in groups   # general population


def test_an_unmapped_food_is_reported_and_never_typed_as_foodon(tmp_path):
    result, out = run(tmp_path, GOOD)
    assert result.returncode == 0
    report = (tmp_path / "gaps.md").read_text()
    assert "iyokan juice" in report
    assert "satsuma juice" not in report
    g = rdflib.Graph(); g.parse(out, format="turtle")
    assert not [s for s in g.subjects() if "FOODON" in str(s) and "iyokan" in str(s).lower()]


def test_a_precoordinated_quality_is_normalised(tmp_path):
    """'delayed bitterness' is accepted and rewritten to bitterness at the
    finish, so old and new spellings land on the same queryable shape."""
    sheet = HEADER + ",iyokan juice,delayed bitterness,moderate,,,personal tasting,C. Sun,\n"
    result, out = run(tmp_path, sheet)
    assert result.returncode == 0, result.stdout + result.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    assert rdflib.URIRef(HTO + "0000114") in set(g.objects(None, rdflib.URIRef(HTO + "0000081")))
    assert rdflib.URIRef(HTO + "0000213") in set(g.objects(None, rdflib.URIRef(HTO + "0000083")))


@pytest.mark.parametrize("row,fragment", [
    (",iyokan juice,zestiness,slight,,,personal tasting,C. Sun,", "zestiness"),
    (",iyokan juice,bitterness,quite a lot,,,personal tasting,C. Sun,", "quite a lot"),
    (",iyokan juice,bitterness,slight,,,hearsay,C. Sun,", "hearsay"),
    (",iyokan juice,bitterness,slight,,,personal tasting,,", "source"),
    (",iyokan juice,bitterness,slight,,,literature,Aoki 2023,", "PMID"),
    ("FOOD:1,iyokan juice,bitterness,slight,,,personal tasting,C. Sun,", "FOOD:1"),
    (",iyokan juice,bitterness,slight,,,personal tasting,C. Sun,HTO:0009999", "HTO:0009999"),
])
def test_bad_rows_are_rejected_with_a_useful_message(tmp_path, row, fragment):
    result, out = run(tmp_path, HEADER + row + "\n")
    assert result.returncode == 1, "a bad row was accepted"
    assert fragment in result.stderr, result.stderr
    assert not out.exists(), "a rejected run must write no graph at all"


def test_contradictory_duplicate_rows_are_rejected(tmp_path):
    sheet = HEADER + (
        ",iyokan juice,bitterness,slight,finish,,personal tasting,C. Sun,\n"
        ",iyokan juice,bitterness,strong,finish,,personal tasting,C. Sun,\n"
    )
    result, _ = run(tmp_path, sheet)
    assert result.returncode == 1
    assert "duplicate" in result.stderr.lower() or "contradic" in result.stderr.lower()


def test_tastants_become_contains_tastant_triples(tmp_path):
    tastants = write(tmp_path, "food_id,food_label,tastant,source_type,source\n"
                               ",iyokan juice,CHEBI:16226,literature,PMID:12595690\n",
                     name="tastants.csv")
    result, out = run(tmp_path, GOOD, extra=("--tastants", str(tastants)))
    assert result.returncode == 0, result.stdout + result.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    objects = set(g.objects(None, rdflib.URIRef(HTO + "0000086")))
    assert rdflib.URIRef("http://purl.obolibrary.org/obo/CHEBI_16226") in objects


def test_full_ontology_label_taster_group_is_accepted(tmp_path):
    """Controller ruling R2: the ontology labels the seeded groups 'TAS2R38
    PAV/PAV taster group', 'PROP super-taster group' and so on, while the
    short form 'tas2r38 pav/pav' / 'prop super-taster' also has to work. A
    contributor writing either form must succeed and land on the same
    individual."""
    sheet = HEADER + (
        ",PROP test strip,bitterness,intense,overall,PROP super-taster group,"
        "literature,PMID:37242298,\n"
    )
    result, out = run(tmp_path, sheet)
    assert result.returncode == 0, result.stdout + result.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    groups = set(g.objects(None, rdflib.URIRef(HTO + "0000084")))
    assert rdflib.URIRef(HTO + "0000229") in groups


def test_two_foods_sharing_a_label_stay_two_entries(tmp_path):
    """V9 keys identity on the food node, so the entry IRI must too.

    One row with a FoodOn id and one without are two different foods that
    happen to share a label. Keying the entry IRI on the label let them pass
    V9 and then merge, producing a single entry carrying both levels and both
    sources -- V9 bypassed by the very rows it exists to catch.
    """
    sheet = HEADER + (
        ",pear juice,sweetness,strong,,,personal tasting,X,\n"
        "FOODON:03301710,pear juice,sweetness,slight,,,personal tasting,Y,\n"
    )
    result, out = run(tmp_path, sheet)
    assert result.returncode == 0, result.stdout + result.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    entries = list(g.subjects(RDF.type, rdflib.URIRef(HTO + "0000400")))
    assert len(entries) == 2, "two foods collapsed onto one profile entry"
    for entry in entries:
        assert len(list(g.objects(entry, rdflib.URIRef(HTO + "0000082")))) == 1
        assert len(list(g.objects(entry, rdflib.URIRef(HTO + "0000093")))) == 1


def test_error_line_numbers_are_physical_file_lines(tmp_path):
    """The shipped template carries thirteen `#` comment lines, so numbering
    the comment-stripped stream would misdirect every error a newcomer gets.
    Here the bad row sits on physical line 6."""
    sheet = ("# one\n# two\n# three\n" + HEADER
             + ",iyokan juice,bitterness,slight,,,personal tasting,C. Sun,\n"
             + ",iyokan juice,zestiness,slight,,,personal tasting,C. Sun,\n")
    result, _ = run(tmp_path, sheet)
    assert result.returncode == 1
    assert "line 6:" in result.stderr, result.stderr


TASTANT_HEADER = "food_id,food_label,tastant,source_type,source\n"


@pytest.mark.parametrize("row,fragment", [
    (",iyokan juice,CHEBI:16226,,limonin is in citrus juice", "source_type"),
    (",iyokan juice,CHEBI:16226,hearsay,limonin is in citrus juice", "hearsay"),
    (",iyokan juice,CHEBI:16226,literature,Raithore et al. 2015", "neither a PMID"),
    (",iyokan juice,CHEBI:16226,expert assertion,", "source is empty"),
])
def test_tastant_rows_are_held_to_the_profile_sheets_provenance_rule(tmp_path, row,
                                                                     fragment):
    """Both sheets describe the same foods; holding their sources to two
    different standards is how `source_type: literature` with free text got in
    one sheet while V6 forbade it in the other."""
    tastants = write(tmp_path, TASTANT_HEADER + row + "\n", name="tastants.csv")
    result, out = run(tmp_path, GOOD, extra=("--tastants", str(tastants)))
    assert result.returncode == 1, "a tastant row with bad provenance was accepted"
    assert fragment in result.stderr, result.stderr
    assert not out.exists(), "a rejected run must write no graph at all"


def test_the_shipped_tastant_template_has_the_columns_the_converter_reads():
    lines = [l for l in (ROOT / "data" / "food_tastants.csv").read_text().splitlines()
             if not l.lstrip().startswith("#")]
    assert lines[0] == TASTANT_HEADER.strip()
    assert len(lines) == 1, "the shipped template is blank apart from its header"
