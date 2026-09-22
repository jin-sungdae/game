//! Batch3 fixtures reuse #27 provider/clock injection; production flags stay closed.
use super::*;
use crate::{behaviors::World, desktop::SafeAreaTracker, geometry::Area};
use chrono::{DateTime, FixedOffset};
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Arc, Mutex,
};
#[derive(Clone)]
struct FakeClock {
    value: Arc<Mutex<DateTime<FixedOffset>>>,
    reads: Arc<AtomicUsize>,
}
impl FakeClock {
    fn at(hour: u32, minute: u32) -> Self {
        let value =
            DateTime::parse_from_rfc3339(&format!("2026-09-22T{hour:02}:{minute:02}:00+09:00"))
                .unwrap();
        Self {
            value: Arc::new(Mutex::new(value)),
            reads: Arc::new(AtomicUsize::new(0)),
        }
    }
}
impl conditions::CalendarClock for FakeClock {
    fn local_now(&self) -> DateTime<FixedOffset> {
        self.reads.fetch_add(1, Ordering::Relaxed);
        *self.value.lock().unwrap()
    }
}
struct FixtureProvider;
fn definition(code: &str) -> serde_json::Value {
    let records: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("../../../../src/entities/monster-dex.json")).unwrap();
    records
        .into_iter()
        .find(|m| m["monsterCode"] == code)
        .unwrap()
}
impl SpawnCandidateProvider for FixtureProvider {
    fn candidate(&self, code: &str) -> Option<Candidate> {
        let d = definition(code);
        Some(Candidate {
            monster_code: code.into(),
            zone: super::super::dex_adapter::fixture_zone(d["spawnProfile"].as_str()?)?,
            movement_profile: serde_json::from_value(d["movementProfile"].clone()).ok()?,
            size: crate::geometry::PIP_SIZE,
            lifetime: Duration::from_secs(60),
            condition: serde_json::from_value(d["spawnCondition"].clone()).ok()?,
        })
    }
    fn identity(&self, code: &str) -> Option<MonsterIdentity> {
        let d = definition(code);
        Some(MonsterIdentity {
            monster_code: code.into(),
            asset_identity: code.to_lowercase(),
            rarity: d["rarity"].as_str()?.into(),
            level: 0,
            encounter_id: None,
            movement_profile: serde_json::from_value(d["movementProfile"].clone()).ok()?,
        })
    }
}
fn fixture(code: &str, clock: &FakeClock, id: u128) -> (World, Encounter) {
    let screen = Area {
        x: -3000.0,
        y: -1100.0,
        w: 2000.0,
        h: 1000.0,
    };
    let safe = SafeAreaTracker::default().update(1, screen, Area { h: 972.0, ..screen }, &[]);
    let mut w = World::new(safe.final_luma_safe_area, 0.0, 42);
    w.set_spawn_environment(safe, (-9999.0, -9999.0), Some(vec![]));
    w.spawn_runtime.calendar = Box::new(clock.clone());
    w.spawn_runtime.provider = Box::new(FixtureProvider);
    let bytes = std::fs::read(format!(
        "{}/../public/assets/monsters/{}/base.png",
        env!("CARGO_MANIFEST_DIR"),
        code.to_lowercase()
    ))
    .unwrap();
    assert_eq!(bytes, approved(code));
    assert_eq!(definition(code)["assetIdentity"], code.to_lowercase());
    w.spawn_runtime.available_assets.insert(code.into()); // validated real asset; test-only readiness
    let m = FixtureProvider.identity(code).unwrap();
    let date = *clock.value.lock().unwrap();
    let e = Encounter {
        encounter_id: uuid::Uuid::from_u128(id),
        monster: crate::backend::Monster {
            code: code.into(),
            name: code.into(),
            level: 2,
            rarity: m.rarity,
            movement_profile: serde_json::to_value(m.movement_profile)
                .unwrap()
                .as_str()
                .unwrap()
                .into(),
        },
        spawned_at: date.with_timezone(&chrono::Utc),
        expires_at: (date + chrono::Duration::seconds(120)).with_timezone(&chrono::Utc),
        battle_id: None,
        expiration_suspended: false,
    };
    (w, e)
}
const CODES: [&str; 5] = ["SHADE", "EMBER", "LUNET", "NOVA", "NOCT"];
fn approved(code: &str) -> &'static [u8] {
    match code {
        "SHADE" => include_bytes!("../../../../public/assets/monsters/shade/base.png"),
        "EMBER" => include_bytes!("../../../../public/assets/monsters/ember/base.png"),
        "LUNET" => include_bytes!("../../../../public/assets/monsters/lunet/base.png"),
        "NOVA" => include_bytes!("../../../../public/assets/monsters/nova/base.png"),
        "NOCT" => include_bytes!("../../../../public/assets/monsters/noct/base.png"),
        _ => panic!("not a Batch3 fixture"),
    }
}
fn motion(w: &mut World, code: &str) {
    let start = w.view.pip.as_ref().unwrap().clone();
    let (mut dx, mut dy) = (false, false);
    for i in 1..=80 {
        w.tick(f64::from(i) * 0.1, 0.1, (-9999., -9999.), false);
        let p = w.view.pip.as_ref().unwrap();
        let a = w.area;
        let b = p.size.bounds(p.x, p.y);
        assert!(b.x >= a.x + 8. - 1e-6 && b.x + b.w <= a.x + a.w - 8. + 1e-6);
        assert!(b.y >= a.ground_y() - 1e-6 && b.y + b.h <= a.y + a.h - 8. + 1e-6);
        dx |= (p.x - start.x).abs() > 1.;
        dy |= (p.y - start.y).abs() > 1.;
        if ["SHADE", "NOCT"].contains(&code) {
            assert!((p.x - start.x).abs() < 1e-6);
        }
    }
    assert!(dy, "{code} vertical movement");
    if ["EMBER", "NOVA"].contains(&code) {
        assert!(dx, "{code} horizontal movement");
    }
}
#[test]
fn batch3_assets_metadata_motion_night_and_restart() {
    for (code, rarity, profile, zone, condition) in [
        ("SHADE", "UNCOMMON", "EDGE", "EDGE", "NIGHT"),
        ("EMBER", "RARE", "FREE_2D", "FREE_AREA", "ANY_TIME"),
        ("LUNET", "RARE", "FLOATING", "FREE_AREA", "NIGHT"),
        ("NOVA", "RARE", "FREE_2D", "FREE_AREA", "ANY_TIME"),
        ("NOCT", "SPECIAL", "EDGE", "EDGE", "NIGHT"),
    ] {
        let d = definition(code);
        for (key, value) in [
            ("rarity", rarity),
            ("movementProfile", profile),
            ("spawnProfile", zone),
            ("spawnCondition", condition),
        ] {
            assert_eq!(d[key], value);
        }
        assert_eq!(d["enabled"], false);
        assert_eq!(d["contentReady"], false);
        assert_eq!(d["productionStatus"], "PROVISIONAL");
        assert!(ContentProvider.candidate(code).is_none());
        assert!(ContentProvider.identity(code).is_none());
        for (h, m, night) in [(21, 59, false), (22, 0, true), (5, 59, true), (6, 0, false)] {
            let clock = FakeClock::at(h, m);
            let (mut w, e) = fixture(code, &clock, 8);
            w.apply_server_encounter(0., Some(e.clone()), 120.);
            let allowed = condition == "ANY_TIME" || night;
            assert_eq!(w.view.pip.is_some(), allowed, "{code} {h}:{m}");
            assert_eq!(!w.view.dex.discovered_codes.is_empty(), allowed);
            if allowed {
                motion(&mut w, code);
                let (mut restored, _) = fixture(code, &clock, 8);
                assert_eq!(restored.spawn_action(0.), Some(Action::Reconcile));
                restored.complete_spawn(0., Action::Reconcile, Ok(Some(e.clone())));
                assert_eq!(
                    restored.view.monster.as_ref().unwrap().encounter_id,
                    Some(e.encounter_id)
                );
                assert!(restored.spawn_action(1.).is_none());
            } else {
                assert_eq!(w.spawn_action(0.), Some(Action::Resolve(e.encounter_id)));
            }
        }
    }
}
#[test]
fn batch3_both_edges_and_fail_closed_per_species() {
    for code in CODES {
        let clock = FakeClock::at(23, 0);
        if ["SHADE", "NOCT"].contains(&code) {
            for (seed, right) in [(8, false), (9, true)] {
                let (mut w, e) = fixture(code, &clock, seed);
                w.apply_server_encounter(0., Some(e), 120.);
                let p = w.view.pip.as_ref().unwrap();
                let b = p.size.bounds(p.x, p.y);
                assert_eq!(
                    if right { b.x + b.w } else { b.x },
                    if right {
                        w.area.x + w.area.w - 8.
                    } else {
                        w.area.x + 8.
                    }
                );
                motion(&mut w, code);
            }
        }
        for failure in [
            "asset",
            "rarity",
            "movement",
            "name",
            "windows",
            "production",
        ] {
            let (mut w, mut e) = fixture(code, &clock, 8);
            match failure {
                "asset" => w.spawn_runtime.available_assets.clear(),
                "rarity" => e.monster.rarity = "COMMON".into(),
                "movement" => e.monster.movement_profile = "UNKNOWN".into(),
                "name" => e.monster.name = "PIP".into(),
                "windows" => {
                    let a = w.area;
                    let safe = SafeAreaTracker::default().update(1, a, a, &[]);
                    w.set_spawn_environment(safe, (-9999., -9999.), None);
                }
                "production" => w.spawn_runtime.provider = Box::new(ContentProvider),
                _ => unreachable!(),
            }
            w.apply_server_encounter(0., Some(e), 120.);
            assert!(w.view.pip.is_none(), "{code} {failure}");
            assert!(w.view.dex.discovered_codes.is_empty());
        }
    }
}
#[test]
#[ignore = "launched by Batch3PreparationTest with LUMA_BATCH3_LIVE=1 and isolated test DB"]
fn live_batch3_fixture() {
    let code = std::env::var("LUMA_BATCH3_CODE").unwrap();
    assert!(CODES.contains(&code.as_str()));
    let api = crate::backend::Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    let e = api.encounter(false).unwrap().unwrap();
    assert_eq!(e.monster.code, code);
    // Fixed local night with current server date; authoritative remaining lease stays explicit.
    let clock = FakeClock::at(23, 0);
    let (mut w, _) = fixture(&code, &clock, 8);
    w.apply_server_encounter(0., Some(e.clone()), 60.);
    motion(&mut w, &code);
    let (mut restored, _) = fixture(&code, &clock, 8);
    let fetched = api.encounter(false).unwrap().unwrap();
    assert_eq!(fetched.encounter_id, e.encounter_id);
    restored.apply_server_encounter(0., Some(fetched), 60.);
    assert_eq!(
        restored.view.monster.as_ref().unwrap().encounter_id,
        Some(e.encounter_id)
    );
    let b = api.battle(e.encounter_id, Some("start")).unwrap();
    restored.apply_battle(b.clone());
    let hit = api.battle(b.battle_id, Some("attack")).unwrap();
    assert_eq!(hit.monster.hp, 18);
    restored.apply_battle(hit);
    let c = api.capture(b.battle_id).unwrap();
    assert!(c.success);
    assert_eq!(c.collection.as_ref().unwrap().monster_code, code);
    restored.view.dex.loaded(api.collection().unwrap());
    restored.apply_battle(c.battle);
    restored.apply_server_encounter(2., api.encounter(false).unwrap(), 0.);
    restored.tick(3., 0.1, (-9999., -9999.), false);
    assert!(restored.view.pip.is_none());
    assert_eq!(
        restored.spawn_runtime.director.state(),
        SpawnState::Cooldown
    );
    eprintln!("BATCH3 LIVE PASS {code}: real asset/spawn/motion/restart/battle/capture/collection/cooldown");
}
