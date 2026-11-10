# Scryfall nonland import

`decklist_import.py` implements a stateless query workflow; there is intentionally
no local catalog, disk cache, or bulk download. `decklist_import.ipynb` is the
paste-and-run entry point and must be edited through IDE notebook tools.

## Conventions

- Use `/cards/collection` with name identifiers in batches of at most 75.
  Send User-Agent/Accept/Content-Type headers, use a 30-second timeout, and leave
  at least 500 ms between batch starts. Do not retry HTTP errors automatically.
- Disregard set/collector annotations and format legality. Index returned names
  and front-face names explicitly; collection response order is not meaningful.
  Aggregate duplicate physical cards by Oracle ID (printing ID as fallback).
- Land filtering uses the front/main face's card type, not cost emptiness or
  color identity. Missing mana cost is not a zero-cost spell.
- Front/main faces only for transform/modal_dfc/adventure/flip layouts. Reject
  split cards and unknown multiface layouts rather than combining their costs.
- Emit existing `SpellCost` values at weight 1; all generic and WUBRG symbols
  are preserved and canonicalized by `SpellCost`. Unsupported symbols fail.
- A failed import aggregates card diagnostics and returns no partial result.
  Clear notebook `SPELLS` before each query so an old successful import cannot
  survive a later failure. Sideboards are not imported.

## Verification

The supplied Dimir deck was successfully queried through the IDE notebook kernel
on 2026-11-09: 60 main-deck cards, 37 nonlands across 15 names, 23 lands omitted.
The live query also resolved printing annotations such as Bitter Triumph (SOA)
because matching is by exact name, independent of printing metadata. Cecil used
its front-face cost B; Kaito used 2UB, ignoring ninjutsu.

The notebook kernel could access Scryfall even when web-document fetches returned
403 and PowerShell's Invoke-RestMethod could not establish its connection. Such
transport failures do not establish that the API itself is unavailable.

Offline tests mock HTTP transport and responses; the sample-deck count test uses
explicitly synthetic costs to test routing, not assert unverified card facts.

Sources: [API](https://scryfall.com/docs/api),
[collection](https://scryfall.com/docs/api/cards/collection),
[card objects](https://scryfall.com/docs/api/cards),
[access and rate-limit guidance](https://scryfall.com/docs/faqs/i-m-having-trouble-accessing-the-scryfall-api-or-i-m-blocked-17).
