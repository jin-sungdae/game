# Monster Production Asset Delivery v0.1

## Design before implementation

Extend the existing Monster Asset Registry, BaseAssetLoader, rendererSource and Python Asset Validator. Do not introduce an asset engine or merge Companion/Monster registries. Preserve PIP's path and legacy 0.8 gameplay wrapper scale. Add explicit delivery identities for the requested fifteen assets without mapping provisional Dex codes, activating monsters or modifying content DB/Collection UI.

All production PNGs remain user-delivered; this PR creates no production or placeholder PNGs. Binary parser fixtures are temporary test data only. Optional alpha validation accepts missing delivery, but validates every present file; explicit strict-alpha requires all fifteen bases independently of Companion frames.

The current Monster renderer has no animation scheduler. Extend its source selection contract to accept an optional same-monster, registered animation frame, validated through the existing image loader; an external existing animation producer owns timing. No new timer or engine. Animation failure falls through to the same monster base, then diagnostic. Visual scale is bounded and fitted inside the existing presentation envelope; PIP's existing scale is not multiplied twice.

Alternatives rejected: another registry/master in the database, copied Companion animation pipeline, placeholder art, and enabling missing content in gameplay. Human review applies before merge.
