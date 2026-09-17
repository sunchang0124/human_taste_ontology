# New term request: iyokan (Citrus × iyo)

**Tracker:** https://github.com/FoodOntology/foodon/issues
**Requested by:** Chang Sun (chang.sun@maastrichtuniversity.nl), Human Taste Ontology (HTO)
**Date:** 2026-09-17

## Summary

FoodOn already has terms for several citrus fruits and their juices —
`FOODON:00003555` mandarin orange, `FOODON:00003554` grapefruit,
`FOODON:00003732` yuzu, `FOODON:00003027` pomelo, plus the general
`FOODON:00003324` citrus fruit and juice terms such as
`FOODON:03301103` orange juice, `FOODON:03305742` citrus juice and
`FOODON:03305428` lemon juice — but has no term for **iyokan**
(*Citrus × iyo*, sometimes called *Citrus iyo*), searched for and not found
in OLS or the FoodOn source on 2026-09-17.

Iyokan is the characteristic citrus of Ehime prefecture, Japan — the
prefecture whose capital, Matsuyama, is the venue for the tasting that this
ontology (the Human Taste Ontology, HTO) was built to support. FoodOn's
existing coverage of satsuma (mandarin orange), yuzu and pomelo, without
iyokan, leaves a specific and fillable gap: iyokan is a distinct, named,
commercially significant citrus cultivar, not a synonym or minor variety of
any citrus FoodOn already lists.

## Requested term

- **Label:** iyokan
- **Synonym:** Citrus iyo
- **Scientific name:** *Citrus × iyo* Hort. ex Y.Tanaka
- **Definition (proposed):** A citrus fruit of the hybrid species
  *Citrus × iyo*, believed to derive from a cross between a mandarin orange
  and an orange-type citrus, characterised by an easy-to-peel rind, a
  bittersweet flesh and prominent astringency and limonoid bitterness;
  cultivated principally in Ehime Prefecture, Japan, where it is the
  prefecture's characteristic citrus fruit.
- **Suggested parent:** the same FoodOn branch used for its sibling citrus
  terms, e.g. as a sibling of `FOODON:00003555` mandarin orange and
  `FOODON:00003027` pomelo under FoodOn's citrus fruit hierarchy
  (`FOODON:00003324` citrus fruit).
- **Suggested juice term:** an `iyokan juice` term as a sibling of
  `FOODON:03301103` orange juice and `FOODON:03305742` citrus juice, for
  consistency with FoodOn's existing pattern of fruit + corresponding juice
  terms.

## Why this matters for HTO

HTO's instance data model (`src/templates/core.tsv`,
`HTO:0000059 stimulus derived from`) links a `taste stimulus` to the FoodOn
food class it was prepared from. Without an `iyokan` FoodOn term, a real
iyokan-juice tasting sample collected at the Matsuyama venue cannot be
linked to a specific FoodOn class the way the other juices in the planned
tasting (mandarin, grapefruit, yuzu, pomelo) can; it would have to fall back
to the generic `citrus juice` term, losing the distinction HTO otherwise
preserves between its sampled juices. Filing this request is the honest
alternative to either minting an ad hoc food term inside HTO (out of scope
for an ontology about perception, not food classification) or silently
under-specifying the sample.

## Cross-reference

- `src/external_terms.tsv` — the eight FoodOn terms HTO currently reuses
- `docs/superpowers/specs/2026-09-17-hto-design.md` §2 — "What HTO reuses",
  which records `iyokan` as absent from FoodOn and slated for this request
  rather than being minted inside HTO
