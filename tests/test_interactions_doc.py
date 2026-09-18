"""docs/interactions.md must not drift from the template it is generated from.

`make interactions-doc` is wired into neither `build` nor `test`, so the only
thing keeping the committed table in step with
`src/templates/interactions.tsv` is someone remembering to run it. This test
remembers instead. It is offline: the generator reads the templates and the
committed import module, and touches no network.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import interactions_md  # noqa: E402


def test_the_committed_table_matches_its_template(tmp_path, monkeypatch):
    regenerated = tmp_path / "interactions.md"
    monkeypatch.setattr(interactions_md, "OUT", regenerated)
    assert interactions_md.main() == 0
    committed = (ROOT / "docs" / "interactions.md").read_text()
    assert regenerated.read_text() == committed, (
        "docs/interactions.md is stale with respect to "
        "src/templates/interactions.tsv; run `make interactions-doc`")
