import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_validate_runs_all_competency_questions(tmp_path):
    # Converted into tmp_path, not over the committed data/rdf/example.ttl:
    # a test run must leave the working tree as it found it.
    data = tmp_path / "example.ttl"
    subprocess.run([sys.executable, "scripts/sheet2rdf.py",
                    "data/raw/example_tasting.csv", str(data),
                    "--session", "example"], cwd=ROOT, check=True)
    r = subprocess.run([sys.executable, "scripts/validate.py", "--data", str(data)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("PASS") >= 8, r.stdout

def test_every_cq_file_is_valid_sparql():
    import rdflib.plugins.sparql as sp
    for q in sorted((ROOT / "queries").glob("*.rq")):
        sp.prepareQuery(q.read_text())
