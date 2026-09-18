# HTO — Human Taste Ontology

No ontology of human taste perception existed before HTO: this was verified on
2026-09-17 against the OBO Foundry registry (267 ontologies) and the EBI
Ontology Lookup Service, and HTO fills that gap by making a single person's
single perception of a single tasted sample a first-class, addressable,
FAIR thing.

**Walkthrough page:** https://claude.ai/artifact/L5wdjXo15GqfinKaixEtPs — the gap, the ontology's layers, a worked tasting, and what the build does and does not demonstrate.

## The gap

| Concept | Exists today? | Where |
|---|---|---|
| bitter (as a quality) | yes | `PATO:0002474` |
| sweet, sour, salty, umami (as qualities) | **no** | only `NCIT`, a cancer thesaurus, not OBO-style |
| astringency (as a perceptual quality) | **no** | `CHEBI:74783` exists but is a *chemical role*, a category error |
| kokumi, oleogustus, mouthfeel | **no** | nowhere in OLS |
| aftertaste | **no** | only `SNOMED:110365009` |
| a tasting event (who tasted what, perceived what) | **no** | nowhere |

FoodOn covers foods, FOBI covers food biomarkers, CDNO covers nutrition
composition, and FIDEO covers food–drug interactions — none of them cover what
a person perceives when they taste something. HTO fills exactly the gaps
above and reuses everything else it can find. See `docs/findings.md` for the
full prior-art search.

## Quick start

**Prerequisites:** Java 21 (ROBOT 1.9.10 is built for it) and Python 3.9 or
newer with the packages in `requirements.txt` (`pip install -r
requirements.txt`; rdflib 7 and pytest 7 or newer).

```bash
bash scripts/setup.sh   # downloads the pinned ROBOT 1.9.10 jar
make build               # templates -> reasoned hto.owl, hto.obo, hto.json
make test                 # report (QC) + validate (competency questions) + pytest
make validate             # build the instance data and run the fourteen competency questions
```

`make build && make validate` and `make test` both currently succeed with zero
failures (see `docs/findings.md` for the exact competency-question output and
`docs/pato-gap-report.md` for the gap table).

## What HTO reuses

HTO never redefines a term it can import. The authoritative list of every
external term reused, with the ontology it comes from and why it was pulled
in, is `src/external_terms.tsv` — currently 57 terms: ChEBI (12), GO (11),
FoodOn (8), PATO (6), OBA (6), UBERON (4), HP (4), IAO (3), OBI (2), CL (1).
Each is imported as a small MIREOT-style module under `src/imports/`, built
by `scripts/build_imports.py` from the OLS4 API (see "Design decisions"
below for why OLS rather than `robot extract`).

Being imported is not the same as being used, and the list should not be read
as 57 terms doing work. Of the 57: 23 are referenced by an HTO axiom in
`src/templates/*.tsv` (a set that grew in this branch, because the
interaction rules' `demonstrated_with` column and the food→tastant links both
cite ChEBI compounds directly), 3 FoodOn terms are referenced by the instance
data via `data/raw/example_samples.csv` (disjoint from the template-referenced
set), 25 appear as mapping objects in `mappings/*.sssom.tsv` (18 of which
overlap with the template-referenced set), and 24 are declared and imported
but not yet referenced by any HTO axiom, mapping or datum.

## Four-layer structure

Measured directly from the ROBOT template TSVs and the released `hto.obo`
(132 `[Term]` stanzas, 32 `[Typedef]` stanzas, 0 `[Instance]` stanzas,
imported terms included). HTO declares **75 classes** of its own: 26 core,
34 quality, 6 scale, 9 profile/interaction vocabulary.

- **Layer 1 — Percept core** (`src/templates/core.tsv`, 26 classes; the
  27th row, `HTO:0000000`, is an annotation property, not a class). Reifies
  a perception so it can carry a rater, a scale, a value and provenance:
  tasting event, taster role, taste stimulus, taste percept assertion,
  intensity/hedonic/threshold ratings, taster status, TAS2R38 diplotype,
  tasting session, confounders, and related information content entities.
- **Layer 2 — Quality lexicon** (`src/templates/qualities.tsv`, 34 classes).
  Rooted at `HTO:0000100 perceptual taste quality`. Basic tastes, candidate
  (contested) tastes, bitterness subtypes generated from a DOSDP-style
  pattern, chemesthetic qualities flagged as trigeminal, temporal qualities,
  and hedonic qualities.
- **Layer 3 — Bridges** (`mappings/*.sssom.tsv`, five files, 30 mapping rows
  total). SSSOM mappings from HTO terms to NCIT, GO, ChEBI, OBA and PATO,
  each with `mapping_justification` and an honestly chosen predicate (see
  below).
- **Layer 4 — Taste profiles, interactions and taster groups**
  (`src/templates/profiles.tsv`, 9 classes plus 22 named individuals; and
  `src/templates/interactions.tsv`, 9 named individuals). Lets a kind of
  food or drink carry its own taste profile, independent of any tasting
  event, and lets qualities interact with each other. See
  "Taste profiles" below.

Supporting modules: `src/templates/properties.tsv` (42 object/data/annotation
properties: 32 object, 8 data, 2 annotation) and `src/templates/scales.tsv`
(6 classes: five rating scales — general LMS, LMS, 9-point hedonic scale,
visual analogue scale and just-about-right scale — plus `HTO:0000305 PROP
filter paper strip protocol`, which is not a rating scale at all and is
parented at `OBI:0000070 assay`: a procedure for eliciting a response is not
a specification of permitted values and anchors).

## The tasting sheet

`data/tasting_sheet.csv` is the blank collection template; `scripts/sheet2rdf.py`
converts a filled sheet to validated RDF instance data. The consent and safety
text now lives at the head of `data/tasting_sheet.csv` itself, as `#` comment
lines that the converter skips, so it travels with the sheet handed to
participants instead of only with this README. It is adapted from the design
spec §8 (which states the requirement in prose rather than giving fixed
wording), and reads:

> You are identified only by an anonymous code you choose yourself. No names
> and no identifiers that could re-identify anyone are collected. Taking part
> is voluntary: you may decline, or stop at any point, with no consequence.
> This is a food-preference exercise using commercially available juices and
> taste strips, not a clinical investigation. Anyone with a citrus allergy, or
> a sensitivity to the taste strips, should not take part.

The sheet has a `consent` column, and `sheet2rdf.py` refuses to emit any row
for a participant unless that column reads `yes`: `data/raw/example_tasting.csv`
includes one participant (`P99`) who declined consent precisely to exercise
this gate, and no assertions are produced for them.

## Taste profiles

Everything above this section is about a **percept**: one tasting event, one
taster, one moment. A **taste profile entry** is a different kind of claim: it
says that a *kind* of food or drink — satsuma juice in general, not the glass
someone drank on 18 September — carries a quality at some level, without
needing a taster to have been in the room. You use a profile entry when you
want to say "iyokan juice is slightly bitter in the finish" as a fact about
iyokan juice, the way a tasting note or a spec sheet would, rather than as a
report of what one person perceived on one occasion.

**The profile sheet**, `data/profile_sheet.csv` (seeded example at
`data/raw/example_profiles.csv`), has one row per claim:

| Column | Required | Content |
|---|---|---|
| `food_id` | no | A FoodOn CURIE, e.g. `FOODON:03301710`. Left blank, the food gets a local identifier instead and is listed in the FoodOn gap report (below). |
| `food_label` | yes | The name people would actually use, e.g. `iyokan juice`. |
| `quality` | yes | An HTO taste quality, by label or CURIE, e.g. `bitterness`. |
| `level` | yes | One of five ordinal levels: `absent`, `slight`, `moderate`, `strong`, `intense`. |
| `phase` | no | One of `attack`, `mid-palate`, `finish`, `overall`. **Blank means `overall`** — the whole tasting taken together, not any one stage of it. |
| `taster_group` | no | A named taster group (see below). **Blank means `general population`** — no genotype or phenotype qualifier. |
| `source_type` | yes | Where the claim comes from: `literature`, `panel data`, `expert assertion`, or `personal tasting`. |
| `source` | yes | Free text, or a `PMID:…`/`doi:…` when `source_type` is `literature`. |
| `explained_by` | no | An interaction rule CURIE (see below) that accounts for the level reported. |

The two blank-means-something-specific defaults are the ones easy to miss when
filling the sheet by hand: an entry with no `phase` is not "unspecified," it
is asserted to hold across the whole tasting, and an entry with no
`taster_group` is asserted to hold for tasters generally, not just for
whoever happened to write the row.

**Recording a group-specific claim.** Not every claim holds for everyone. To
say something is true only for people with a particular genotype or measured
phenotype, fill `taster_group` with a seeded group instead of leaving it
blank — for example `TAS2R38 PAV/PAV taster group`, `TAS2R38 AVI/AVI taster
group`, `PROP non-taster group`, `PROP medium-taster group`, or `PROP
super-taster group`. The seed data does exactly this for PROP bitterness: the
same quality, at three different levels, filed as three rows that differ only
in `taster_group`. A `personal tasting` row from one named source is a
first-class claim too — it just has to say so honestly as its `source_type`.

**Interactions.** Some qualities change how strongly another quality reads —
sweetness commonly suppresses bitterness, for instance. HTO ships nine such
rules as `HTO:0000410 taste interaction` individuals, each citing a real
psychophysics paper, naming the actual compounds it was tested with, and
stating a direction (never "sweet and bitter interact," always "sweetness
suppresses bitterness"). A profile entry can point at one of these rules
through `explained_by`, to say *why* a level reads the way it does rather
than just asserting that it does. The full table, generated from
`src/templates/interactions.tsv`, is `docs/interactions.md`.

**What a food contains**, as opposed to what it tastes like, is recorded
separately, in a sheet of its own: `data/food_tastants.csv` is the blank
template (`food_id, food_label, tastant, source_type, source`, with the same
`#` comment header as the profile sheet), and `data/raw/example_food_tastants.csv`
is the seeded example. This is a fact about the food's chemistry, not one more
line of its taste profile. Its `source_type` and `source` columns are held to
exactly the rule the profile sheet's are: one of the four evidence types, a
non-empty source, and a `PMID:`/`doi:` rather than free text whenever
`source_type` is `literature`.

**The FoodOn gap report.** Many real foods — iyokan is the case that started
this project — have no FoodOn term. Rather than force a profile entry onto
the wrong FoodOn class, a blank `food_id` gets a local IRI and is listed in
the generated `docs/needs-foodon.md`, which feeds the upstream new-term
requests in `docs/term-requests/`.

**Building the seed data:** `make profiles` runs `scripts/profile2rdf.py` over
the two *example* sheets — `data/raw/example_profiles.csv` and
`data/raw/example_food_tastants.csv` — writing `data/rdf/profiles.ttl` and
regenerating the committed `docs/needs-foodon.md`. It is also run as part of
`make validate`.

**Converting your own sheet is a direct call, not `make profiles`.** That
target's inputs are hardcoded to the examples, so running it after filling in
`data/profile_sheet.csv` would convert the example data and hand you a graph
full of satsuma juice. Call the script with your own paths instead:

```bash
python3 scripts/profile2rdf.py data/profile_sheet.csv my-profiles.ttl \
    --tastants data/food_tastants.csv \
    --gap-report my-needs-foodon.md
```

`--tastants` and `--gap-report` are both optional. The gap report defaults to
`needs-foodon.md` **beside the output `.ttl`**, never inside `docs/`, so
converting a sheet of your own cannot overwrite the repository's committed
report.

Every validation failure is a rejection naming the physical line in your file,
and a sheet with even one bad row produces no graph at all — partial output
would be worse than none.

**Two things this layer does not give you, said plainly rather than left for
you to discover:**

- **Named individuals — the four vocabularies above (levels, phases, taster
  groups, evidence types) and all nine interaction rules — do not reach the
  OBO release.** `hto.obo` contains zero `[Instance]` stanzas; the classes
  (`HTO:0000400 taste profile entry`, `HTO:0000410 taste interaction`, and
  so on) are there, but none of the individuals asserted on them are. This
  is not a bug in this branch — it is how ROBOT's OBO conversion treats
  named individuals in general, and it affects the pre-existing slot
  vocabularies exactly as it affects the interactions table. If you download
  `hto.obo` and go looking for the interaction table or the level
  vocabulary, you will not find it there. Use `hto.owl` or `hto.json`
  instead; both carry every individual.
- **A profile entry is a claim, not a measurement**, and levels are not
  comparable across sources — one person's *strong* is another's *moderate*,
  and a `personal tasting` level is not commensurate with a `literature`
  level from a different study. A profile row does not require any tasters
  at all, so this layer is not evidence about what any population perceives.
  See `docs/findings.md` for the full statement of this limitation.

## Design decisions and deviations

- **`skos:exactMatch` rather than `owl:equivalentClass` to PATO.** Only
  `HTO:0000114 bitterness` gets `skos:exactMatch PATO:0002474`, because that
  is the one case where the definitions genuinely coincide. Every other HTO
  quality gets a weaker predicate (`skos:relatedMatch`, `skos:closeMatch`,
  `skos:broadMatch`) rather than a false claim of logical equivalence to a
  PATO term that does not exist.
- **Imports built from the OLS4 API rather than `robot extract`.** The
  source ontologies (ChEBI, FoodOn, GO, ...) exceed a gigabyte on disk and
  HTO needs only 56 terms out of them; `scripts/build_imports.py` resolves
  each identifier live via OLS4 and writes a minimal module instead of
  running a MIREOT/SLME extraction over multi-gigabyte source files.
- **No DOSDP tooling dependency.** The bitterness-subtype pattern
  (`HTO:0000130`–`HTO:0000135` in `src/templates/qualities.tsv`) is
  DOSDP-*shaped* — one row per subtype, sharing a common structure — but is
  expressed inline as ordinary ROBOT template rows rather than run through
  DOSDP tooling, so the pipeline has one fewer moving part during a two-day
  build.
- **Chemesthesis is included but flagged.** Astringency, pungency, cooling,
  tingling and carbonation bite are marked explicitly as trigeminal, not
  gustatory (`HTO:0000140 chemesthetic quality`, not a subclass of basic
  taste quality) — excluding them would make the ontology useless for real
  sensory panels, but asserting they are taste would be wrong.
- **Candidate tastes are kept under a separate parent.** Fattiness
  (oleogustus), kokumi, metallic, calcium taste and starchy taste sit under
  `HTO:0000120 candidate taste quality`, a separate parent class from
  `HTO:0000110 basic taste quality`, so using HTO does not commit you to
  treating them as basic tastes. The controversy is recorded in each
  definition instead: the ontology does not assert a scientific consensus
  that does not exist.
- **A common `rating` superclass was added.** `HTO:0000026 rating` was
  introduced above intensity rating and hedonic rating so that the data
  property `rating value` (`HTO:0000070`) has one domain that legitimately
  covers both, instead of being declared twice or given a domain wider than
  it should have.
- **`HTO:0000065 has diplotype` and `HTO:0000066 threshold for quality`
  were added** during the published re-annotation work because the existing
  properties' declared domains and ranges did not fit the triples that
  re-annotation needed to assert; adding narrow, correctly scoped properties
  was judged better than forcing a triple through a property whose domain
  or range it would contradict.

## Licence

- The ontology content (`src/templates/`, `src/imports/`, `src/metadata.ttl`,
  and the generated `hto.owl`, `hto.obo`, `hto.json`) is licensed under
  **CC BY 4.0**.
- Everything under `scripts/` and `tests/` is licensed under the **MIT
  License**.
- See `LICENSE` for the full text of both.
- **HTO's PURLs do not resolve.** `http://purl.obolibrary.org/obo/HTO_*`
  IRIs are used throughout the ontology as the OBO Foundry expects, but OBO
  Foundry registration has not happened yet — it is applied for after this
  work, not before — so those PURLs will 404 until registration completes.

## More

- `docs/findings.md` — the prior-art search, the PATO gap, what the instance
  data does and does not demonstrate, the competency-question results, and
  the full limitations section.
- `docs/pato-gap-report.md` — generated gap table (`scripts/gap_report.py`).
- `docs/interactions.md` — the full taste interaction table, generated by
  `scripts/interactions_md.py` from `src/templates/interactions.tsv`.
- `docs/needs-foodon.md` — generated report of foods with no FoodOn term,
  written by `scripts/profile2rdf.py`.
- `docs/term-requests/` — ready-to-paste upstream new-term requests for PATO
  and FoodOn.
