//! Read-only Collection projection. Discovery is session evidence from server encounters.
use crate::backend::battle::Collected;
use serde::Serialize;
#[derive(Clone, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Presentation {
    pub records: Option<Vec<Collected>>,
    pub discovered_codes: Vec<String>,
    pub busy: bool,
    pub error: Option<String>,
}
impl Presentation {
    pub fn begin(&mut self) {
        self.busy = true;
        self.error = None;
    }
    pub fn finish(&mut self, error: Option<String>) {
        if self.busy {
            self.busy = false;
            self.error = error;
        }
    }
    pub fn discover(&mut self, code: &str) {
        if !self.discovered_codes.iter().any(|c| c == code) {
            self.discovered_codes.push(code.into());
        }
    }
    pub fn loaded(&mut self, records: Vec<Collected>) {
        self.records = Some(records);
    }
    pub fn captured(&mut self, record: &Collected) {
        self.discover(&record.monster_code);
        // A single capture response is not a complete Collection snapshot.
        if let Some(records) = &mut self.records {
            if let Some(old) = records
                .iter_mut()
                .find(|r| r.monster_code == record.monster_code)
            {
                *old = record.clone();
            } else {
                records.push(record.clone());
            }
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn record(code: &str, count: u64) -> Collected {
        serde_json::from_value(
            serde_json::json!({"monsterCode":code,"monsterName":code,"captureCount":count,
        "firstCapturedAt":"2026-09-22T00:00:00Z","lastCapturedAt":"2026-09-22T01:00:00Z"}),
        )
        .unwrap()
    }
    #[test]
    fn unloaded_empty_failure_retry_and_retained_snapshot() {
        let mut p = Presentation::default();
        assert!(p.records.is_none());
        p.begin();
        p.finish(Some("offline".into()));
        assert!(p.records.is_none());
        assert!(!p.busy);
        assert!(p.error.is_some());
        p.begin();
        assert!(p.error.is_none());
        p.loaded(vec![]);
        p.finish(None);
        assert_eq!(p.records.as_ref().unwrap().len(), 0);
        p.loaded(vec![record("PIP", 4)]);
        p.begin();
        p.finish(Some("offline".into()));
        assert_eq!(p.records.as_ref().unwrap()[0].capture_count, 4);
    }
    #[test]
    fn discovery_is_deduplicated_and_capture_preserves_other_records() {
        let mut p = Presentation::default();
        p.discover("PIP");
        p.discover("PIP");
        assert_eq!(p.discovered_codes, vec!["PIP"]);
        p.captured(&record("PIP", 7));
        assert!(p.records.is_none());
        p.loaded(vec![record("PIP", 2), record("FUTURE", 3)]);
        p.captured(&record("PIP", 7));
        assert_eq!(p.records.as_ref().unwrap().len(), 2);
        assert_eq!(p.records.as_ref().unwrap()[0].capture_count, 7);
        p.captured(&record("ANOTHER", 1));
        assert_eq!(p.records.as_ref().unwrap().len(), 3);
        p.finish(Some("unrelated request".into()));
        assert!(p.error.is_none());
    }
    #[test]
    fn server_encounter_discovers_but_debug_spawn_does_not_and_dex_stays_open() {
        let mut world = crate::behaviors::World::new(
            crate::geometry::Area {
                x: 0.0,
                y: 0.0,
                w: 1200.0,
                h: 800.0,
            },
            0.0,
            1,
        );
        world.debug_spawn(0.0);
        assert!(world.view.dex.discovered_codes.is_empty());
        let encounter=serde_json::from_value(serde_json::json!({
            "encounterId":"00000000-0000-0000-0000-000000000001",
            "monster":{"code":"PIP","name":"PIP","rarity":"COMMON","movementProfile":"GROUND","level":1},
            "spawnedAt":"2026-09-22T00:00:00Z","expiresAt":"2026-09-22T00:01:00Z"
        })).unwrap();
        crate::spawn::runtime::test_environment(&mut world);
        world.apply_server_encounter(0.0, Some(encounter), 60.0);
        assert_eq!(world.view.dex.discovered_codes, vec!["PIP"]);
        world.view.menu = true;
        world.view.interaction = crate::behaviors::InteractionMode::Dex;
        world.despawn(1.0);
        assert!(world.view.menu);
    }
}
