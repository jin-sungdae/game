//! Server-owned Dex projection and placement acknowledgements.
use super::*;
#[derive(Clone, Debug, PartialEq)]
pub struct Job {
    pub encounter_id: uuid::Uuid,
    pub code: String,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Entry {
    pub dex_no: u32,
    pub state: String,
    pub monster_code: Option<String>,
    pub monster_name: Option<String>,
    pub asset_identity: Option<String>,
    pub base_asset: Option<String>,
    pub encounter_count: u64,
    pub first_discovered_at: Option<DateTime<Utc>>,
    pub last_seen_at: Option<DateTime<Utc>>,
    pub capture_count: u64,
    pub first_captured_at: Option<DateTime<Utc>>,
    pub last_captured_at: Option<DateTime<Utc>>,
}
impl Entry {
    fn valid(&self) -> bool {
        let discovery = self.encounter_count > 0;
        let capture = self.capture_count > 0;
        let timestamps =
            |count: bool, first: Option<DateTime<Utc>>, last: Option<DateTime<Utc>>| {
                if count {
                    first.zip(last).is_some_and(|(f, l)| f <= l)
                } else {
                    first.is_none() && last.is_none()
                }
            };
        (1..=30).contains(&self.dex_no)
            && timestamps(discovery, self.first_discovered_at, self.last_seen_at)
            && timestamps(capture, self.first_captured_at, self.last_captured_at)
            && self.state
                == if capture {
                    "CAPTURED"
                } else if discovery {
                    "DISCOVERED"
                } else {
                    "UNDISCOVERED"
                }
            && if discovery || capture {
                self.monster_code.as_ref().is_some_and(|c| !c.is_empty())
                    && self.monster_name.as_ref().is_some_and(|n| !n.is_empty())
            } else {
                self.monster_code.is_none()
                    && self.monster_name.is_none()
                    && self.asset_identity.is_none()
                    && self.base_asset.is_none()
            }
    }
    pub fn collected(&self) -> Option<battle::Collected> {
        if self.state != "CAPTURED" {
            return None;
        }
        Some(battle::Collected {
            monster_code: self.monster_code.clone()?,
            monster_name: self.monster_name.clone()?,
            capture_count: self.capture_count,
            first_captured_at: self.first_captured_at?,
            last_captured_at: self.last_captured_at?,
        })
    }
}
impl Api {
    pub fn dex(&self) -> Result<Vec<Entry>, &'static str> {
        let rows: Vec<Entry> = self.request("/api/v1/dex", false)?.ok_or("missing Dex")?;
        let numbers: std::collections::HashSet<_> = rows.iter().map(|r| r.dex_no).collect();
        let codes: Vec<_> = rows
            .iter()
            .filter_map(|r| r.monster_code.as_ref())
            .collect();
        let unique: std::collections::HashSet<_> = codes.iter().collect();
        if rows.len() != 30
            || numbers.len() != 30
            || unique.len() != codes.len()
            || rows.iter().any(|r| !r.valid())
        {
            return Err("invalid Dex");
        }
        Ok(rows)
    }
    pub fn discover(&self, job: &Job) -> Result<Entry, &'static str> {
        if !job.code.chars().all(|c| c.is_ascii_uppercase())
            || job.code.is_empty()
            || job.encounter_id.is_nil()
        {
            return Err("invalid discovery command");
        }
        let row: Entry = self
            .request_json(
                &format!("/api/v1/monsters/{}/discoveries", job.code),
                Some(&serde_json::json!({"encounterId":job.encounter_id})),
            )?
            .ok_or("missing discovery")?;
        if !row.valid() || row.encounter_count == 0 || row.monster_code.as_ref() != Some(&job.code)
        {
            return Err("invalid discovery response");
        }
        Ok(row)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{behaviors::World, geometry::Area};
    fn world() -> World {
        let mut w = World::new(
            Area {
                x: 0.0,
                y: 0.0,
                w: 1200.0,
                h: 800.0,
            },
            0.0,
            7,
        );
        crate::spawn::runtime::test_environment(&mut w);
        w
    }
    #[test]
    fn stale_snapshot_and_late_discovery_never_downgrade_capture() {
        let mut p = crate::collection_dex::Presentation::default();
        let captured = battle::Collected {
            monster_code: "WISP".into(),
            monster_name: "WISP".into(),
            capture_count: 2,
            first_captured_at: Utc::now(),
            last_captured_at: Utc::now(),
        };
        p.captured(&captured);
        p.loaded(vec![]);
        assert_eq!(p.records.as_ref().unwrap()[0].capture_count, 2);
        p.loaded(vec![battle::Collected {
            capture_count: 1,
            ..captured.clone()
        }]);
        assert_eq!(p.records.as_ref().unwrap()[0].capture_count, 2);
    }
    #[test]
    fn malformed_projection_and_masking_are_rejected() {
        let mut row:Entry=serde_json::from_value(serde_json::json!({"dexNo":1,"state":"UNDISCOVERED","encounterCount":0,"captureCount":0})).unwrap();
        assert!(row.valid());
        row.monster_name = Some("PIP".into());
        assert!(!row.valid());
        row.monster_name = None;
        row.state = "DISCOVERED".into();
        assert!(!row.valid());
    }
    #[test]
    #[ignore = "requires isolated live Discovery Spring/PostgreSQL; run before and after actual Spring restart"]
    fn live_discovery_restart_slice() {
        let api = Api::new(&std::env::var("LUMA_LIVE_TEST_URL").unwrap()).unwrap();
        let stage = std::env::var("LUMA_DISCOVERY_STAGE").unwrap();
        let mut w = world();
        w.apply_bootstrap(api.bootstrap().unwrap());
        let rows = api.dex().unwrap();
        w.view.dex.loaded_dex(&rows);
        if stage == "after" {
            let row = rows
                .iter()
                .find(|r| r.monster_code.as_deref() == Some("WISP"))
                .unwrap();
            assert_eq!(row.state, "DISCOVERED");
            assert_eq!(row.encounter_count, 1);
            assert_eq!(row.capture_count, 0);
            assert!(w.view.dex.discovered_codes.iter().any(|c| c == "WISP"));
            assert!(w.view.pip.is_none());
            if let Some(old) = api.encounter(false).unwrap() {
                api.ignore(old.encounter_id).unwrap();
            }
        } else {
            assert!(!w.view.dex.discovered_codes.iter().any(|c| c == "WISP"));
        }
        let e = api.encounter(true).unwrap().unwrap();
        assert_eq!(e.monster.code, "WISP");
        assert!(w.discovery.next(0.0).is_none());
        w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
        assert!(w.view.pip.is_some());
        let job = w.discovery.next(0.0).unwrap();
        // Simulate a failed POST without changing gameplay or removing the entity.
        w.discovery.complete(&job, 0.0, false, true);
        assert!(w.view.pip.is_some());
        assert!(!w.view.game.busy);
        assert!(w.discovery.next(4.9).is_none());
        let job = w.discovery.next(5.0).unwrap();
        let row = api.discover(&job).unwrap();
        assert_eq!(row.state, "DISCOVERED");
        w.discovery.complete(&job, 5.0, true, true);
        w.view.dex.acknowledged(&row);
        assert_eq!(
            api.discover(&job).unwrap().encounter_count,
            row.encounter_count
        );
        if stage == "after" {
            assert_eq!(row.encounter_count, 2);
            let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
            while b.status == battle::Status::Active {
                b = api.battle(b.battle_id, Some("attack")).unwrap();
            }
            assert_eq!(b.status, battle::Status::Victory);
            let c = api.capture(b.battle_id).unwrap();
            assert!(c.success);
            w.view.dex.captured(c.collection.as_ref().unwrap());
            w.view.dex.acknowledged(&row); // Delayed discovery cannot erase capture evidence.
            assert_eq!(w.view.dex.records.as_ref().unwrap()[0].capture_count, 1);
            let rows = api.dex().unwrap();
            assert_eq!(
                rows.iter()
                    .find(|r| r.monster_code.as_deref() == Some("WISP"))
                    .unwrap()
                    .state,
                "CAPTURED"
            );
        } else {
            assert!(api.collection().unwrap().is_empty());
            let mut restored = world();
            restored.view.dex.loaded_dex(&api.dex().unwrap());
            assert!(restored
                .view
                .dex
                .discovered_codes
                .iter()
                .any(|c| c == "WISP"));
        }
        eprintln!(
            "LIVE DISCOVERY stage={stage} WISP placement/POST/retry/Dex verified encounter={}",
            e.encounter_id
        );
    }
}
