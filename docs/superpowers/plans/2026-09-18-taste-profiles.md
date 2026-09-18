# HTO Taste Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give HTO a thing-centric layer — a kind of food or drink carries a taste profile, qualities interact with each other, and a profile entry can hold for one taster group rather than everyone.

**Architecture:** Curated general knowledge (slot vocabularies, interaction rules, quality→tastant links) is built into `hto.owl` from ROBOT templates. Open-ended per-food profiles are instance data, generated from a CSV by a new converter alongside the existing `sheet2rdf.py`. Six new SPARQL competency questions prove the layer answers the three questions it was built for.

**Tech Stack:** ROBOT 1.9.10 (Java 21), ROBOT templates (TSV), ELK reasoner, Python 3.9+, rdflib 7, pytest 7, GNU Make.

**Spec:** `docs/superpowers/specs/2026-09-18-taste-profiles-design.md` — read it before Task 1. This plan implements it and does not restate its reasoning.

## Global Constraints

- **Branch:** `feat/taste-profiles`, already cut from `main` at `cabfcee`. Do not merge or push.
- **Build must stay green at every commit:** `make build && make report` → 0 ERROR, and `python3 -m pytest tests/ -q` all passing. The report profile treats `missing_definition` and `missing_label` as ERRORs, so **every new term — classes, properties and named individuals alike — needs `A IAO:0000115` (definition) and `A IAO:0000119` (source, always `HTO:0000000`)**.
- **Identifier blocks are fixed by the spec §4.** Do not mint an ID outside the block the spec assigns.
- **Never write a citation you have not resolved.** In the v1 build ten of eleven proposed PMIDs were fabricated — real identifiers pointing at unrelated papers (`docs/findings.md` §4). Task 4 defines the verification procedure; it is mandatory, not advisory.
- **Templates are two-header-row TSVs.** Row 1 is the human header, row 2 is the ROBOT template string row; the repo keeps them identical except where a template string is needed. Tabs, not spaces.
- **`make test` must stay offline.** Anything touching the network goes in the `verify-citations` target, which is excluded from `test`.
- **Commit after every task** with a message body ending:

  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  ```

### Verified ROBOT template facts (probed 2026-09-18, do not re-derive)

| Need | Column directive | Result |
|---|---|---|
| Individual typed by an HTO class | `TYPE` with the class CURIE | emits `NamedIndividual` with `rdf:type` |
| Object property assertion between individuals | `I HTO:00000NN` | emits an object property assertion |
| Typed literal on an individual | `AT HTO:00000NN^^xsd:integer` | emits an **annotation** assertion with `rdf:datatype` |
| Plain `A prop^^xsd:integer` | — | **broken**: ROBOT reads the datatype as the property. Never use it. |
| `I <prop>` with a literal value | — | **fails** with `object cannot be null`. `I` is for IRIs only. |

Because `AT` emits an annotation, `HTO:0000092 level rank` and `HTO:0000095 interaction condition` are **annotation properties**, not data properties. The spec's §4.1 table says "data"; Task 1 Step 1 corrects the spec. `HTO:0000093 source statement` stays a data property: it appears only in script-generated instance data, never in a template.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `src/templates/properties.tsv` | modify | +18 properties (`0000080`–`0000097`) |
| `src/external_terms.tsv` | modify | +1 row, `CHEBI:24431` chemical entity |
| `src/templates/profiles.tsv` | **create** | the 9 new classes and 20 vocabulary individuals |
| `src/templates/qualities.tsv` | modify | +1 column `SC HTO:0000085 some %`, 8 elicitation rows, 2 demotion comments |
| `src/templates/interactions.tsv` | **create** | the verified interaction rules |
| `Makefile` | modify | `tmp/profiles.owl` rule, `profiles` and `verify-citations` targets |
| `scripts/profile2rdf.py` | **create** | profile + tastant CSV → `data/rdf/profiles.ttl` + gap report |
| `scripts/interactions_md.py` | **create** | `src/templates/interactions.tsv` → `docs/interactions.md` |
| `scripts/verify_citations.py` | **create** | resolve every PMID/DOI against PubMed (network) |
| `scripts/validate.py` | modify | load the profiles graph |
| `data/profile_sheet.csv` | **create** | blank template with `#` header guidance |
| `data/raw/example_profiles.csv` | **create** | seed profile rows |
| `data/raw/example_food_tastants.csv` | **create** | seed food→tastant rows |
| `queries/cq09.rq` … `cq14.rq` | **create** | six competency questions |
| `tests/test_profiles_ontology.py` | **create** | terms, vocabularies, interaction-row integrity |
| `tests/test_profile2rdf.py` | **create** | converter happy path + every rejection path |
| `README.md`, `docs/findings.md` | modify | document the layer |

---

## Task 1: New properties and the one new import

**Files:**
- Modify: `src/templates/properties.tsv` (append 18 rows)
- Modify: `src/external_terms.tsv` (append 1 row)
- Modify: `docs/superpowers/specs/2026-09-18-taste-profiles-design.md` (§4.1 correction)
- Test: `tests/test_profiles_ontology.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: properties `HTO:0000080`–`HTO:0000097`, used by every later task. Exact labels are in the table below and are referenced verbatim by Tasks 2, 3, 4, 5 and 7.

- [ ] **Step 1: Correct the spec's property-type table**

In `docs/superpowers/specs/2026-09-18-taste-profiles-design.md` §4.1, change the `Type` cell for `HTO:0000092 level rank` from `data (integer)` to `annotation (integer)` and for `HTO:0000095 interaction condition` from `data (string)` to `annotation (string)`. Immediately after the table's trailing paragraph about `CHEBI:24431`, add:

```markdown
`HTO:0000092` and `HTO:0000095` are annotation properties rather than data properties because both
are asserted from ROBOT templates, where the only working typed-literal directive (`AT prop^^type`)
emits an annotation assertion. Declaring them as data properties and then annotating with them would
pun, which is the same OWL 2 DL breakage the Makefile's `tmp/qualities.owl` rule exists to avoid.
`HTO:0000093 source statement` remains a data property: it is only ever emitted by rdflib from
instance data.
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_profiles_ontology.py`:

```python
"""The taste-profile layer's ontology terms: properties, vocabularies, interactions."""
import pathlib
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTO = "http://purl.obolibrary.org/obo/HTO_"


def graph():
    g = rdflib.Graph()
    g.parse(ROOT / "hto.owl", format="xml")
    return g


def term(local):
    return rdflib.URIRef(HTO + local)


# Expected rdflib/OWL types, as rdflib sees them in the parsed, serialised graph.
# NOTE: the ROBOT template keyword for a data property is `owl:DataProperty`
# (see properties.tsv's TYPE column); OWL serialises it as `owl:DatatypeProperty`,
# which is why this dict correctly reads OWL.DatatypeProperty for HTO:0000093
# below. Writing `owl:DatatypeProperty` in the TEMPLATE ITSELF is a different,
# silent bug: ROBOT does not recognise it as a keyword, CURIE-resolves it, and
# types the subject as a named individual of it instead - property/individual
# punning that OWL 2 DL does not permit, and that dropped the term from hto.obo.
NEW_PROPERTIES = {
    "0000080": ("has profile entry", OWL.ObjectProperty),
    "0000081": ("entry quality", OWL.ObjectProperty),
    "0000082": ("entry level", OWL.ObjectProperty),
    "0000083": ("entry phase", OWL.ObjectProperty),
    "0000084": ("holds for group", OWL.ObjectProperty),
    "0000085": ("elicited by tastant", OWL.ObjectProperty),
    "0000086": ("contains tastant", OWL.ObjectProperty),
    "0000087": ("interaction agent", OWL.ObjectProperty),
    "0000088": ("interaction target", OWL.ObjectProperty),
    "0000089": ("interaction effect", OWL.ObjectProperty),
    "0000090": ("demonstrated with", OWL.ObjectProperty),
    "0000091": ("explained by interaction", OWL.ObjectProperty),
    "0000092": ("level rank", OWL.AnnotationProperty),
    "0000093": ("source statement", OWL.DatatypeProperty),
    "0000094": ("has evidence type", OWL.ObjectProperty),
    "0000095": ("interaction condition", OWL.AnnotationProperty),
    "0000096": ("group defined by status", OWL.ObjectProperty),
    "0000097": ("group defined by diplotype", OWL.ObjectProperty),
}


def test_every_new_property_is_declared_with_the_right_type_and_label():
    g = graph()
    for local, (label, owl_type) in NEW_PROPERTIES.items():
        subject = term(local)
        assert (subject, RDF.type, owl_type) in g, f"{local} {label}: wrong or missing type"
        assert (subject, RDFS.label, rdflib.Literal(label)) in g, f"{local}: label mismatch"


def test_every_new_property_carries_a_definition():
    """missing_definition is an ERROR in src/report_profile.txt, so a property
    without IAO:0000115 fails the build, not just this test."""
    g = graph()
    definition = rdflib.URIRef("http://purl.obolibrary.org/obo/IAO_0000115")
    for local in NEW_PROPERTIES:
        assert (term(local), definition, None) in g, f"{local} has no definition"


def test_chemical_entity_is_imported():
    g = graph()
    assert (rdflib.URIRef("http://purl.obolibrary.org/obo/CHEBI_24431"), RDFS.label, None) in g
```

- [ ] **Step 3: Run the test and confirm it fails**

```bash
cd /gpfs/home2/csun/HTO && make build && python3 -m pytest tests/test_profiles_ontology.py -v
```

Expected: failures on the first two tests (properties not declared) and on `test_chemical_entity_is_imported`.

- [ ] **Step 4: Append the properties**

Append these rows to `src/templates/properties.tsv`. Columns, in order, are `ID`, `LABEL`, `TYPE`, `DOMAIN`, `RANGE`, `A IAO:0000115`, `A IAO:0000119`; separate with tabs; the last column is `HTO:0000000` on every row.

| ID | LABEL | TYPE | DOMAIN | RANGE | Definition |
|---|---|---|---|---|---|
| HTO:0000080 | has profile entry | owl:ObjectProperty | | HTO:0000400 | Relates a kind of food or drink to one line of its taste profile. |
| HTO:0000081 | entry quality | owl:ObjectProperty | HTO:0000400 | HTO:0000100 | Relates a taste profile entry to the perceptual taste quality it reports. |
| HTO:0000082 | entry level | owl:ObjectProperty | HTO:0000400 | HTO:0000200 | Relates a taste profile entry to the ordinal intensity level at which the quality is reported. |
| HTO:0000083 | entry phase | owl:ObjectProperty | HTO:0000400 | HTO:0000210 | Relates a taste profile entry to the phase of the tasting at which the quality is reported. |
| HTO:0000084 | holds for group | owl:ObjectProperty | HTO:0000400 | HTO:0000220 | Relates a taste profile entry to the group of tasters for whom it is asserted to hold. |
| HTO:0000085 | elicited by tastant | owl:ObjectProperty | HTO:0000100 | CHEBI:24431 | Relates a perceptual taste quality to a chemical entity whose presence elicits it. |
| HTO:0000086 | contains tastant | owl:ObjectProperty | | CHEBI:24431 | Relates a kind of food or drink to a chemical entity it contains that is capable of eliciting a taste quality. |
| HTO:0000087 | interaction agent | owl:ObjectProperty | HTO:0000410 | HTO:0000100 | Relates a taste interaction to the quality whose presence produces the effect. |
| HTO:0000088 | interaction target | owl:ObjectProperty | HTO:0000410 | HTO:0000100 | Relates a taste interaction to the quality whose perceived intensity is altered. |
| HTO:0000089 | interaction effect | owl:ObjectProperty | HTO:0000410 | HTO:0000230 | Relates a taste interaction to the direction of the effect the agent has on the target. |
| HTO:0000090 | demonstrated with | owl:ObjectProperty | HTO:0000410 | CHEBI:24431 | Relates a taste interaction to a chemical entity used as a stimulus in the study that established it. |
| HTO:0000091 | explained by interaction | owl:ObjectProperty | HTO:0000400 | HTO:0000410 | Relates a taste profile entry to a taste interaction that accounts for the level reported. |
| HTO:0000092 | level rank | owl:AnnotationProperty | | | The position of an ordinal intensity level in the ordering from absent to intense, as an integer from zero to four. |
| HTO:0000093 | source statement | owl:DataProperty | HTO:0000400 | | The free-text statement of where a taste profile entry's claim comes from. |
| HTO:0000094 | has evidence type | owl:ObjectProperty | HTO:0000400 | HTO:0000240 | Relates a taste profile entry to the kind of evidence its claim rests on. |
| HTO:0000095 | interaction condition | owl:AnnotationProperty | | | The concentrations, matched intensities or reversals under which a taste interaction was observed. |
| HTO:0000096 | group defined by status | owl:ObjectProperty | HTO:0000223 | HTO:0000011 | Relates a phenotype-defined taster group to the taster status that defines its membership. |
| HTO:0000097 | group defined by diplotype | owl:ObjectProperty | HTO:0000222 | HTO:0000015 | Relates a genotype-defined taster group to the diplotype that defines its membership. |

`HTO:0000080` and `HTO:0000086` have a deliberately **empty domain**: their subject is a kind of food or drink, which is a FoodOn class and not an HTO class, and asserting a domain HTO does not own would make every annotated food an instance of an HTO class it never claimed to be.

- [ ] **Step 5: Add the one new import**

Append to `src/external_terms.tsv` (columns: CURIE, ontology, note):

```
CHEBI:24431	chebi	chemical entity, range for 'elicited by tastant' and 'contains tastant'
```

Then rebuild the import module:

```bash
cd /gpfs/home2/csun/HTO && python3 scripts/build_imports.py
```

Expected: reports 57 terms resolved, zero failures. If OLS4 is unreachable the task stops here and is reported as blocked — do not hand-write the module.

- [ ] **Step 6: Run the tests and the build**

```bash
cd /gpfs/home2/csun/HTO && make build && make report && python3 -m pytest tests/ -q
```

Expected: `robot report` "No violations found", `test_profiles_ontology.py` passing, all pre-existing tests still passing. `tests/test_imports.py` asserts a term count — if it hard-codes 56, update it to 57 and say so in the commit message.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: properties for the taste profile layer, and the CHEBI chemical-entity import

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Slot vocabularies and the two reified classes

**Files:**
- Create: `src/templates/profiles.tsv`
- Modify: `Makefile` (one new explicit rule)
- Modify: `tests/test_profiles_ontology.py`

**Interfaces:**
- Consumes: `HTO:0000092`, `HTO:0000096`, `HTO:0000097` from Task 1.
- Produces: classes `HTO:0000200`, `0000210`, `0000220`, `0000222`, `0000223`, `0000230`, `0000240`, `0000400`, `0000410`, and the individuals listed below. Tasks 5 and 7 match on these IRIs and on these labels, lowercased.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_profiles_ontology.py`:

```python
VOCABULARY = {
    "0000200": ["0000201", "0000202", "0000203", "0000204", "0000205"],
    "0000210": ["0000211", "0000212", "0000213", "0000214"],
    "0000230": ["0000231", "0000232"],
    "0000240": ["0000241", "0000242", "0000243", "0000244"],
}
RANKS = {"0000201": 0, "0000202": 1, "0000203": 2, "0000204": 3, "0000205": 4}


def test_slot_vocabularies_contain_exactly_the_enumerated_members():
    """Closed lists. A member appearing that the converter does not know about
    would be accepted by the ontology and rejected by the sheet, silently."""
    g = graph()
    for parent, members in VOCABULARY.items():
        found = {str(s).replace(HTO, "") for s in g.subjects(RDF.type, term(parent))}
        assert found == set(members), f"{parent}: expected {members}, found {sorted(found)}"


def test_intensity_levels_are_ranked_zero_to_four():
    g = graph()
    rank = term("0000092")
    for local, expected in RANKS.items():
        values = [int(o) for o in g.objects(term(local), rank)]
        assert values == [expected], f"{local}: rank {values}, expected [{expected}]"


def test_taster_groups_point_back_at_the_v1_core():
    """A group is not a new parallel vocabulary: genotype groups name an
    HTO:0000015 diplotype, phenotype groups name an HTO:0000011 taster status."""
    g = graph()
    by_diplotype, by_status = term("0000097"), term("0000096")
    assert (term("0000224"), by_diplotype, None) in g
    assert (term("0000226"), by_diplotype, None) in g
    assert (term("0000227"), by_status, term("0000012")) in g
    assert (term("0000229"), by_status, term("0000014")) in g


def test_the_two_reified_classes_exist():
    g = graph()
    for local in ("0000400", "0000410"):
        assert (term(local), RDF.type, OWL.Class) in g
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /gpfs/home2/csun/HTO && python3 -m pytest tests/test_profiles_ontology.py -v
```

Expected: the four new tests fail; Task 1's tests still pass.

- [ ] **Step 3: Create `src/templates/profiles.tsv`**

Two identical header rows except where a template string differs. Columns: `ID`, `LABEL`, `TYPE`, `SC %`, `I HTO:0000096`, `I HTO:0000097`, `AT HTO:0000092^^xsd:integer`, `A IAO:0000115`, `A IAO:0000119`.

Row 1 (human header): `ID  LABEL  TYPE  SC %  group defined by status  group defined by diplotype  level rank  definition  definition source`
Row 2 (template strings): `ID  LABEL  TYPE  SC %  I HTO:0000096  I HTO:0000097  AT HTO:0000092^^xsd:integer  A IAO:0000115  A IAO:0000119`

Classes first (`TYPE` = `owl:Class`, `SC %` giving the parent where there is one):

| ID | LABEL | SC % | Definition |
|---|---|---|---|
| HTO:0000200 | taste intensity level | | An ordinal degree at which a perceptual taste quality is reported to be present in a kind of food or drink. |
| HTO:0000210 | tasting phase | | A stage of a single tasting, from the first contact of the sample with the tongue to the sensation remaining after swallowing. |
| HTO:0000220 | taster group | | A group of human tasters sharing a characteristic relevant to how they perceive taste. |
| HTO:0000222 | genotype-defined taster group | HTO:0000220 | A taster group whose membership is defined by a genotype at a taste receptor locus. |
| HTO:0000223 | phenotype-defined taster group | HTO:0000220 | A taster group whose membership is defined by a measured taste phenotype rather than by genotype. |
| HTO:0000230 | taste interaction effect | | The direction in which one perceptual taste quality alters the perceived intensity of another. |
| HTO:0000240 | evidence type | | The kind of evidence on which a taste profile entry's claim rests. |
| HTO:0000400 | taste profile entry | | One line of the taste profile of a kind of food or drink: a single quality, at a single ordinal level, at a single phase of the tasting, holding for a single group of tasters, from a single source. |
| HTO:0000410 | taste interaction | | An asserted relation in which the presence of one perceptual taste quality alters the perceived intensity of another, as established by a cited study using named chemical stimuli. |

Then individuals (`TYPE` = the parent class CURIE, `SC %` empty):

| ID | LABEL | TYPE | rank | Definition |
|---|---|---|---|---|
| HTO:0000201 | absent | HTO:0000200 | 0 | The intensity level at which a quality is reported not to be perceptible at all. |
| HTO:0000202 | slight | HTO:0000200 | 1 | The intensity level at which a quality is reported as just perceptible. |
| HTO:0000203 | moderate | HTO:0000200 | 2 | The intensity level at which a quality is reported as clearly present without dominating. |
| HTO:0000204 | strong | HTO:0000200 | 3 | The intensity level at which a quality is reported as dominating the taste. |
| HTO:0000205 | intense | HTO:0000200 | 4 | The intensity level at which a quality is reported as close to the strongest the taster can imagine. |
| HTO:0000211 | attack | HTO:0000210 | | The phase of a tasting from first contact of the sample with the tongue to the first clear perception. |
| HTO:0000212 | mid-palate | HTO:0000210 | | The phase of a tasting while the sample is held in the mouth, after the first perception and before swallowing or expectoration. |
| HTO:0000213 | finish | HTO:0000210 | | The phase of a tasting after the sample leaves the mouth, in which remaining and newly emerging sensations are perceived. |
| HTO:0000214 | overall | HTO:0000210 | | The whole of a tasting taken together, used when a report does not distinguish phases. |
| HTO:0000221 | general population | HTO:0000220 | | The taster group comprising human tasters generally, used when a claim is not qualified by genotype or phenotype. |
| HTO:0000231 | suppression | HTO:0000230 | | The effect in which the presence of the agent quality lowers the perceived intensity of the target quality. |
| HTO:0000232 | enhancement | HTO:0000230 | | The effect in which the presence of the agent quality raises the perceived intensity of the target quality. |
| HTO:0000241 | literature | HTO:0000240 | | Evidence consisting of a published study identified by a persistent identifier. |
| HTO:0000242 | panel data | HTO:0000240 | | Evidence consisting of ratings collected from a trained or untrained sensory panel. |
| HTO:0000243 | expert assertion | HTO:0000240 | | Evidence consisting of the judgement of a person with domain expertise, unaccompanied by data. |
| HTO:0000244 | personal tasting | HTO:0000240 | | Evidence consisting of one person's own tasting, recorded without a panel or a published source. |

Then the six seeded groups, which use the `I` columns:

| ID | LABEL | TYPE | I HTO:0000096 | I HTO:0000097 | Definition |
|---|---|---|---|---|---|
| HTO:0000224 | TAS2R38 PAV/PAV taster group | HTO:0000222 | | HTO:0000015 | The genotype-defined taster group whose members carry the PAV haplotype of TAS2R38 on both chromosomes. |
| HTO:0000225 | TAS2R38 PAV/AVI taster group | HTO:0000222 | | HTO:0000015 | The genotype-defined taster group whose members carry one PAV and one AVI haplotype of TAS2R38. |
| HTO:0000226 | TAS2R38 AVI/AVI taster group | HTO:0000222 | | HTO:0000015 | The genotype-defined taster group whose members carry the AVI haplotype of TAS2R38 on both chromosomes. |
| HTO:0000227 | PROP non-taster group | HTO:0000223 | HTO:0000012 | | The phenotype-defined taster group whose members report no bitterness from a propylthiouracil filter-paper strip. |
| HTO:0000228 | PROP medium-taster group | HTO:0000223 | HTO:0000013 | | The phenotype-defined taster group whose members report moderate bitterness from a propylthiouracil filter-paper strip. |
| HTO:0000229 | PROP super-taster group | HTO:0000223 | HTO:0000014 | | The phenotype-defined taster group whose members report intense bitterness from a propylthiouracil filter-paper strip. |

`HTO:0000015 TAS2R38 diplotype` is a class in v1, so `I HTO:0000097` pointing at it is an assertion about a class IRI. That is intentional and matches how the seeded groups name a diplotype *kind*; it does not create an individual.

- [ ] **Step 4: Add the Makefile rule**

`src/templates/profiles.tsv` references properties declared in `properties.tsv` (`HTO:0000092`, `0000096`, `0000097`). Built in isolation, ROBOT emits bare declarations for them and the merge pollutes the release — the identical problem the existing `tmp/qualities.owl` rule documents. Insert immediately after that rule in `Makefile`:

```make
# profiles.tsv asserts I HTO:0000096 / I HTO:0000097 and AT HTO:0000092 on named
# individuals. As with qualities.tsv, templating it in isolation leaves ROBOT
# guessing at those properties' types; passing the built properties module as
# --input supplies them. None of its axioms are copied into the output.
tmp/profiles.owl: src/templates/profiles.tsv tmp/properties.owl | tmp
	$(ROBOT) template --input tmp/properties.owl --template $< $(PREFIX) --output $@
```

No change to `TEMPLATES` or `MODULES` is needed: both are wildcards over `src/templates/*.tsv`, so the new file is picked up automatically and this explicit rule takes precedence over the pattern rule.

- [ ] **Step 5: Build and run the tests**

```bash
cd /gpfs/home2/csun/HTO && make build && make report && python3 -m pytest tests/ -q
```

Expected: 0 ERROR from `robot report`, all tests green. If `report` flags `missing_definition` on an individual, that individual's `A IAO:0000115` cell is empty — fill it, do not weaken the profile.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: taste profile entry, taste interaction, and the four slot vocabularies

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: The quality→tastant mechanism layer

**Files:**
- Modify: `src/templates/qualities.tsv` (one new column, eight populated cells, two comments)
- Modify: `tests/test_profiles_ontology.py`

**Interfaces:**
- Consumes: `HTO:0000085 elicited by tastant` from Task 1.
- Produces: eight `SubClassOf(quality, elicited_by some <CHEBI term>)` axioms that cq13 in Task 7 queries.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_profiles_ontology.py`:

```python
ELICITATION = {
    "0000111": "CHEBI_17992",  # sweetness      <- sucrose
    "0000112": "CHEBI_30769",  # sourness       <- citric acid
    "0000113": "CHEBI_26710",  # saltiness      <- sodium chloride
    "0000115": "CHEBI_16015",  # umami          <- L-glutamic acid
    "0000131": "CHEBI_8502",   # thiourea bitterness  <- PROP
    "0000132": "CHEBI_16226",  # limonoid bitterness  <- limonin
    "0000133": "CHEBI_28819",  # flavanone bitterness <- naringin
    "0000134": "CHEBI_27732",  # alkaloid bitterness  <- caffeine
}


def test_qualities_are_linked_to_the_tastants_that_elicit_them():
    """Each link is an existential restriction, not an annotation: cq13 walks it
    to find foods containing a tastant whose quality nobody has annotated."""
    g = graph()
    elicited_by = term("0000085")
    for quality, chebi in ELICITATION.items():
        found = False
        for restriction in g.objects(term(quality), RDFS.subClassOf):
            if (restriction, OWL.onProperty, elicited_by) in g and (
                restriction,
                OWL.someValuesFrom,
                rdflib.URIRef("http://purl.obolibrary.org/obo/" + chebi),
            ) in g:
                found = True
        assert found, f"HTO:{quality} is not linked to {chebi}"


def test_the_two_precoordinated_temporal_terms_name_their_preferred_form():
    g = graph()
    for local in ("0000153", "0000154"):
        comments = " ".join(str(c) for c in g.objects(term(local), RDFS.comment))
        assert "finish" in comments.lower(), f"HTO:{local} does not name the preferred form"
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /gpfs/home2/csun/HTO && python3 -m pytest tests/test_profiles_ontology.py -v -k "elicit or precoordinated"
```

Expected: both fail.

- [ ] **Step 3: Add the column and the eight links**

In `src/templates/qualities.tsv`, insert a new column immediately after the existing `SC HTO:0000061 some %` column. Header row 1: `SC HTO:0000085 some %`. Header row 2: `SC HTO:0000085 some %`. Every existing row gains one empty cell at that position — check with `awk -F'\t' '{print NF}' src/templates/qualities.tsv | sort -u`, which must print a single number.

Populate exactly the eight cells in the `ELICITATION` map above, and no others. `HTO:0000114 bitterness` itself gets **no** link: bitterness in general is not elicited by any one compound, and asserting `bitterness elicited_by some quinine` would be a weaker and misleading claim than the subtype links.

- [ ] **Step 4: Demote the two pre-coordinated terms**

In the existing `A rdfs:comment` column, set for `HTO:0000153 lingering bitterness`:

> Prefer the post-coordinated form for new data: a taste profile entry with entry quality bitterness and entry phase finish. This term is retained for continuity and is accepted by scripts/profile2rdf.py, which normalises it to that form.

and for `HTO:0000154 delayed bitterness`:

> Prefer the post-coordinated form for new data: a taste profile entry with entry quality bitterness and entry phase finish. This term is retained for continuity — the published walkthrough cites it — and is accepted by scripts/profile2rdf.py, which normalises it to that form.

If either row already has a comment, append as a second sentence rather than overwriting it.

- [ ] **Step 5: Build, test, commit**

```bash
cd /gpfs/home2/csun/HTO && make build && make report && python3 -m pytest tests/ -q
git add -A
git commit -m "feat: link taste qualities to the tastants that elicit them

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: The interaction rules

This is the research task. Its deliverable is a table of claims that are **true and cited**, not a table of a particular length.

**Files:**
- Create: `src/templates/interactions.tsv`
- Create: `scripts/interactions_md.py`
- Create: `docs/interactions.md` (generated)
- Create: `scripts/verify_citations.py`
- Modify: `Makefile` (`verify-citations` target)
- Modify: `tests/test_profiles_ontology.py`

**Interfaces:**
- Consumes: `HTO:0000410` and `HTO:0000231`/`0000232` from Task 2; properties `0000087`–`0000090`, `0000095` from Task 1.
- Produces: interaction individuals from `HTO:0000411` upward. Task 5's validation rule V7 reads `src/templates/interactions.tsv` directly for its ID→target map, so the column names below are an interface, not an implementation detail.

- [ ] **Step 1: Verify candidate claims before writing any of them down**

For each candidate — sucrose suppressing quinine bitterness; sodium chloride suppressing bitterness; sucrose and citric acid suppressing each other; sodium chloride enhancing sweetness at low concentration; glutamate enhancing saltiness; astringency accumulating over repeated sips — run:

```bash
esearch -db pubmed -query "<claim terms> taste mixture suppression" | efetch -format docsum | head -40
```

If `esearch` is unavailable, use the E-utilities HTTP API directly:

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term=<urlencoded+query>"
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=<pmid>"
```

Acceptance for a rule, all four required:

1. The PMID resolves and its title and abstract are actually about taste mixture interaction.
2. The paper names **both** compounds that go in `demonstrated_with`.
3. The direction matches: the paper reports the agent lowering (or raising) the target's perceived intensity, not merely co-occurring with it.
4. The conditions under which it holds are stated well enough to fill the `condition` cell.

Record every candidate you rejected and why in a scratch note; Step 7 puts it in `docs/findings.md`. **A candidate you cannot verify is dropped, not softened.** Do not pad the table to reach a count; the spec explicitly promises none.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_profiles_ontology.py`:

```python
import csv

INTERACTIONS_TSV = ROOT / "src" / "templates" / "interactions.tsv"


def interaction_rows():
    with open(INTERACTIONS_TSV) as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    return rows[1:]  # row 0 is ROBOT's template-string row


def test_at_least_one_interaction_rule_ships():
    assert interaction_rows(), "no interaction rules: the layer's contribution is empty"


def test_every_interaction_row_is_complete():
    """A rule missing its compound pair or its citation is an unsupported claim.
    Every psychophysics result is about sucrose versus quinine, not sweet versus
    bitter, so demonstrated_with is mandatory."""
    for row in interaction_rows():
        rule = row["ID"]
        for column in ("LABEL", "agent", "target", "effect", "demonstrated_with",
                       "condition", "citation"):
            assert (row.get(column) or "").strip(), f"{rule}: {column} is empty"
        assert row["effect"] in ("HTO:0000231", "HTO:0000232"), f"{rule}: bad effect"
        assert len([c for c in row["demonstrated_with"].split("|") if c.strip()]) >= 2, \
            f"{rule}: demonstrated_with needs at least two compounds"
        assert row["citation"].startswith(("PMID:", "doi:")), f"{rule}: unsourced"


def test_interaction_individuals_reach_the_release():
    g = graph()
    built = set(g.subjects(RDF.type, term("0000410")))
    assert len(built) == len(interaction_rows())
```

- [ ] **Step 3: Run it and confirm it fails**

```bash
cd /gpfs/home2/csun/HTO && python3 -m pytest tests/test_profiles_ontology.py -v -k interaction
```

Expected: all three fail — the file does not exist.

- [ ] **Step 4: Create `src/templates/interactions.tsv`**

Row 1 (human header):

```
ID	LABEL	TYPE	agent	target	effect	demonstrated_with	condition	citation	A IAO:0000115	A IAO:0000119
```

Row 2 (template strings):

```
ID	LABEL	TYPE	I HTO:0000087	I HTO:0000088	I HTO:0000089	I HTO:0000090 SPLIT=|	A HTO:0000095	A IAO:0000119	A IAO:0000115	A IAO:0000119
```

Note `SPLIT=|` on `demonstrated_with`: ROBOT splits that cell on `|` into one assertion per compound, which is how a rule names both stimuli. The `citation` and the definition-source column both write `A IAO:0000119`; that is intended — the citation *is* the definition source for an interaction, and ROBOT merges both into the same annotation property.

One row per verified rule, IDs from `HTO:0000411` upward, `TYPE` = `HTO:0000410`. Worked example of the intended shape, to be replaced by whatever Step 1 actually verified:

```
HTO:0000411	sweetness suppresses bitterness	HTO:0000410	HTO:0000111	HTO:0000114	HTO:0000231	CHEBI:17992|CHEBI:15854	<conditions from the paper>	PMID:<verified>	Interaction in which the presence of sweetness lowers the perceived intensity of bitterness.	HTO:0000000
```

Rules are directional: if the reverse direction is also verified, it is a second row with its own ID, not a symmetric reading of this one.

- [ ] **Step 5: Write the generator and the verifier**

Create `scripts/interactions_md.py`:

```python
#!/usr/bin/env python3
"""Render src/templates/interactions.tsv as a readable table in docs/interactions.md.

The interaction rules are the ontology's contribution; requiring SPARQL to read
them would hide them from everyone who is not already an ontologist.
"""
from __future__ import annotations
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TSV = ROOT / "src" / "templates" / "interactions.tsv"
OUT = ROOT / "docs" / "interactions.md"

LABELS = {}  # CURIE -> label, filled from the quality and vocabulary templates


def load_labels() -> None:
    for name in ("qualities.tsv", "profiles.tsv"):
        path = ROOT / "src" / "templates" / name
        if not path.exists():
            continue
        with open(path) as fh:
            for row in list(csv.DictReader(fh, delimiter="\t"))[1:]:
                LABELS[row["ID"]] = row["LABEL"]


def main() -> int:
    load_labels()
    with open(TSV) as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))[1:]
    lines = [
        "# Taste interactions",
        "",
        "Generated by `scripts/interactions_md.py` from `src/templates/interactions.tsv`.",
        "Every rule is directional, names the compounds it was demonstrated with, and",
        "carries a citation verified against PubMed.",
        "",
        "| Rule | Agent | Effect | Target | Demonstrated with | Condition | Citation |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        effect = "suppresses" if row["effect"] == "HTO:0000231" else "enhances"
        compounds = ", ".join(LABELS.get(c, c) for c in row["demonstrated_with"].split("|"))
        lines.append(
            f"| `{row['ID']}` | {LABELS.get(row['agent'], row['agent'])} | {effect} "
            f"| {LABELS.get(row['target'], row['target'])} | {compounds} "
            f"| {row['condition']} | {row['citation']} |"
        )
    lines.append("")
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}: {len(rows)} rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `scripts/verify_citations.py`:

```python
#!/usr/bin/env python3
"""Resolve every PMID in the templates and the profile data against PubMed.

Ten of the eleven citations proposed during the v1 build were fabricated: real
identifiers pointing at unrelated papers (docs/findings.md section 4). This
script exists so that failure mode is caught by a command rather than by a
reader. It touches the network and is therefore excluded from `make test`.
"""
from __future__ import annotations
import json, pathlib, re, sys, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PMID = re.compile(r"PMID:(\d+)")
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def sources() -> list[pathlib.Path]:
    return sorted(
        list((ROOT / "src" / "templates").glob("*.tsv"))
        + list((ROOT / "data" / "raw").glob("*.csv"))
    )


def main() -> int:
    found: dict[str, list[str]] = {}
    for path in sources():
        for pmid in PMID.findall(path.read_text()):
            found.setdefault(pmid, []).append(path.name)
    if not found:
        print("no PMIDs found")
        return 0
    query = urllib.parse.urlencode({"db": "pubmed", "retmode": "json",
                                    "id": ",".join(sorted(found))})
    with urllib.request.urlopen(f"{ESUMMARY}?{query}", timeout=30) as response:
        payload = json.load(response)
    result = payload.get("result", {})
    failures = 0
    for pmid in sorted(found):
        record = result.get(pmid)
        if not record or record.get("error"):
            print(f"UNRESOLVED  PMID:{pmid}  cited in {', '.join(found[pmid])}")
            failures += 1
            continue
        print(f"OK          PMID:{pmid}  {record.get('title', '')[:90]}")
        print(f"                        cited in {', '.join(found[pmid])}")
    print(f"\n{failures} unresolved of {len(found)}")
    print("Resolution is necessary, not sufficient: read each title above and "
          "confirm it supports the claim that cites it.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to `Makefile`, and add both targets to the `.PHONY` line:

```make
interactions-doc:
	python3 scripts/interactions_md.py

verify-citations:
	python3 scripts/verify_citations.py
```

- [ ] **Step 6: Build, generate, verify, test**

```bash
cd /gpfs/home2/csun/HTO && make build && make report && make interactions-doc && make verify-citations && python3 -m pytest tests/ -q
```

Expected: `robot report` clean, every PMID resolving, all tests green. A PMID reported `UNRESOLVED` means that rule is fabricated — delete the row, do not substitute a different identifier for the same claim without re-running Step 1's acceptance check.

- [ ] **Step 7: Record the rejected candidates**

Add a short subsection to `docs/findings.md` listing each candidate interaction that did not survive Step 1 and the reason. This is the part of the work a reader cannot reconstruct, and it stops the next person re-proposing the same unsupported rule.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: verified taste interaction rules, with the generated table and citation verifier

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: The profile converter

**Files:**
- Create: `scripts/profile2rdf.py`
- Create: `tests/test_profile2rdf.py`

**Interfaces:**
- Consumes: the vocabularies from Task 2 (by label, lowercased), the qualities template, and `src/templates/interactions.tsv` from Task 4.
- Produces: `convert(profiles_csv, out_path, tastants_csv=None) -> int` raising `ProfileError`; CLI `python3 scripts/profile2rdf.py <profiles.csv> <out.ttl> [--tastants <t.csv>] [--gap-report <path>]`. Task 6 supplies its data, Task 7 queries its output.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile2rdf.py`:

```python
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
```

- [ ] **Step 2: Run them and confirm they fail**

```bash
cd /gpfs/home2/csun/HTO && python3 -m pytest tests/test_profile2rdf.py -v
```

Expected: every test fails — the script does not exist.

- [ ] **Step 3: Write `scripts/profile2rdf.py`**

```python
#!/usr/bin/env python3
"""Convert a taste profile CSV into RDF instance data typed by HTO.

Each row becomes one HTO:0000400 taste profile entry: a single quality, at a
single ordinal level, at a single phase, holding for a single taster group,
from a single named source. Two rows differing only in taster group are how a
food that tastes different to different people is written down.

Vocabularies are resolved from the templates rather than from the built
ontology, so the converter runs without Java and without a build.
"""
from __future__ import annotations
import argparse, csv, pathlib, re, sys
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

ROOT = pathlib.Path(__file__).resolve().parent.parent
OBO = Namespace("http://purl.obolibrary.org/obo/")
EX = Namespace("https://w3id.org/hto/data/")

LEVELS = {"absent": "0000201", "slight": "0000202", "moderate": "0000203",
          "strong": "0000204", "intense": "0000205"}
PHASES = {"attack": "0000211", "mid-palate": "0000212", "finish": "0000213",
          "overall": "0000214"}
GROUPS = {"general population": "0000221",
          "tas2r38 pav/pav": "0000224", "tas2r38 pav/avi": "0000225",
          "tas2r38 avi/avi": "0000226", "prop non-taster": "0000227",
          "prop medium-taster": "0000228", "prop super-taster": "0000229"}
EVIDENCE = {"literature": "0000241", "panel data": "0000242",
            "expert assertion": "0000243", "personal tasting": "0000244"}

# Accepted for continuity, rewritten to the post-coordinated form. See the
# rdfs:comment on each term in src/templates/qualities.tsv.
PRECOORDINATED = {"lingering bitterness": ("0000114", "finish"),
                  "delayed bitterness": ("0000114", "finish")}

PMID_RE = re.compile(r"^PMID:\d+$")
DOI_RE = re.compile(r"^doi:10\.\d{4,9}/\S+$", re.IGNORECASE)
FOODON_RE = re.compile(r"^FOODON:\d+$")
CHEBI_RE = re.compile(r"^CHEBI:\d+$")

COLUMNS = ("food_id", "food_label", "quality", "level", "phase", "taster_group",
           "source_type", "source", "explained_by")


class ProfileError(Exception):
    pass


def hto(local: str) -> URIRef:
    return OBO[f"HTO_{local}"]


def curie_to_iri(curie: str) -> URIRef:
    prefix, local = curie.split(":", 1)
    return OBO[f"{prefix}_{local}"]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def template_rows(name: str) -> list[dict]:
    path = ROOT / "src" / "templates" / name
    if not path.exists():
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))[1:]


def load_qualities() -> dict[str, str]:
    """label (lowercased) and CURIE -> local id, for every HTO quality."""
    index: dict[str, str] = {}
    for row in template_rows("qualities.tsv"):
        local = row["ID"].split(":", 1)[1]
        index[row["LABEL"].strip().lower()] = local
        index[row["ID"].strip()] = local
    return index


def load_interactions() -> dict[str, str]:
    """interaction CURIE -> its target quality CURIE, for rule V7."""
    return {row["ID"].strip(): (row.get("target") or "").strip()
            for row in template_rows("interactions.tsv")}


def convert(profiles_csv: pathlib.Path, out_path: pathlib.Path,
            tastants_csv: pathlib.Path | None = None,
            gap_report: pathlib.Path | None = None) -> int:
    qualities, interactions = load_qualities(), load_interactions()
    errors: list[str] = []
    graph = Graph()
    graph.bind("hto", OBO)
    graph.bind("ex", EX)
    seen: set[tuple] = set()
    unmapped: dict[str, str] = {}
    written = 0

    def food_node(row: dict, line: int) -> URIRef | None:
        label = (row.get("food_label") or "").strip()
        if not label:
            errors.append(f"line {line}: food_label is empty")
            return None
        food_id = (row.get("food_id") or "").strip()
        if food_id:
            if not FOODON_RE.match(food_id):
                errors.append(f"line {line}: food_id {food_id!r} is not a FOODON CURIE")
                return None
            return curie_to_iri(food_id)
        unmapped[slug(label)] = label
        return EX[f"food/{slug(label)}"]

    with open(profiles_csv) as fh:
        reader = csv.DictReader(l for l in fh if not l.lstrip().startswith("#"))
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or ())]
        if missing:
            raise ProfileError(f"{profiles_csv}: missing column(s): {', '.join(missing)}")

        for line, row in enumerate(reader, start=2):
            food = food_node(row, line)

            raw_quality = (row.get("quality") or "").strip()
            phase_text = (row.get("phase") or "").strip().lower() or "overall"
            key = raw_quality.lower()
            if key in PRECOORDINATED:
                quality_local, phase_text = PRECOORDINATED[key]
            else:
                quality_local = qualities.get(key) or qualities.get(raw_quality)
                if quality_local is None:
                    errors.append(f"line {line}: quality {raw_quality!r} is not an HTO quality")

            level_local = LEVELS.get((row.get("level") or "").strip().lower())
            if level_local is None:
                errors.append(f"line {line}: level {row.get('level')!r} is not one of "
                              f"{', '.join(LEVELS)}")
            phase_local = PHASES.get(phase_text)
            if phase_local is None:
                errors.append(f"line {line}: phase {phase_text!r} is not one of "
                              f"{', '.join(PHASES)}")
            group_text = (row.get("taster_group") or "").strip().lower() or "general population"
            group_local = GROUPS.get(group_text)
            if group_local is None:
                errors.append(f"line {line}: taster_group {group_text!r} is not one of "
                              f"{', '.join(GROUPS)}")

            evidence_text = (row.get("source_type") or "").strip().lower()
            evidence_local = EVIDENCE.get(evidence_text)
            if evidence_local is None:
                errors.append(f"line {line}: source_type {evidence_text!r} is not one of "
                              f"{', '.join(EVIDENCE)}")
            source = (row.get("source") or "").strip()
            if not source:
                errors.append(f"line {line}: source is empty; every claim names where it came from")
            elif evidence_text == "literature" and not (PMID_RE.match(source)
                                                        or DOI_RE.match(source)):
                errors.append(f"line {line}: source {source!r} claims to be literature but is "
                              f"neither a PMID: nor a doi:")

            interaction = (row.get("explained_by") or "").strip()
            if interaction:
                if interaction not in interactions:
                    errors.append(f"line {line}: explained_by {interaction} is not a known "
                                  f"interaction")
                elif quality_local and interactions[interaction] != f"HTO:{quality_local}":
                    errors.append(f"line {line}: explained_by {interaction} targets "
                                  f"{interactions[interaction]}, not this row's quality "
                                  f"HTO:{quality_local}")

            if None in (food, quality_local, level_local, phase_local, group_local,
                        evidence_local):
                continue

            identity = (str(food), quality_local, phase_local, group_local)
            if identity in seen:
                errors.append(f"line {line}: duplicate entry for the same food, quality, phase "
                              f"and taster group; two levels for one claim is a contradiction")
                continue
            seen.add(identity)

            entry = EX[f"profile/{slug(row['food_label'])}/{quality_local}/"
                       f"{phase_local}/{group_local}"]
            graph.add((food, RDFS.label, Literal(row["food_label"].strip())))
            graph.add((food, hto("0000080"), entry))
            graph.add((entry, RDF.type, hto("0000400")))
            graph.add((entry, hto("0000081"), hto(quality_local)))
            graph.add((entry, hto("0000082"), hto(level_local)))
            graph.add((entry, hto("0000083"), hto(phase_local)))
            graph.add((entry, hto("0000084"), hto(group_local)))
            graph.add((entry, hto("0000093"), Literal(source)))
            graph.add((entry, hto("0000094"), hto(evidence_local)))
            if interaction:
                graph.add((entry, hto("0000091"), curie_to_iri(interaction)))
            written += 1

    if tastants_csv is not None:
        with open(tastants_csv) as fh:
            reader = csv.DictReader(l for l in fh if not l.lstrip().startswith("#"))
            for line, row in enumerate(reader, start=2):
                food = food_node(row, line)
                tastant = (row.get("tastant") or "").strip()
                if not CHEBI_RE.match(tastant):
                    errors.append(f"{tastants_csv.name} line {line}: tastant {tastant!r} "
                                  f"is not a CHEBI CURIE")
                    continue
                if not (row.get("source") or "").strip():
                    errors.append(f"{tastants_csv.name} line {line}: source is empty")
                    continue
                if food is None:
                    continue
                graph.add((food, RDFS.label, Literal(row["food_label"].strip())))
                graph.add((food, hto("0000086"), curie_to_iri(tastant)))

    if errors:
        raise ProfileError("\n".join(errors))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=out_path, format="turtle")

    if gap_report is not None:
        lines = ["# Foods with no FoodOn term", "",
                 "Generated by `scripts/profile2rdf.py`. Each food below is described in HTO",
                 "but has no FoodOn identifier, so it carries a local IRI and cannot yet be",
                 "joined against the wider food ecosystem. These are candidates for a FoodOn",
                 "new-term request; see `docs/term-requests/`.", ""]
        lines += [f"- {label} (`{key}`)" for key, label in sorted(unmapped.items())] or \
                 ["_None: every food carries a FoodOn identifier._"]
        gap_report.parent.mkdir(parents=True, exist_ok=True)
        gap_report.write_text("\n".join(lines) + "\n")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles_csv", type=pathlib.Path)
    parser.add_argument("out_path", type=pathlib.Path)
    parser.add_argument("--tastants", type=pathlib.Path, default=None)
    parser.add_argument("--gap-report", type=pathlib.Path,
                        default=ROOT / "docs" / "needs-foodon.md")
    args = parser.parse_args()
    try:
        n = convert(args.profiles_csv, args.out_path, args.tastants, args.gap_report)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out_path}: {n} profile entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests**

```bash
cd /gpfs/home2/csun/HTO && python3 -m pytest tests/test_profile2rdf.py -v
```

Expected: all pass. `test_bad_rows_are_rejected_with_a_useful_message` is the important one — if any parametrised case returns 0, a validation rule is missing, and the fix is in the converter, never in the test.

- [ ] **Step 5: Commit**

```bash
git add scripts/profile2rdf.py tests/test_profile2rdf.py
git commit -m "feat: taste profile CSV to RDF converter, with nine validation rules

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: The sheet template and the seed data

**Files:**
- Create: `data/profile_sheet.csv`, `data/raw/example_profiles.csv`, `data/raw/example_food_tastants.csv`
- Create: `docs/needs-foodon.md` (generated)
- Modify: `Makefile` (`profiles` target, and `validate` to call it)

**Interfaces:**
- Consumes: `scripts/profile2rdf.py` from Task 5.
- Produces: `data/rdf/profiles.ttl`, which Task 7's queries run against.

- [ ] **Step 1: Create the blank sheet**

`data/profile_sheet.csv` — `#` comment lines are skipped by the converter, so the guidance travels with the sheet:

```csv
# HTO taste profile sheet. One row per quality you want to record about one food or drink.
# food_id      a FoodOn CURIE such as FOODON:03301710; leave blank if you do not know one
# food_label   what the thing is called, e.g. "iyokan juice"
# quality      an HTO quality: sweetness, sourness, saltiness, bitterness, umami,
#              astringency, kokumi, fattiness, ... (see docs or hto.obo for the full list)
# level        absent | slight | moderate | strong | intense
# phase        attack | mid-palate | finish | overall   (blank means overall)
# taster_group blank means the general population; otherwise e.g. TAS2R38 PAV/PAV,
#              PROP super-taster
# source_type  literature | panel data | expert assertion | personal tasting
# source       a PMID: or doi: when source_type is literature; otherwise who says so, and when
# explained_by optional HTO interaction id, e.g. HTO:0000411, when a known interaction
#              accounts for the level you recorded
food_id,food_label,quality,level,phase,taster_group,source_type,source,explained_by
```

- [ ] **Step 2: Create the seed profiles**

`data/raw/example_profiles.csv`. **The honesty rule from spec §10 is binding here.** Literature rows describe the PROP strip, because that is what the cited study measured; citrus rows are personal tasting at the general-population level. Do not write a literature-sourced, genotype-qualified row about a juice.

Look up the correct FoodOn CURIEs before writing them — `https://www.ebi.ac.uk/ols4/api/search?q=satsuma&ontology=foodon`. A CURIE you cannot confirm means the cell stays blank and the food lands in the gap report, which is the intended behaviour, not a failure.

```csv
# Seed profiles. Citrus rows are one person's tasting, recorded as such.
# The PROP rows are the only literature-sourced ones, and they are about the
# strip, not about any juice: PMID:37242298 measured PROP thresholds by TAS2R38
# diplotype and says nothing about citrus.
food_id,food_label,quality,level,phase,taster_group,source_type,source,explained_by
<foodon or blank>,satsuma juice,sweetness,strong,,,personal tasting,C. Sun 2026-09-18,
<foodon or blank>,satsuma juice,sourness,moderate,,,personal tasting,C. Sun 2026-09-18,
,iyokan juice,sourness,strong,,,personal tasting,C. Sun 2026-09-18,
,iyokan juice,sweetness,moderate,,,personal tasting,C. Sun 2026-09-18,
,iyokan juice,bitterness,slight,finish,,personal tasting,C. Sun 2026-09-18,
,PROP test strip,bitterness,intense,overall,TAS2R38 PAV/PAV,literature,PMID:37242298,
,PROP test strip,bitterness,moderate,overall,TAS2R38 PAV/AVI,literature,PMID:37242298,
,PROP test strip,bitterness,absent,overall,TAS2R38 AVI/AVI,literature,PMID:37242298,
```

If Task 4 produced a verified sweet-suppresses-bitter rule, add its CURIE to the `explained_by` cell of the iyokan bitterness row; if it did not, leave the cell blank rather than pointing at a rule that does not exist.

- [ ] **Step 3: Create the seed tastants**

`data/raw/example_food_tastants.csv`. cq13 returns nothing without these.

```csv
# What each food contains that can elicit a taste. CHEBI CURIEs only.
food_id,food_label,tastant,source_type,source
,iyokan juice,CHEBI:16226,literature,PMID:12595690
,iyokan juice,CHEBI:30769,expert assertion,citrus juice contains citric acid
,PROP test strip,CHEBI:8502,expert assertion,the strip is impregnated with PROP
```

`PMID:12595690` is the one citation v1 verified and kept (`docs/findings.md` §4). Re-check it with `make verify-citations` before relying on it, and if it does not support limonin in citrus, change `source_type` to `expert assertion` with a plain-language justification rather than hunting for a replacement PMID.

- [ ] **Step 4: Wire up the Makefile**

Add the target and extend `validate` (and add `profiles` to `.PHONY`):

```make
profiles:
	python3 scripts/profile2rdf.py data/raw/example_profiles.csv data/rdf/profiles.ttl \
	    --tastants data/raw/example_food_tastants.csv
```

In the `validate` target, insert this line after the `published2rdf.py` line and before `scripts/validate.py`:

```make
	python3 scripts/profile2rdf.py data/raw/example_profiles.csv data/rdf/profiles.ttl --tastants data/raw/example_food_tastants.csv
```

- [ ] **Step 5: Generate and inspect**

```bash
cd /gpfs/home2/csun/HTO && make profiles && cat docs/needs-foodon.md && head -30 data/rdf/profiles.ttl
```

Expected: the converter reports the number of entries, the gap report lists every food whose `food_id` you left blank, and the Turtle contains `HTO_0000400` entries with all five slots.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: profile sheet template and seed data, with the FoodOn gap report

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Competency questions

**Files:**
- Create: `queries/cq09.rq` … `queries/cq14.rq`
- Modify: `scripts/validate.py` (load the profiles graph)
- Modify: `tests/test_queries.py` (raise the PASS floor)

**Interfaces:**
- Consumes: the ontology from Tasks 1–4 and `data/rdf/profiles.ttl` from Task 6.
- Produces: nothing downstream; this is the proof the layer works.

- [ ] **Step 1: Teach the validator about the profiles graph**

In `scripts/validate.py`, add after the `--published` argument:

```python
    ap.add_argument("--profiles", type=pathlib.Path,
                    default=ROOT / "data" / "rdf" / "profiles.ttl",
                    help="taste profile instance graph (default data/rdf/profiles.ttl)")
```

and after the `published` block:

```python
    profiles = args.profiles
    if profiles.exists():
        g.parse(profiles, format="turtle")
    else:
        print(f"note: {profiles} absent; cq09-cq14 will be empty")
```

- [ ] **Step 2: Write the failing test**

In `tests/test_queries.py`, change `assert r.stdout.count("PASS") >= 8` to `>= 14`, and add:

```python
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
```

- [ ] **Step 3: Run it and confirm it fails**

```bash
cd /gpfs/home2/csun/HTO && make build && make validate && python3 -m pytest tests/test_queries.py -v
```

Expected: fails — the six query files do not exist.

- [ ] **Step 4: Write the six queries**

Each begins with the prefix block used by the existing queries:

```sparql
PREFIX hto:  <http://purl.obolibrary.org/obo/HTO_>
PREFIX obo:  <http://purl.obolibrary.org/obo/>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX ex:   <https://w3id.org/hto/data/>
```

`queries/cq09.rq` — what does a thing taste like?

```sparql
# The whole taste profile of every described food, strongest quality first.
# This is the question v1 could not answer: it could only list other people's
# ratings, never the taste of the thing itself.
SELECT ?foodLabel ?qualityLabel ?levelLabel ?phaseLabel ?groupLabel
WHERE {
  ?food hto:0000080 ?entry ; rdfs:label ?foodLabel .
  ?entry hto:0000081 ?quality ; hto:0000082 ?level ;
         hto:0000083 ?phase ; hto:0000084 ?group .
  ?quality rdfs:label ?qualityLabel .
  ?level   rdfs:label ?levelLabel ; hto:0000092 ?rank .
  ?phase   rdfs:label ?phaseLabel .
  ?group   rdfs:label ?groupLabel .
} ORDER BY ?foodLabel DESC(?rank)
```

`queries/cq10.rq` — phase-aware retrieval:

```sparql
# Which foods are bitter at the finish, and how bitter? Phase is a slot, not a
# term, so this catches every bitterness subtype at that phase without needing
# a pre-coordinated "lingering bitterness" term per quality.
SELECT DISTINCT ?foodLabel ?qualityLabel ?levelLabel
WHERE {
  ?food hto:0000080 ?entry ; rdfs:label ?foodLabel .
  ?entry hto:0000081 ?quality ; hto:0000082 ?level ; hto:0000083 hto:0000213 .
  ?quality rdfs:subClassOf* hto:0000114 ; rdfs:label ?qualityLabel .
  ?level rdfs:label ?levelLabel ; hto:0000092 ?rank .
  FILTER(?rank > 0)
} ORDER BY DESC(?rank) ?foodLabel
```

`queries/cq11.rq` — the genotype contrast:

```sparql
# Where does one thing taste different to different groups? Two entries on the
# same food, same quality and same phase, differing in taster group and level.
SELECT ?foodLabel ?qualityLabel ?groupA ?levelA ?groupB ?levelB
WHERE {
  ?food hto:0000080 ?e1, ?e2 ; rdfs:label ?foodLabel .
  ?e1 hto:0000081 ?quality ; hto:0000082 ?l1 ; hto:0000083 ?phase ; hto:0000084 ?g1 .
  ?e2 hto:0000081 ?quality ; hto:0000082 ?l2 ; hto:0000083 ?phase ; hto:0000084 ?g2 .
  FILTER(STR(?g1) < STR(?g2))
  FILTER(?l1 != ?l2)
  ?quality rdfs:label ?qualityLabel .
  ?g1 rdfs:label ?groupA . ?g2 rdfs:label ?groupB .
  ?l1 rdfs:label ?levelA . ?l2 rdfs:label ?levelB .
} ORDER BY ?foodLabel ?qualityLabel
```

`queries/cq12.rq` — the interaction table with its evidence:

```sparql
# What suppresses bitterness, on what evidence, demonstrated with what? A rule
# without its compound pair and citation is an unsupported claim, so all three
# are returned together.
SELECT ?agentLabel ?targetLabel ?compoundLabel ?condition ?citation
WHERE {
  ?rule rdf:type hto:0000410 ;
        hto:0000087 ?agent ; hto:0000088 ?target ; hto:0000089 hto:0000231 .
  ?target rdfs:subClassOf* hto:0000114 ; rdfs:label ?targetLabel .
  ?agent rdfs:label ?agentLabel .
  OPTIONAL { ?rule hto:0000090 ?compound . ?compound rdfs:label ?compoundLabel }
  OPTIONAL { ?rule hto:0000095 ?condition }
  OPTIONAL { ?rule obo:IAO_0000119 ?citation }
} ORDER BY ?agentLabel
```

`queries/cq13.rq` — the gap-finder:

```sparql
# Which foods contain a tastant that elicits a quality nobody has annotated on
# that food? This is what makes the compound layer useful rather than
# decorative: it proposes the next row for the profile sheet.
SELECT DISTINCT ?foodLabel ?qualityLabel ?tastantLabel
WHERE {
  ?food hto:0000086 ?tastant ; rdfs:label ?foodLabel .
  ?quality rdfs:subClassOf ?restriction ; rdfs:label ?qualityLabel .
  ?restriction owl:onProperty hto:0000085 ; owl:someValuesFrom ?tastant .
  OPTIONAL { ?tastant rdfs:label ?tastantLabel }
  FILTER NOT EXISTS { ?food hto:0000080 ?entry . ?entry hto:0000081 ?quality }
} ORDER BY ?foodLabel ?qualityLabel
```

`queries/cq14.rq` — provenance triage:

```sparql
# Which claims rest only on one person's tasting? Personal tasting is a
# first-class source in HTO, but a reader must be able to separate it from
# published evidence without reading the CSV.
SELECT ?foodLabel ?qualityLabel ?levelLabel ?source
WHERE {
  ?food hto:0000080 ?entry ; rdfs:label ?foodLabel .
  ?entry hto:0000081 ?quality ; hto:0000082 ?level ;
         hto:0000094 hto:0000244 ; hto:0000093 ?source .
  ?quality rdfs:label ?qualityLabel .
  ?level rdfs:label ?levelLabel .
} ORDER BY ?foodLabel
```

- [ ] **Step 5: Run and fix by query, never by data**

```bash
cd /gpfs/home2/csun/HTO && make build && make validate && python3 -m pytest tests/ -q
```

Expected: 14 PASS lines, 0 failing, both `qc_*.rq` still returning 0 rows.

If a query returns nothing: cq11 needs two entries differing by group (the PROP rows); cq13 needs both a `contains tastant` triple and an elicitation restriction on the *same* CHEBI term; cq12 needs at least one suppression rule whose target is bitterness or a subtype. **If cq12 is empty because Task 4 verified no bitterness-suppression rule, change the query to match what was verified** — do not add an unverified rule to satisfy a query.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: six competency questions for profiles, interactions and taster groups

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Documentation

**Files:**
- Modify: `README.md`, `docs/findings.md`

**Interfaces:** consumes everything; produces nothing but prose.

- [ ] **Step 1: Update the README**

Add a section after "The tasting sheet" describing: what a taste profile is and how it differs from a percept; the profile sheet's columns and its two defaults; the level and phase vocabularies; how to record a group-specific claim; the interaction table with a pointer to `docs/interactions.md`; and `make profiles`. Update the counts in "What HTO reuses" (56 → 57 external terms) and in "Three-layer structure" — recount from the built `hto.obo` rather than adding numbers by hand:

```bash
cd /gpfs/home2/csun/HTO && grep -c "^\[Term\]" hto.obo && grep -c "^\[Typedef\]" hto.obo && grep -c "^\[Instance\]" hto.obo
```

State the new layer honestly: it is a fourth layer, and the README's "three-layer structure" heading needs to become four.

- [ ] **Step 2: Update `docs/findings.md`**

Add: the rejected interaction candidates from Task 4 Step 7 (if not already added), and a limitation paragraph covering spec §11 R2 and R4 — ordinal levels are not comparable across sources, and a profile row needs no tasters at all, so nothing in this layer is evidence about what a population perceives.

- [ ] **Step 3: Final check and commit**

```bash
cd /gpfs/home2/csun/HTO && make clean && make build && make report && make validate && python3 -m pytest tests/ -q && make interactions-doc && make verify-citations
git add -A
git commit -m "docs: document the taste profile layer in the README and findings

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Report the final counts — terms, interaction rules, profile entries, passing competency questions, passing tests — and say plainly which spec items did not land, if any.

---

## Self-review notes

Checked against the spec on 2026-09-18:

- **§4.1 (18 properties)** → Task 1. Two type corrections applied to the spec itself, from the ROBOT probe.
- **§4.2 (slot vocabularies), §4.3 (two classes)** → Task 2.
- **§4.4 (pre-coordinated terms)** → Task 3 Step 4 (annotation) and Task 5 (`PRECOORDINATED` normalisation), tested in both.
- **§5 (sheet), §6 (converter, V1–V9)** → Tasks 5 and 6. V1–V9 each map to a parametrised rejection test except V3 and V4, which are covered by `test_defaults_are_applied_for_blank_phase_and_group` plus the bad-value cases.
- **§7 (interaction rules)** → Task 4, including the mandatory verification procedure.
- **§8 (mechanism layer)** → Task 3 (quality→tastant) and Tasks 5–6 (food→tastant).
- **§9 (cq09–cq14)** → Task 7.
- **§10 (build, tests, seed data)** → Tasks 6, 7, 8.
- **§11 (risks)** → R1 shapes Task 4's "no count promised"; R2 and R4 land in Task 8's findings update; R3 is the gap report in Task 5.

**Known deviation from the spec, deliberate:** §5 gives `food_tastants.csv` `source_type` and `source` columns, and the converter validates them, but the emitted RDF carries only the plain `contains tastant` triple — a triple cannot hold provenance without reification, and reifying the tastant layer is not worth a second entry class in v1. The provenance stays in the CSV. Task 8 Step 2 must state this in `docs/findings.md`; if it is unacceptable, the fix is a third reified class and it belongs in a follow-up, not in this plan.
