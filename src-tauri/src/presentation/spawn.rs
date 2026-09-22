//! Arrival timing only; no selection, rarity inference, clock polling or new timer.
pub fn hold_seconds(rarity: &str) -> f64 {
    static DURATIONS: std::sync::OnceLock<serde_json::Value> = std::sync::OnceLock::new();
    let values = DURATIONS.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../../../src/presentation/spawnDurations.json"
        ))
        .expect("checked presentation durations")
    });
    // Preserve the existing 600ms COMMON/debug startup. Longer arrival layers finish
    // before the existing World state transitions into ambient behavior.
    values
        .get(rarity)
        .and_then(|v| v.as_f64())
        .unwrap_or(300.0)
        .max(600.0)
        / 1000.0
}
