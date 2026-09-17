import pathlib, subprocess, sys, csv
import rdflib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

HTO = "http://purl.obolibrary.org/obo/HTO_"

def convert_example(tmp_path):
    out = tmp_path / "out.ttl"
    r = subprocess.run([sys.executable, "scripts/sheet2rdf.py",
                        "data/raw/example_tasting.csv", str(out), "--session", "test"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    g = rdflib.Graph(); g.parse(out, format="turtle")
    return g

def test_emits_one_assertion_per_rated_quality(tmp_path):
    g = convert_example(tmp_path)
    assertions = set(g.subjects(rdflib.RDF.type, rdflib.URIRef(HTO + "0000005")))
    with open(ROOT / "data/raw/example_tasting.csv") as fh:
        rows = [r for r in csv.DictReader(fh) if r["consent"].strip().lower() == "yes"]
    # four rated qualities per row: sweetness, sourness, bitterness, astringency
    assert len(assertions) == 4 * len(rows)

def test_ratings_round_trip(tmp_path):
    g = convert_example(tmp_path)
    values = [float(o) for o in g.objects(None, rdflib.URIRef(HTO + "0000070"))]
    assert values and all(0 <= v <= 100 for v in values)

def test_rows_without_consent_are_dropped(tmp_path):
    g = convert_example(tmp_path)
    ttl = g.serialize(format="turtle")
    assert "P99" not in ttl, "the no-consent participant must not appear"

def test_out_of_range_rating_is_rejected(tmp_path):
    bad = tmp_path / "bad.csv"
    src = (ROOT / "data/raw/example_tasting.csv").read_text().splitlines()
    header, first = src[0], src[1].split(",")
    cols = header.split(",")
    first[cols.index("sweetness")] = "555"
    bad.write_text("\n".join([header, ",".join(first)]))
    r = subprocess.run([sys.executable, "scripts/sheet2rdf.py", str(bad),
                        str(tmp_path / "x.ttl"), "--session", "t"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and "555" in (r.stdout + r.stderr)
