//! Final Batch3 acceptance uses production provider/assets; only local time/environment are injected.
use super::*;
use crate::{behaviors::World, desktop::SafeAreaTracker, geometry::Area};
use chrono::{DateTime, FixedOffset, Timelike};
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
fn definition(code: &str) -> serde_json::Value {
    let records: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("../../../../src/entities/monster-dex.json")).unwrap();
    records
        .into_iter()
        .find(|m| m["monsterCode"] == code)
        .unwrap()
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
    w.spawn_runtime.load_assets(|path| {
        std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../public")
                .join(path),
        )
        .ok()
    });
    assert!(w.spawn_runtime.available_assets.contains(code));
    assert_eq!(definition(code)["assetIdentity"], code.to_lowercase());
    let m = ContentProvider.identity(code).unwrap();
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
fn motion(w: &mut World, code: &str) {
    let start = w.view.pip.as_ref().unwrap().clone();
    for i in 1..=80 {
        w.tick(f64::from(i) * 0.1, 0.1, (-9999., -9999.), false);
        let p = w.view.pip.as_ref().unwrap();
        let a = w.area;
        let b = p.size.bounds(p.x, p.y);
        assert!(b.x >= a.x + 8. - 1e-6 && b.x + b.w <= a.x + a.w - 8. + 1e-6);
        assert!(b.y >= a.ground_y() - 1e-6 && b.y + b.h <= a.y + a.h - 8. + 1e-6);
        if ["SHADE", "NOCT"].contains(&code) {
            assert!((p.x - start.x).abs() < 1e-6);
        }
    }
    // Missing Companion safely permits idle; actual behavior traces cover scheduled motion.
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
        assert_eq!(d["enabled"], true);
        assert_eq!(d["contentReady"], true);
        assert_eq!(d["productionStatus"], "PRODUCTION");
        assert!(ContentProvider.candidate(code).is_some());
        assert!(ContentProvider.identity(code).is_some());
        for (h, m, night) in [
            (21, 59, false),
            (22, 0, true),
            (23, 59, true),
            (0, 0, true),
            (5, 59, true),
            (6, 0, false),
        ] {
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
        for failure in ["asset", "rarity", "movement", "name", "windows", "unknown"] {
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
                "unknown" => e.monster.code = "MONSTER_005".into(),
                _ => unreachable!(),
            }
            w.apply_server_encounter(0., Some(e), 120.);
            assert!(w.view.pip.is_none(), "{code} {failure}");
            assert!(w.view.dex.discovered_codes.is_empty());
        }
    }
}
#[test]
fn daytime_night_restore_resolves_same_id_without_create_spam() {
    for code in ["SHADE", "LUNET", "NOCT"] {
        let night = FakeClock::at(23, 0);
        let (mut active, e) = fixture(code, &night, 8);
        active.apply_server_encounter(0., Some(e.clone()), 120.);
        assert!(active.view.pip.is_some());
        let day = FakeClock::at(12, 0);
        // Same live UTC lease, local noon after a timezone change during restart.
        *day.value.lock().unwrap() = night
            .value
            .lock()
            .unwrap()
            .with_timezone(&FixedOffset::west_opt(2 * 3600).unwrap());
        let (mut restored, _) = fixture(code, &day, 8);
        assert_eq!(restored.spawn_action(0.), Some(Action::Reconcile));
        restored.complete_spawn(0., Action::Reconcile, Ok(Some(e.clone())));
        assert!(restored.view.pip.is_none());
        assert!(restored.view.dex.discovered_codes.is_empty());
        let action = Action::Resolve(e.encounter_id);
        assert_eq!(restored.spawn_action(0.), Some(action));
        restored.complete_spawn(0., action, Err("offline".into()));
        for i in 1..1000 {
            assert!(restored.spawn_action(f64::from(i) * 0.004).is_none());
        }
        assert_eq!(restored.spawn_action(5.), Some(action));
        restored.complete_spawn(5., action, Ok(None));
        assert_eq!(
            restored.spawn_runtime.director.state(),
            SpawnState::Cooldown
        );
        assert!(restored.spawn_action(6.).is_none());
    }
}
fn live_night() -> FakeClock {
    let clock = FakeClock::at(23, 0);
    let now = chrono::Utc::now();
    // Preserve the actual UTC instant/lease while injecting a local timezone whose hour is23.
    let hours = (23 - now.hour() as i32 + 12) % 24 - 12;
    *clock.value.lock().unwrap() = now.with_timezone(&FixedOffset::east_opt(hours * 3600).unwrap());
    clock
}
#[test]
#[ignore = "requires isolated test-only LUMA_TEST_BATCH3 Spring server and fresh DB"]
fn live_batch3_production() {
    let api = crate::backend::Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    assert!(api.encounter(false).unwrap().is_none());
    for code in CODES {
        let clock = live_night();
        let (mut w, _) = fixture(code, &clock, 8);
        assert_eq!(w.spawn_action(0.), Some(Action::Reconcile));
        w.complete_spawn(0., Action::Reconcile, Ok(api.encounter(false).unwrap()));
        let t = w.spawn_runtime.director.next_spawn_at().as_secs_f64();
        assert!(w.spawn_action(t).is_none());
        assert_eq!(w.spawn_action(t), Some(Action::Create));
        let e = api.encounter(true).unwrap().unwrap();
        assert_eq!(e.monster.code, code);
        let (mut w, _) = fixture(code, &clock, 8);
        assert_eq!(w.spawn_action(0.), Some(Action::Reconcile));
        w.complete_spawn(0., Action::Reconcile, Ok(Some(e.clone())));
        assert_eq!(w.view.dex.discovered_codes, vec![code]);
        let identity = w.view.monster.as_ref().unwrap();
        assert_eq!(identity.asset_identity, code.to_lowercase());
        assert_eq!(identity.rarity, e.monster.rarity);
        motion(&mut w, code);
        let (mut restored, _) = fixture(code, &clock, 8);
        assert_eq!(restored.spawn_action(0.), Some(Action::Reconcile));
        restored.complete_spawn(0., Action::Reconcile, Ok(api.encounter(false).unwrap()));
        assert_eq!(
            restored.view.monster.as_ref().unwrap().encounter_id,
            Some(e.encounter_id)
        );
        assert!(restored.spawn_action(1.).is_none());
        let b = api.battle(e.encounter_id, Some("start")).unwrap();
        restored.apply_battle(b.clone());
        let hit = api.battle(b.battle_id, Some("attack")).unwrap();
        assert_eq!(hit.monster.hp, 18);
        restored.apply_battle(hit);
        for item in ["SMALL_POTION", "CAPTURE_CHARM"] {
            api.purchase(item, 1).unwrap();
        }
        let potion = api.use_item("SMALL_POTION", Some(b.battle_id)).unwrap();
        assert_eq!(potion.healed_amount, Some(5));
        let charm = api.use_item("CAPTURE_CHARM", Some(b.battle_id)).unwrap();
        assert_eq!(charm.armed, Some(true));
        let c = api.capture(b.battle_id).unwrap();
        assert!(c.success);
        let base = definition(code)["baseCaptureRate"].as_f64().unwrap();
        assert!((c.base_chance.unwrap() - (base + 0.2)).abs() < 1e-9);
        assert_eq!(c.item_bonus, Some(0.1));
        assert!((c.final_chance.unwrap() - (base + 0.3)).abs() < 1e-9);
        let row = c.collection.as_ref().unwrap();
        assert_eq!(row.monster_code, code);
        assert_eq!(row.capture_count, 1);
        assert!(row.first_captured_at <= row.last_captured_at);
        restored.view.dex.loaded(api.collection().unwrap());
        restored.view.dex.captured(row);
        restored.apply_battle(c.battle);
        restored.apply_server_encounter(2., api.encounter(false).unwrap(), 0.);
        restored.tick(3., 0.1, (-9999., -9999.), false);
        assert!(restored.view.pip.is_none());
        assert_eq!(
            restored.spawn_runtime.director.state(),
            SpawnState::Cooldown
        );
        assert!(restored.spawn_action(3.).is_none());
        eprintln!("BATCH3 PRODUCTION LIVE PASS {code}: POST/asset/condition/movement/restore/battle/hit/potion/charm/capture/collection/cooldown id={}",e.encounter_id);
    }
    let records = api.collection().unwrap();
    assert_eq!(records.len(), 5);
    assert!(CODES.iter().all(|code| records
        .iter()
        .any(|r| r.monster_code == *code && r.capture_count == 1)));
    if let Ok(path) = std::env::var("LUMA_TEST_BATCH3_COLLECTION_OUTPUT") {
        std::fs::write(path, serde_json::to_vec(&records).unwrap()).unwrap();
    }
}
