# HTO — Human Taste Ontology

Date: 2026-09-17 · Venue: BioHackathon 2026 Japan, Matsuyama · Owner: Chang Sun · Status: design approved

## 1. Purpose

There is no ontology for human taste perception. Verified 2026-09-17 against the OBO Foundry
registry (267 ontologies) and the EBI Ontology Lookup Service: FoodOn covers foods, FOBI covers
food biomarkers, CDNO covers nutrition composition, FIDEO covers food–drug interactions. None
covers what a person perceives when they taste something.

The gap is concrete and demonstrable:

| Concept | Exists today? | Where |
|---|---|---|
| bitter (as a quality) | yes | `PATO:0002474` |
| sweet, sour, salty, umami (as qualities) | **no** | only `NCIT` (a cancer thesaurus), not OBO-style |
| astringency (as a perceptual quality) | **no** | `CHEBI:74783` exists but is a *chemical role*, a category error |
| kokumi, oleogustus, mouthfeel | **no** | nowhere in OLS |
| aftertaste | **no** | only `SNOMED:110365009` |
| a tasting event (who tasted what, perceived what) | **no** | nowhere |

HTO fills exactly those gaps and reuses everything else. Its distinctive contribution is that a
**single person's single perception of a single sample is a first-class, addressable, FAIR thing**.
That is what lets two people disagree about the same glass of juice in a machine-readable way.

Deliverables by 2026-09-19:

1. `hto.owl` / `hto.obo` / `hto.json` — released ontology, ~70 new classes, reasoned and QC-clean.
2. SSSOM mapping files to NCIT, GO, ChEBI, HGNC, OBA, HPO.
3. A tasting data-collection sheet and a converter producing RDF instance data.
4. Two instance datasets: a blind citrus tasting run in Matsuyama, and a re-annotation of published
   TAS2R38 × PROP threshold data.
5. SPARQL competency questions that pass against the instance data.
6. Documentation and a published walkthrough page.

Out of scope this week: OBO Foundry registration (application only), a full BFO upper-level
alignment, odour/aroma terms (taste only, with chemesthesis where panels record it), non-human taste.

## 2. What HTO reuses (verified identifiers, 2026-09-17)

Every identifier below was resolved live via OLS4, Ensembl, HGNC or gnomAD. HTO imports these
through MIREOT modules and never redefines them.

| Domain | Terms reused |
|---|---|
| Perception processes | `GO:0050909` taste, `GO:0050913` bitter, `GO:0050916` sweet, `GO:0050915` sour, `GO:0050914` salty, `GO:0050917` umami, `GO:0001580` detection…bitter, `GO:0008527` taste receptor activity, `GO:0033038` bitter taste receptor activity, `GO:0090682` GPCR bitter taste receptor activity |
| Quality scaffolding | `PATO:0000001` quality, `PATO:0001241` physical object quality, `PATO:0002474` bitter, `PATO:0000049` intensity, `PATO:0001309` duration, `PATO:0002325` onset quality |
| Organism traits | `OBA:VT0001986` taste sensitivity trait, `OBA:VT0004209` sweet, `OBA:VT0004210` bitter, `OBA:VT0004211` sour, `OBA:VT0004212` salty, `OBA:VT0004213` umami taste sensitivity trait |
| Anatomy / cells | `UBERON:0001727` taste bud, `UBERON:0001723` tongue, `UBERON:0002448` fungiform papilla, `UBERON:0000167` oral cavity, `CL:0000209` taste receptor cell |
| Tastants | `CHEBI:8502` PROP, `CHEBI:46261` PTC, `CHEBI:15854` quinine, `CHEBI:27732` caffeine, `CHEBI:17992` sucrose, `CHEBI:30769` citric acid, `CHEBI:26710` sodium chloride, `CHEBI:16015` L-glutamate, `CHEBI:16226` limonin, `CHEBI:28819` naringin, `CHEBI:28775` hesperidin |
| Foods | `FOODON:03301103` orange juice, `FOODON:03305742` citrus juice, `FOODON:00003324` citrus fruit, `FOODON:00003555` mandarin orange, `FOODON:00003554` grapefruit, `FOODON:00003732` yuzu, `FOODON:00003027` pomelo, `FOODON:03305428` lemon juice |
| Disorders | `HP:0041051` ageusia, `HP:0000224` hypogeusia, `HP:0031249` parageusia, `HP:0000223` abnormality of taste sensation |
| Assay / data | `OBI:0000070` assay, `OBI:0001000` questionnaire, `OBI:0003725` survey administration assay, `IAO:0000109` measurement datum, `IAO:0000032` scalar measurement datum, `IAO:0000030` information content entity |
| Genetics | TAS2R38 `ENSG00000257138` (chr7:141,972,631-141,973,773); haplotype variants `rs713598` (A49P), `rs1726866` (V262A), `rs10246939` (I296V), all confirmed missense via Ensembl; 39 `TAS2R` genes in HGNC |
| Mapping targets | `NCIT:C62182` Sweet, `NCIT:C150482` Sour, `NCIT:C150480` Salty, `NCIT:C150481` Bitter, `NCIT:C150484` Umami |

**Not found and therefore requiring new HTO terms:** sweet/sour/salty/umami as OBO qualities,
astringency, pungency, cooling, tingling, kokumi, oleogustus, metallic, aftertaste, delayed
bitterness, and the whole tasting-event model. `iyokan` is absent from FoodOn and will be submitted
as a new-term request rather than minted in HTO.

## 3. Identifier policy

- Prefix `HTO`, confirmed free in the OBO Foundry registry on 2026-09-17.
- IRIs follow the OBO pattern: `http://purl.obolibrary.org/obo/HTO_0000001`, seven digits.
- ID blocks: `0000001–0000099` percept core; `0000100–0000299` quality lexicon; `0000300–0000399`
  scales and instances; `0000400–0000499` confounders and metadata.
- OBO Foundry registration is applied for after the hackathon; until then the PURL will not resolve
  and the README says so plainly.

## 4. Architecture

```
HTO/
  src/
    templates/        ROBOT template TSVs, one per module (the editable source of truth)
      core.tsv        percept core classes
      qualities.tsv   quality lexicon
      properties.tsv  object and data properties
      scales.tsv      named rating-scale individuals
    imports/          MIREOT modules, generated by `make imports`, committed
      go_import.owl pato_import.owl oba_import.owl uberon_import.owl cl_import.owl
      chebi_import.owl foodon_import.owl hp_import.owl obi_import.owl iao_import.owl ncit_import.owl
    patterns/         DOSDP pattern for "bitterness of <ChEBI class>" subtypes
    report_profile.txt  ROBOT report severity profile (which checks are ERROR vs WARN)
  mappings/           SSSOM TSVs: hto-ncit, hto-go, hto-chebi, hto-gene, hto-oba, hto-hpo
  data/
    raw/              tasting sheet CSVs as collected
    rdf/              generated instance graphs (.ttl)
    tasting_sheet.csv the blank collection template
  scripts/
    setup.sh          downloads robot.jar
    sheet2rdf.py      CSV -> RDF instance data, validated against the ontology
    validate.py       runs competency questions, exits non-zero on failure
  queries/            *.rq competency questions and QC checks
  hto.owl hto.obo hto.json   release artefacts, committed
  Makefile            robot pipeline
  docs/               spec, plan, findings, term-gap report
```

Editable source is the TSV templates. Nothing is hand-edited in OWL. The build is deterministic:
the same templates produce the same `hto.owl` byte for byte apart from a version IRI date stamp.

## 5. Layer 1 — Percept core (~22 classes)

The model reifies a perception so it can carry a rater, a scale, a value and provenance.

```
tasting session  (HTO:0000013)  ──has part──▶  tasting event (HTO:0000001) ⊑ OBI:0000070 assay
                                                   │ has participant ──▶ taster (person bearing HTO:0000002 taster role)
                                                   │ has stimulus   ──▶ taste stimulus (HTO:0000003)
                                                   │ has output     ──▶ taste percept assertion (HTO:0000005)
                                                                             │ asserts quality ──▶ perceptual taste quality (Layer 2)
                                                                             │ has intensity   ──▶ intensity rating (HTO:0000006) ⊑ IAO:0000032
                                                                             │                        └ on scale ──▶ rating scale (HTO:0000008)
                                                                             └ has hedonic    ──▶ hedonic rating (HTO:0000007)
```

Classes: tasting event, taster role, taste stimulus, reference tastant, taste percept assertion,
intensity rating, hedonic rating, rating scale, detection threshold datum, recognition threshold
datum, taster status (⊑ `OBA:VT0001986`), TAS2R38 diplotype, taste genotype assertion, tasting
session, palate cleansing process, blinding condition, time–intensity profile datum, taste
confounder, and four confounder subclasses (tobacco use, recent upper respiratory infection,
xerostomia, medication with known dysgeusia).

Taster status individuals: PROP non-taster, PROP medium taster, PROP super-taster, defined by the
standard strip protocol, each linked to the TAS2R38 diplotype that typically produces it. The link
is deliberately **not** `equivalent_to`, because the association is probabilistic: it uses
`RO:0002610 correlated with` if that term's definition fits on inspection, otherwise an HTO
annotation property `typically associated with diplotype`. The build picks one and records which in
the docs; it never asserts logical equivalence between a phenotype and a genotype.

Object properties (Layer 1): `has taster`, `has stimulus`, `asserts quality`, `has intensity
rating`, `on scale`, `has hedonic rating`, `part of session`, `has taster status`, `has genotype
assertion`, `stimulus derived from` (→ FoodOn), `stimulus contains tastant` (→ ChEBI), `perception
realises` (→ GO process).

Data properties: `rating value` (xsd:decimal), `scale minimum`, `scale maximum`, `sample order`,
`is blinded` (xsd:boolean), `collection date`.

## 6. Layer 2 — Quality lexicon (~45 classes)

Root: `HTO:0000100 perceptual taste quality` ⊑ `PATO:0001241 physical object quality`. Defined as
"a quality of a material entity that is realised in the sensory perception of taste by a human
perceiver". Every leaf carries a textual definition with a source, an exemplar tastant, and, where
known, the receptor gene.

**Basic taste quality** — sweetness, sourness, saltiness, bitterness, umami. `bitterness` is
asserted `owl:equivalentClass PATO:0002474`; the other four are the terms PATO lacks and are
proposed back to PATO as new-term requests.

**Candidate taste quality** — fattiness (oleogustus), kokumi, metallic, calcium taste, starchy
taste. Grouped separately and annotated as contested, with the literature position recorded, so the
ontology does not take a stand it cannot defend.

**Bitterness subtype** — thiourea bitterness (`CHEBI:46261`, `CHEBI:8502`; TAS2R38), limonoid
bitterness (`CHEBI:16226` limonin; citrus), flavanone bitterness (`CHEBI:28819` naringin;
grapefruit), alkaloid bitterness (`CHEBI:15854` quinine, `CHEBI:27732` caffeine), amino-acid
bitterness. Generated from a DOSDP pattern so the list extends by adding a row, not by hand-writing
OWL.

**Chemesthetic quality** — astringency, pungency, cooling, tingling, carbonation bite. Marked
explicitly as *not* taste sensu stricto (trigeminal, not gustatory) but included because sensory
panels record them and because astringency is central to citrus.

**Temporal taste quality** ⊑ `PATO:0002325 onset quality` / `PATO:0001309 duration` — onset latency,
aftertaste, lingering bitterness, delayed bitterness, taste adaptation. Delayed bitterness is the
term the Matsuyama data will actually exercise: limonin forms after juicing, so the same bottle
tastes different an hour later.

**Hedonic quality** — palatability, taste aversion.

## 7. Layer 3 — Bridges

SSSOM TSV files, one per target resource, each row carrying `predicate_id`, `mapping_justification`
(`semapv:ManualMappingCuration`) and `author_id`. Predicates are chosen honestly:
`skos:exactMatch` only where the definitions genuinely coincide (HTO bitterness ↔ `PATO:0002474`),
`skos:closeMatch` for NCIT descriptors, `skos:relatedMatch` for quality → receptor gene.

Bridge axioms in the ontology itself use two HTO-defined object properties rather than borrowed BFO
relations, because a quality is not *realised in* a process the way a role or disposition is, and
misusing `BFO:0000054` would make the ontology wrong in a way a reasoner cannot catch:

- `HTO:perceived via` — domain perceptual taste quality, range GO biological process. Each quality
  links to its GO perception process.
- `HTO:detected by receptor` — domain perceptual taste quality, range gene product. Asserted only
  where a receptor is established in the literature, with the citation on the axiom.

Before minting either, the build checks the Relation Ontology for an existing property with a
matching definition and reuses it if one exists.

## 8. Instance data

**(a) Matsuyama citrus tasting.** Four to six juices, roughly twenty participants, anonymous
participant codes. Per participant per sample: intensity of sweetness, sourness, bitterness and
astringency on the general Labelled Magnitude Scale (0–100), liking on the 9-point hedonic scale,
aftertaste present yes/no. Per participant once: PROP strip result (none / medium / strong), age
band, two confounders (current smoker, recent loss of smell), and a `consent` column the participant
ticks, which the converter requires before emitting any row for that participant. No names, no
identifiers that could re-identify; the sheet carries that statement at its head. This is a
food-preference exercise with commercially available juices and taste strips, not a clinical
investigation. Anyone with a citrus allergy or a latex/strip sensitivity simply does not take part,
which the sheet states.

**(b) Published re-annotation.** The PROP threshold study in adults in Japan
(PMC10222862) reports thresholds by TAS2R38 diplotype. Each reported group becomes a
`taste percept assertion` set with `detection threshold datum`, showing the schema accommodates
literature data and not only our own sheet.

## 9. Competency questions

The ontology is correct when these return the right answers on the instance data. Each becomes a
`.rq` file and a test.

1. Which perceived qualities were reported for a given FoodOn citrus juice, and by how many tasters?
2. What is the mean bitterness intensity per PROP taster status?
3. Which tasters rated the same sample more than one standard deviation apart on bitterness?
4. Which tastants present in the sampled juices are known agonists of TAS2R38?
5. Which HTO qualities have no exact match in PATO? (the gap report, generated from the mappings)
6. Retrieve all assertions of a temporal quality, with the sample and the elapsed time since juicing.
7. Which participants report a confounder that would exclude them from a bitterness analysis?
8. For each basic taste, which GO perception process and which OBA sensitivity trait does it link to?

## 10. Build, QC and tests

`make all` runs: templates → modules; MIREOT extracts → imports; merge → `hto-edit.owl`; ELK
reasoning; annotate with version IRI and licence; convert to `.obo` and `.json`.

Quality gates, all enforced in CI-style by `make test`:

- `robot reason --reasoner ELK` succeeds and the ontology is consistent with no unsatisfiable classes.
- `robot report --profile src/report_profile.txt` returns zero ERROR-level violations. Warnings are
  listed in the docs, not suppressed silently.
- Every `HTO:` class has exactly one label, one textual definition, and a definition source.
- Every `HTO:` class is reachable from `HTO:0000100` or `HTO:0000001` (no orphans).
- Every quality leaf has at least one mapping or one logical axiom (no floating vocabulary).
- `scripts/validate.py` runs all eight competency questions; each must return a non-empty result set
  with the expected shape.
- `sheet2rdf.py` round-trips: CSV → TTL → SPARQL recovers the original ratings exactly.
- The converter rejects malformed sheets (out-of-range intensity, unknown sample, missing consent
  flag) with a clear message rather than emitting bad RDF.

Licence: CC BY 4.0 for the ontology, MIT for the scripts, matching OBO Foundry expectations.

## 11. Risks and honest limitations

- **Twenty tasters is a demonstration, not a study.** The dataset shows the schema works; it does
  not support claims about the Japanese population. The README and findings will say this.
- **PROP strips approximate TAS2R38 status; they are not genotyping.** Recorded as a phenotype, with
  the association to diplotype marked probabilistic.
- **Chemesthesis is included but flagged** as trigeminal rather than gustatory, because excluding it
  would make the ontology useless for real panels while conflating it would be wrong.
- **Contested tastes** (kokumi, oleogustus) are included under a clearly separate parent with the
  controversy annotated.
- **The PURL will not resolve** until OBO Foundry registration completes.
- **Descriptor terms are culture-bound.** English labels with Japanese synonyms where a participant
  used one; the lexicon does not claim cross-cultural completeness.

## 12. Day plan (17 Sep → 19 Sep)

- Thu: repo, build pipeline, imports, percept core, quality lexicon drafted, `hto.owl` builds and reasons.
- Fri morning: mappings, tasting sheet, converter, competency questions, run the tasting at the venue.
- Fri afternoon: instance data, published re-annotation, gap report, docs, walkthrough page, demo.
