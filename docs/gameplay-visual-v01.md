# Gameplay Visual Integration v0.1

Presentation-only extension of PR11. Cozy cream/green MOA and smaller cream/brown diagnostic PIP; no new PNG or character design. Keep existing 240x300 interaction NSPanel and all native focus flags.

Before implementation: events[] currently contains names only. Client-derived damage would violate server authority. Add optional presentationEvents [{type,damage}] to Battle DTO, computed on the server from the existing resolved HP decrease. Preserve original events[], formulas, locking, lifecycle, schema and migrations. Alternative of estimating damage or copying CombatRules into Desktop is rejected.

A separate Rust presentation controller consumes authoritative DTOs immediately, deduplicates transient responses, and schedules a bounded cue queue on the existing 33ms world tick. Rendering receives phase/damage/reward/level feedback only. No per-damage window/timer, HTTP on AppKit, or authoritative HP interpolation. Motion is CSS on an inner visual wrapper, independent of sprite animation/world position/anchor.

Implementation and validation pending. Physical mouse/typing focus remains MANUAL_REQUIRED; PR10 tool-driven activation attribution is not resolved by this feature. No automatic merge.
