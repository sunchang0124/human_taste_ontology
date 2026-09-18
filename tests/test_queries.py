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
    assert r.stdout.count("PASS") >= 14, r.stdout

def test_every_cq_file_is_valid_sparql():
    import rdflib.plugins.sparql as sp
    for q in sorted((ROOT / "queries").glob("*.rq")):
        sp.prepareQuery(q.read_text())

def test_profile_questions_run_against_the_profile_graph(tmp_path):
    """cq09-cq14 are only meaningful with the profile graph loaded; running them
    against the tasting data alone would pass vacuously if they were written
    loosely."""
    profiles = tmp_path / "profiles.ttl"
    subprocess.run([sys.executable, "scripts/profile2rdf.py",
                    "data/raw/example_profiles.csv", str(profiles),
                    "--tastants", "data/raw/example_food_tastants.csv",
                    "--gap-report", str(tmp_path / "gaps.md")], cwd=ROOT, check=True)
    r = subprocess.run([sys.executable, "scripts/validate.py", "--profiles", str(profiles)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for cq in ("cq09", "cq10", "cq11", "cq12", "cq13", "cq14"):
        assert f"PASS  {cq}" in r.stdout.replace("  ", "  "), f"{cq} returned no rows\n{r.stdout}"
