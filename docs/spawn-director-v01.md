# Desktop Spawn Director Foundation v0.1

## Architecture decision (before implementation)

Add an isolated Rust orchestration module consuming DesktopSafeArea, Size and MovementProfile. Production automatic scheduling remains disabled: the existing manual PIP / server Encounter path remains authoritative and unchanged. No backend scheduler, new polling loop, UI, dependency or database change.

Alternatives: replacing MonsterSelector would violate server authority; integrating the unmerged Monster Dex branch would couple parallel work; enabling automatic POST now would change gameplay. All are deferred. Human architecture review is required before merge.

Implementation and validation details follow in this PR.
