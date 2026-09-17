# New term request: sweetness, sourness, saltiness, umami as PATO qualities

**Tracker:** https://github.com/pato-ontology/pato/issues
**Requested by:** Chang Sun (chang.sun@maastrichtuniversity.nl), Human Taste Ontology (HTO)
**Date:** 2026-09-17

## Summary

PATO defines `PATO:0002474 bitter` as a quality of taste, but has no sibling
terms for the other three (or four, depending on how umami is counted) basic
tastes. Requesting four new terms as siblings of `PATO:0002474`, i.e. as
qualities under the same taste-quality branch of PATO.

This gap was found while building the Human Taste Ontology (HTO), which
needed these qualities and, finding none in PATO on searching OLS and the
PATO source on 2026-09-17, defined them locally as `HTO:0000111`–`HTO:0000115`
with a plan to submit them upstream rather than keep them as an unreviewed
fork of PATO's quality space. HTO's gap analysis
(`docs/pato-gap-report.md`) found that 33 of HTO's 34 quality-lexicon terms
have no PATO equivalent; these four are the ones with the clearest claim to
belong in PATO itself, because — unlike HTO's citrus-specific bitterness
subtypes or contested candidate tastes — they are the remaining three
(four) members of the basic-taste set PATO has already started with
`bitter`.

## Requested terms

Definitions below are copied verbatim from HTO's quality lexicon
(`src/templates/qualities.tsv`), where they are asserted as subclasses of
`HTO:0000110 basic taste quality`, itself a subclass of
`PATO:0001241 physical object quality` (until/unless PATO accepts these
terms, at which point HTO would switch its own bitterness axiom's pattern —
`owl:equivalentClass` — to these as well).

### 1. sweetness

> The basic taste quality typically elicited by sucrose and other sugars,
> transduced by the TAS1R2 and TAS1R3 receptor pair.

GO process reference: `GO:0050916` sensory perception of sweet taste.

### 2. sourness

> The basic taste quality typically elicited by citric acid and other
> acids, transduced by proton-sensitive channels of taste receptor cells.

GO process reference: `GO:0050915` sensory perception of sour taste.

### 3. saltiness

> The basic taste quality typically elicited by sodium chloride, transduced
> principally by the epithelial sodium channel.

GO process reference: `GO:0050914` sensory perception of salty taste.

### 4. umami

> The basic taste quality typically elicited by L-glutamate and by certain
> ribonucleotides, transduced by the TAS1R1 and TAS1R3 receptor pair.

GO process reference: `GO:0050917` sensory perception of umami taste.

## Why PATO and not elsewhere

The only OBO-style representation of these four qualities currently
findable through OLS is under `NCIT` (a cancer thesaurus — `NCIT:C62182`
Sweet, `NCIT:C150482` Sour, `NCIT:C150480` Salty, `NCIT:C150484` Umami),
which is the wrong home for a general-purpose perceptual quality and is
mapped from HTO only as `skos:closeMatch`, not reused as the primary term.
PATO already models `bitter` as a quality of taste; these four terms
complete that set using the same pattern PATO already applies to `bitter`.

## Cross-reference

HTO's own definitions and mappings for these four terms, for anyone
checking this request against the source:

- `src/templates/qualities.tsv` — `HTO:0000111`–`HTO:0000115`
- `mappings/hto-pato.sssom.tsv` — current (necessarily weaker than exact)
  mappings from these HTO terms to PATO
- `mappings/hto-go.sssom.tsv` — mappings to the four GO processes above
- `docs/pato-gap-report.md` — the full gap analysis
