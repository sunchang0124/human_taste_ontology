# HTO — Human Taste Ontology

No ontology of human taste perception existed before HTO: this was verified on
2026-09-17 against the OBO Foundry registry (267 ontologies) and the EBI
Ontology Lookup Service, and HTO fills that gap by making a single person's
single perception of a single tasted sample a first-class, addressable,
FAIR thing.

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

```bash
bash scripts/setup.sh   # downloads robot.jar
make build               # templates -> reasoned hto.owl, hto.obo, hto.json
make test                 # report (QC) + validate (competency questions) + pytest
make validate             # build the instance data and run the eight competency questions
```

`make build && make validate` and `make test` both currently succeed with zero
failures (see `docs/findings.md` for the exact competency-question output and
`docs/pato-gap-report.md` for the gap table).

## What HTO reuses

HTO never redefines a term it can import. The authoritative list of every
external term reused, with the ontology it comes from and why it was pulled
in, is `src/external_terms.tsv` — currently 56 terms: GO (11), ChEBI (11),
FoodOn (8), PATO (6), OBA (6), UBERON (4), HP (4), IAO (3), OBI (2), CL (1).
Each is imported as a small MIREOT-style module under `src/imports/`, built
by `scripts/build_imports.py` from the OLS4 API (see "Design decisions"
below for why OLS rather than `robot extract`).

## Three-layer structure

Measured directly from the ROBOT template TSVs and the released `hto.obo`
(122 `[Term]` stanzas, 17 `[Typedef]` stanzas):

- **Layer 1 — Percept core** (`src/templates/core.tsv`, 27 classes). Reifies
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

Supporting modules: `src/templates/properties.tsv` (24 object/data
properties) and `src/templates/scales.tsv` (6 rating-scale classes: general
LMS, LMS, 9-point hedonic scale, visual analogue scale, just-about-right
scale, and the PROP filter-paper strip protocol).

## The tasting sheet

`data/tasting_sheet.csv` is the blank collection template; `scripts/sheet2rdf.py`
converts a filled sheet to validated RDF instance data. This is the consent
and safety text that goes at the head of the printed sheet handed to
participants, copied from the design spec §8:

> Participants are identified only by an anonymous code they choose. No
> names, no identifiers that could re-identify anyone. This is a
> food-preference exercise with commercially available juices and taste
> strips, not a clinical investigation. Anyone with a citrus allergy or a
> latex/strip sensitivity simply does not take part.

The sheet has a `consent` column, and `sheet2rdf.py` refuses to emit any row
for a participant unless that column reads `yes`: `data/raw/example_tasting.csv`
includes one participant (`P99`) who declined consent precisely to exercise
this gate, and no assertions are produced for them.

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
- **No DOSDP tooling dependency**, only a DOSDP-*shaped* pattern for
  bitterness subtypes (`src/patterns/`) expressed directly as ROBOT template
  rows, so the pipeline has one fewer moving part during a two-day build.
- **Chemesthesis is included but flagged.** Astringency, pungency, cooling,
  tingling and carbonation bite are marked explicitly as trigeminal, not
  gustatory (`HTO:0000140 chemesthetic quality`, not a subclass of basic
  taste quality) — excluding them would make the ontology useless for real
  sensory panels, but asserting they are taste would be wrong.
- **Candidate tastes are kept under a separate parent.** Fattiness
  (oleogustus), kokumi, metallic, calcium taste and starchy taste sit under
  `HTO:0000120 candidate taste quality`, disjoint in the hierarchy from
  `HTO:0000110 basic taste quality`, with the controversy recorded in each
  definition, so the ontology does not assert a scientific consensus that
  does not exist.
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

- The ontology content (`src/templates/`, `src/imports/`, `src/patterns/`,
  `src/metadata.ttl`, and the generated `hto.owl`, `hto.obo`, `hto.json`) is
  licensed under **CC BY 4.0**.
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
- `docs/term-requests/` — ready-to-paste upstream new-term requests for PATO
  and FoodOn.
