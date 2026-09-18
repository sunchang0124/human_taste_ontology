# HTO — Taste profiles, interactions and taster groups

Date: 2026-09-18 · Owner: Chang Sun · Status: design approved · Branch: `feat/taste-profiles`

## 1. Purpose

HTO v1 models **events**: `P01 perceived bitterness at 6.2 on the gLMS in blinded sample C`.
Everything hangs off `HTO:0000001 tasting event`. Asked "what does iyokan juice taste like?", the
released ontology can only answer "here are fourteen people's ratings of it". The juice itself
carries no taste.

This design adds the layer that answers the question directly. Three requirements, stated by the
owner on 2026-09-18:

1. **A way for people to specify the taste of a thing.** Not a study — a person saying what a food
   or drink tastes like, in a form a machine can read and pool with other people's descriptions.
2. **Tastes interact.** Sweetness makes sourness less extreme; salt suppresses bitterness. These
   relations between qualities are absent from HTO: the 34 qualities sit in a hierarchy and never
   touch.
3. **Taste is genotype-relative.** A thing tastes different to people carrying a particular variant.
   `HTO:0000064 typically associated with diplotype` exists with **zero uses**, and even populated it
   would only relate a diplotype to a taster status, never "this thing tastes different to you".

### What changes, in one line

HTO stops being only a record of tastings and becomes also a description of **things, and of how
qualities behave** — independent of any one tasting.

### Out of scope

- **Deriving profiles from percept data** (median rating → ordinal level). The obvious bridge between
  the two layers, deliberately deferred: it needs its own decisions about aggregation across scales
  and raters, and nothing in this design depends on it. Named as follow-up F1 in §11.
- **Numeric interaction magnitudes** and time–intensity curves (§7, §11).
- **Aroma and cross-modal flavour.** Taste and chemesthesis only, as in v1.
- **Tastant concentration.** A food either contains a tastant or does not; how much is not modelled.

## 2. Decisions taken during brainstorming

Each was chosen by the owner on 2026-09-18 and is binding on the implementation.

| # | Question | Decision |
|---|---|---|
| D1 | What carries a taste? | **A kind of food or drink**, not a compound, not a specific batch. |
| D2 | How much does one taste statement carry? | **A reified profile entry**: quality + level + phase + taster group + source. Not a bare triple. |
| D3 | Intensity form | **Ordinal**, not numeric. A person must be able to fill it in by hand. |
| D4 | Temporal structure | **Three phases** — attack, mid-palate, finish — plus `overall` as the default. Not five, not time–intensity curves. |
| D5 | Where do interactions live? | **Between qualities**, as general rules, not per-food and not between compounds. |
| D6 | Do compounds appear at all? | **Yes, as an optional mechanism layer.** They explain a quality, and they are required for the genotype chain, but nobody must supply one to describe a food. |
| D7 | How is "for whom" specified? | **A general taster-group slot**, definable by genotype *or* by phenotype, seeded with TAS2R38 and PROP taster status. |
| D8 | Where does the knowledge physically live? | **Split by kind** (approach C, §3). |

## 3. Architecture

The split follows what the knowledge *is*, not what is convenient to build:

| Knowledge | Nature | Home | Edited by |
|---|---|---|---|
| Slot vocabularies (levels, phases, groups, effects, evidence types) | Closed, small, stable | Ontology (`src/templates/`) | Ontology editor |
| Interaction rules | Curated, expert, citation-bearing, ~10–15 | Ontology (`src/templates/interactions.tsv`) | Ontology editor |
| Quality → tastant elicitation | Curated, stable | Ontology (`src/templates/qualities.tsv`, new column) | Ontology editor |
| **Per-food profiles** | Open-ended, contributed, grows forever | **Instance data** (`data/profile_sheet.csv` → RDF) | Anyone with a CSV |
| **Food → tastant** | Open-ended, contributed | **Instance data** (`data/food_tastants.csv` → RDF) | Anyone with a CSV |

The line matches OBO practice: PATO ships qualities, not measurements. It also means the work a
person can do at a tasting table touches a CSV, and the work that needs literature and verification
touches the ontology templates.

Rejected alternatives:

- **Everything as OWL axioms.** Four slots per entry forces deeply nested anonymous classes,
  provenance rides on axiom annotations, and every contributed profile becomes an ontology edit only
  an ontologist can make.
- **Everything as instance data.** Cheap, but the interaction rules — HTO's actual contribution —
  would sit outside the release, so importing `hto.owl` would not give you "sweet suppresses bitter".

## 4. Identifier allocation

Existing blocks are untouched: core `0000000`–`0000026`, properties `0000050`–`0000076`, qualities
`0000100`–`0000162`, scales `0000300`–`0000305`.

### 4.1 New properties (`src/templates/properties.tsv`)

| ID | Label | Type | Domain | Range |
|---|---|---|---|---|
| `HTO:0000080` | has profile entry | object | food kind | `HTO:0000400` |
| `HTO:0000081` | entry quality | object | `HTO:0000400` | `HTO:0000100` |
| `HTO:0000082` | entry level | object | `HTO:0000400` | `HTO:0000200` |
| `HTO:0000083` | entry phase | object | `HTO:0000400` | `HTO:0000210` |
| `HTO:0000084` | holds for group | object | `HTO:0000400` | `HTO:0000220` |
| `HTO:0000085` | elicited by tastant | object | `HTO:0000100` | `CHEBI:24431` (chemical entity) |
| `HTO:0000086` | contains tastant | object | food kind | `CHEBI:24431` |
| `HTO:0000087` | interaction agent | object | `HTO:0000410` | `HTO:0000100` |
| `HTO:0000088` | interaction target | object | `HTO:0000410` | `HTO:0000100` |
| `HTO:0000089` | interaction effect | object | `HTO:0000410` | `HTO:0000230` |
| `HTO:0000090` | demonstrated with | object | `HTO:0000410` | `CHEBI:24431` |
| `HTO:0000091` | explained by interaction | object | `HTO:0000400` | `HTO:0000410` |
| `HTO:0000092` | level rank | data (integer) | `HTO:0000200` | — |
| `HTO:0000093` | source statement | data (string) | `HTO:0000400` | — |
| `HTO:0000094` | has evidence type | object | `HTO:0000400` | `HTO:0000240` |
| `HTO:0000095` | interaction condition | data (string) | `HTO:0000410` | — |
| `HTO:0000096` | group defined by status | object | `HTO:0000223` | `HTO:0000011` |
| `HTO:0000097` | group defined by diplotype | object | `HTO:0000222` | `HTO:0000015` |

Range `CHEBI:24431` (chemical entity) is **not currently imported**: it is one new row in
`src/external_terms.tsv`, fetched by the existing `scripts/build_imports.py`, taking the external
term count from 56 to 57.

`HTO:0000086 contains tastant` is a new property rather than a reuse of `HTO:0000060 stimulus
contains tastant`: the existing property's domain is `HTO:0000003 taste stimulus`, an instance
poured in a tasting event, not a kind of food.

`HTO:0000096` and `HTO:0000097` are the join back to the v1 core: a phenotype-defined group points at
an existing `HTO:0000011 taster status` subclass, a genotype-defined group at an `HTO:0000015 TAS2R38
diplotype`. Nothing from v1 is duplicated.

### 4.2 Slot vocabularies (new `src/templates/vocabularies.tsv`)

Closed lists, each member a named individual so a CSV can reference it by label.

**`HTO:0000200` taste intensity level** — with `level rank` for ordering and comparison:

| ID | Label | Rank |
|---|---|---|
| `HTO:0000201` | absent | 0 |
| `HTO:0000202` | slight | 1 |
| `HTO:0000203` | moderate | 2 |
| `HTO:0000204` | strong | 3 |
| `HTO:0000205` | intense | 4 |

`absent` is not padding: it is how the AVI/AVI half of a genotype contrast is stated.

**`HTO:0000210` tasting phase** — `HTO:0000211` attack, `HTO:0000212` mid-palate, `HTO:0000213`
finish, `HTO:0000214` overall (default when a row leaves phase blank).

**`HTO:0000220` taster group** — `HTO:0000221` general population (default); subclasses
`HTO:0000222` genotype-defined taster group and `HTO:0000223` phenotype-defined taster group.
Seeded members: `HTO:0000224` TAS2R38 PAV/PAV, `HTO:0000225` TAS2R38 PAV/AVI, `HTO:0000226` TAS2R38
AVI/AVI (each via `group defined by diplotype`); `HTO:0000227` PROP non-taster, `HTO:0000228` PROP
medium-taster, `HTO:0000229` PROP super-taster (each via `group defined by status`, pointing at
`HTO:0000012`–`HTO:0000014`).

**`HTO:0000230` taste interaction effect** — `HTO:0000231` suppression, `HTO:0000232` enhancement.

**`HTO:0000240` evidence type** — `HTO:0000241` literature, `HTO:0000242` panel data, `HTO:0000243`
expert assertion, `HTO:0000244` personal tasting.

### 4.3 New classes

- **`HTO:0000400` taste profile entry** — one line of a thing's taste. Instances live in data.
- **`HTO:0000410` taste interaction** — one rule. Instances live in the ontology, `HTO:0000411`
  onward.

### 4.4 The two pre-coordinated temporal terms

`HTO:0000153 lingering bitterness` and `HTO:0000154 delayed bitterness` bake the phase into the term,
which does not scale (34 qualities × 3 phases). Both are **kept, not deprecated** — the published
walkthrough advertises `HTO:0000154`. Each gains an annotation naming the preferred post-coordinated
form (`bitterness` + phase `finish`), and `profile2rdf.py` accepts either spelling, normalising to
the post-coordinated form in the emitted RDF.

## 5. The profile sheet

`data/profile_sheet.csv`, one row per profile entry, with the consent-free structure of a reference
table rather than a participant form.

| Column | Required | Content |
|---|---|---|
| `food_id` | no | FoodOn CURIE, e.g. `FOODON:03301710`. Blank → local IRI + gap report. |
| `food_label` | yes | Human-readable name, e.g. `iyokan juice`. |
| `quality` | yes | HTO quality label or CURIE. |
| `level` | yes | One of the five level labels. |
| `phase` | no | Blank → `overall`. |
| `taster_group` | no | Blank → `general population`. |
| `source_type` | yes | One of the four evidence types. |
| `source` | yes | Free text, or `PMID:…` / `doi:…` when `source_type` is `literature`. |
| `explained_by` | no | An interaction CURIE, e.g. `HTO:0000411`. |

Example, with the genotype contrast as two rows differing only in group and level:

```csv
food_id,food_label,quality,level,phase,taster_group,source_type,source,explained_by
FOODON:03301710,satsuma juice,sweetness,strong,,,personal tasting,C. Sun 2026-09-18,
FOODON:03301710,satsuma juice,sourness,moderate,,,personal tasting,C. Sun 2026-09-18,
,iyokan juice,bitterness,slight,finish,,personal tasting,C. Sun 2026-09-18,HTO:0000411
,PROP test strip,bitterness,intense,overall,TAS2R38 PAV/PAV,literature,PMID:37242298,
,PROP test strip,bitterness,absent,overall,TAS2R38 AVI/AVI,literature,PMID:37242298,
```

The minimum honest row is a food, a quality, a level, and where the claim came from. A person's own
tasting is a first-class source — it simply has to declare itself as one.

`data/food_tastants.csv` is separate, because containing a compound is a fact about the food and not
about one entry: `food_id, food_label, tastant, source_type, source`.

## 6. The converter

`scripts/profile2rdf.py`, mirroring the interface and error discipline of `scripts/sheet2rdf.py`.
Input: a profile CSV. Output: `data/rdf/profiles.ttl` plus `docs/needs-foodon.md`.

**Validation rules. Every failure is an error with a line number, and the run emits no graph at all
— partial output is worse than none.**

| # | Rule |
|---|---|
| V1 | `quality` resolves to a subclass of `HTO:0000100`, by label or CURIE. |
| V2 | `level` is one of the five level individuals. |
| V3 | `phase` blank → `overall`; otherwise one of the four. |
| V4 | `taster_group` blank → `general population`; otherwise one of the seeded groups. |
| V5 | `source_type` is one of the four evidence types. |
| V6 | `source` is non-empty; when `source_type` is `literature` it matches `PMID:\d+` or a DOI. |
| V7 | `explained_by`, if present, resolves to an existing `HTO:0000410` individual **and that interaction's `interaction target` equals the row's quality**. |
| V8 | `food_id`, if present, matches `FOODON:\d+`. If blank, a local IRI `https://w3id.org/hto/data/food/<slug>` is minted (the namespace
`scripts/sheet2rdf.py` already uses for instance data) and the food is listed in
`docs/needs-foodon.md`. |
| V9 | No two rows share the same (food, quality, phase, taster group): that is a contradiction, not a duplicate. |

V7 is the rule that makes `explained_by` worth having. "The sweetness explains why bitterness reads
slight here" fails validation if the rule cited is about sourness.

**Citations are verified out of band.** The converter checks only the *format* of a PMID or DOI, so
it stays offline and deterministic under test. `make verify-citations` is a separate, network-touching
target that resolves every identifier in the templates and the profile data against PubMed and reports
any whose title does not plausibly match the claim. This is not optional hygiene: in the v1 build ten
of eleven proposed PMIDs were fabricated — real identifiers pointing at unrelated papers (see
`docs/findings.md` §4).

## 7. Interaction rules

New ROBOT template `src/templates/interactions.tsv`, one row per rule, producing `HTO:0000410`
individuals from `HTO:0000411`.

| Column | Content |
|---|---|
| `ID`, `LABEL` | e.g. `HTO:0000411`, "sweetness suppresses bitterness" |
| `agent` | quality doing the suppressing/enhancing |
| `target` | quality affected |
| `effect` | `suppression` or `enhancement` |
| `demonstrated_with` | the compound pair actually tested, as ChEBI CURIEs |
| `condition` | free text: concentrations, matched intensities, reversals |
| `citation` | verified PMID or DOI |
| `definition` | `IAO:0000115` text |

Three modelling decisions:

- **Rules are directional.** "Sweetness suppresses bitterness" and "bitterness suppresses sweetness"
  are different claims with different evidence. If both hold, that is two rows.
- **No magnitude field.** Published percentage reductions hold at one concentration pairing and do
  not transfer. The `condition` text carries the caveat rather than a number that would look more
  portable than it is.
- **`demonstrated_with` is mandatory.** Every psychophysics result is about sucrose versus quinine,
  not "sweet versus bitter". Without the compound pair the citation does not support the rule as
  stated.

**Candidate rules**, to be verified before any is committed: sucrose suppressing quinine bitterness;
sodium chloride suppressing bitterness; sucrose and citric acid suppressing each other; sodium
chloride enhancing sweetness at low concentration; glutamate enhancing saltiness; astringency
accumulating over repeated sips. The binary taste–taste interaction review literature (Keast &
Breslin and successors) is the first place to look. **No count is promised.** A rule ships only if a
real paper stating it can be found and verified; a claim that survives only as folklore stays out,
and the shipped table is however long verification allows.

The build generates `docs/interactions.md` so the table is readable without SPARQL.

## 8. The mechanism layer

Compounds are not what carries a taste (D1) but they are what makes a profile explainable, and they
are unavoidable for the genotype chain: TAS2R38 binds thioureas, not juice.

Three statement kinds, only the first required:

1. **Food → quality** — the profile entry (§5).
2. **Quality → elicited by tastant** — `HTO:0000085`, curated once in the ontology.
   `limonoid bitterness ← limonin (CHEBI:16226)`, `flavanone bitterness ← naringin (CHEBI:28819)`,
   `sourness ← citric acid (CHEBI:30769)`, `sweetness ← sucrose (CHEBI:17992)`,
   `saltiness ← sodium chloride (CHEBI:26710)`, `umami ← L-glutamic acid (CHEBI:16015)`,
   `thiourea bitterness ← PROP (CHEBI:8502)` and `PTC (CHEBI:46261)`.
3. **Food → contains tastant** — `HTO:0000086`, contributed in `data/food_tastants.csv`.

This costs no new imports: all eleven ChEBI tastants are already in `src/external_terms.tsv` and are
currently among the 24 imported-but-unreferenced terms the README admits to. The quality lexicon
already half-encodes the link — `limonoid bitterness`, `flavanone bitterness`, `thiourea bitterness`
are compound classes wearing quality names — and `HTO:0000085` makes that explicit instead of leaving
it in the label.

With all three present, the chain the owner asked for closes and is queryable end to end:

```
iyokan juice --contains--> limonin --elicits--> limonoid bitterness
limonoid bitterness --subclass of--> bitterness --perceived via--> GO:0050913 bitter perception
profile entry (iyokan, bitterness, strong, finish) --holds for group--> TAS2R38 PAV/PAV
```

## 9. Competency questions

Six new questions, `queries/cq09.rq` – `cq14.rq`, each required to return at least one row against
the seed data:

| CQ | Question |
|---|---|
| cq09 | What does a given food taste like? Every quality with its level, ordered by rank. |
| cq10 | Which foods are bitter at the finish? Phase-aware retrieval across the corpus. |
| cq11 | How does one food's profile differ between two taster groups? The requirement-3 query. |
| cq12 | Which qualities suppress bitterness, with what evidence and demonstrated with what compounds? |
| cq13 | Which foods contain a tastant that elicits a quality nobody has annotated on that food? A gap-finder — this is what makes the mechanism layer useful rather than decorative. |
| cq14 | Which profile claims rest only on personal tasting rather than literature or panel data? |

## 10. Build, tests and seed data

**Makefile targets.** `build` gains the two new templates; `profiles` runs the converter; `validate`
runs cq09–cq14 alongside the existing eight; `verify-citations` is new, network-touching, and
excluded from `make test`.

**Tests**, extending the existing 30:

- Ontology: new terms present and reasoner-consistent; `robot report` still 0 ERROR; the four slot
  vocabularies closed (no member outside the enumerated list); every interaction row carries agent,
  target, effect, `demonstrated_with` and a format-valid citation.
- Converter: a valid sheet produces the expected triples; each rejection path is its own test — V1
  unknown quality, V2 bad level, V5 bad evidence type, V6 missing source, V7 mismatched
  `explained_by`, V9 contradictory duplicate; V8 unmapped food lands in the report and not in the
  graph as a FoodOn term.
- Queries: cq09–cq14 each return ≥ 1 row; both QC queries still return 0.

**Seed data, and the honesty rule it enforces.** During design an example row claimed
`iyokan juice, bitterness, strong, PAV/PAV, PMID:37242298`. That is false. The Aoki study measured
**PROP strip** thresholds by diplotype and says nothing about iyokan; asserting a genotype-specific
iyokan level from it would be a fabricated claim wearing a real citation — the exact failure this
repo already suffered. The seed therefore splits:

- **From literature:** PROP strip bitterness by TAS2R38 group. This is what the paper supports, and
  it exercises the group slot honestly.
- **From personal tasting:** the citrus profiles, `source_type: personal tasting`, group *general
  population*.
- **Asserted by nobody:** whether iyokan specifically is bitterer to PAV carriers. That is a
  hypothesis, and it is testable at a table with strips and juice using the v1 tasting sheet.
- **`data/food_tastants.csv` is seeded too**, minimally — iyokan juice containing limonin, grapefruit
  juice containing naringin — because cq13, the gap-finder, returns nothing without both the
  food→tastant and quality→tastant links present.

A useful consequence of the ordinal choice (D3): *strong* is far easier to source honestly than
*4.2 on the gLMS*. Papers routinely support ordinal claims they cannot support numerically.

## 11. Risks, limitations and follow-ups

- **R1 — the interaction literature may not support directional claims as cleanly as the textbooks
  imply.** Mixture suppression is concentration-dependent and often mutual. Mitigation: mandatory
  `condition` text, directional rows, and a shipped table sized by what verifies rather than by what
  was hoped for.
- **R2 — ordinal levels are not comparable across sources.** One person's *strong* is another's
  *moderate*, and a level derived from panel data is not commensurate with one from a juice stand.
  Mitigation: `source_type` is mandatory and cq14 exists precisely to triage on it. HTO does not
  claim cross-source comparability and must not be read as doing so.
- **R3 — FoodOn coverage.** Many foods worth describing have no FoodOn term; iyokan is the case that
  started this project. Mitigation: local IRIs plus `docs/needs-foodon.md`, which feeds the upstream
  requests already drafted in `docs/term-requests/`.
- **R4 — a profile is a claim, not a measurement.** Nothing in this layer is evidence of what a
  population perceives. The v1 limitation that twenty tasters is a demonstration and not a study
  applies here with more force, because a profile row needs no tasters at all.
- **F1 — follow-up: derive profiles from percept data.** Median rating per (food, quality) → ordinal
  level, with the rater count carried through. Deferred, not cancelled.

## 12. Delivery

`feat/hto` was merged to `main` (fast-forward, `cabfcee`) before this branch was cut, so the finished
v1 ontology no longer rides on a single unmerged branch. This work proceeds on `feat/taste-profiles`.
The repository still has no git remote; pushing to GitHub is the owner's decision and is not part of
this design.
