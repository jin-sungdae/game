//! Test-only in-memory metadata/assets. Never toggles production content or writes PNGs/DB.
use super::*;
use crate::{behaviors::World, desktop::SafeAreaTracker, geometry::Area};
use chrono::{DateTime, FixedOffset, NaiveTime};
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
    fn set(&self, hour: u32, minute: u32) {
        *self.value.lock().unwrap() = *Self::at(hour, minute).value.lock().unwrap();
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
    w.spawn_runtime.available_assets.insert(code.into()); // test-only presence, no invented image bytes
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
#[test]
fn local_night_boundaries_and_any_time_no_server_timezone_mixing() {
    for (hour, minute, expected) in [
        (21, 59, false),
        (22, 0, true),
        (23, 59, true),
        (0, 0, true),
        (5, 59, true),
        (6, 0, false),
    ] {
        let clock = FakeClock::at(hour, minute);
        use conditions::CalendarClock;
        let local = clock.local_now();
        assert_eq!(SpawnCondition::Night.eligible(local.time()), expected);
        assert!(SpawnCondition::AnyTime.eligible(local.time()));
        for unsupported in [
            SpawnCondition::Day,
            SpawnCondition::FocusSession,
            SpawnCondition::SpecialEvent,
        ] {
            assert!(!unsupported.eligible(local.time()));
        }
        let (mut w, e) = fixture("SHADE", &clock, 8);
        w.apply_server_encounter(0.0, Some(e.clone()), 120.0);
        assert_eq!(w.view.pip.is_some(), expected);
        if !expected {
            assert_eq!(w.spawn_action(0.0), Some(Action::Resolve(e.encounter_id)));
        }
    }
    // 22:00 +09 is 13:00 UTC: local, not UTC, determines NIGHT.
    assert!(SpawnCondition::Night.eligible(NaiveTime::from_hms_opt(22, 0, 0).unwrap()));
}
#[test]
fn all_advanced_fixtures_route_through_world_with_safe_motion_and_rarity() {
    for code in ["SHADE", "EMBER", "LUNET", "NOVA", "NOCT"] {
        let clock = FakeClock::at(23, 0);
        let (mut w, e) = fixture(code, &clock, 8);
        assert_eq!(w.spawn_action(0.0), Some(Action::Reconcile));
        w.complete_spawn(0.0, Action::Reconcile, Ok(Some(e.clone())));
        let id = w.view.monster.as_ref().unwrap();
        assert_eq!(id.rarity, e.monster.rarity);
        assert_eq!(id.encounter_id, Some(e.encounter_id));
        let start = w.view.pip.as_ref().unwrap().clone();
        for i in 1..=80 {
            w.tick(f64::from(i) * 0.1, 0.1, (-9999.0, -9999.0), false);
            let p = w.view.pip.as_ref().unwrap();
            let b = p.size.bounds(p.x, p.y);
            let a = w.area;
            assert!(
                b.x >= a.x + 8.0 - 1e-6 && b.x + b.w <= a.x + a.w - 8.0 + 1e-6,
                "{code}"
            );
            assert!(
                b.y >= a.ground_y() - 1e-6 && b.y + b.h <= a.y + a.h - 8.0 + 1e-6,
                "{code}"
            );
            if ["SHADE", "NOCT"].contains(&code) {
                assert!((p.x - start.x).abs() < 1e-6);
            }
            assert!(w.spawn_action(f64::from(i) * 0.1).is_none());
        }
        // Safety/profile routing is independent of scheduled personality pauses.
        assert_eq!(
            w.view.monster.as_ref().unwrap().rarity,
            definition(code)["rarity"].as_str().unwrap()
        );
        assert!(
            ContentProvider.candidate(code).is_some(),
            "reviewed final production candidate remains available"
        );
    }
    assert_eq!(definition("NOCT")["rarity"], "SPECIAL");
    assert_eq!(definition("NOCT")["spawnCondition"], "NIGHT");
}
#[test]
fn edge_left_right_and_blocked_side_preserve_full_bounds() {
    let clock = FakeClock::at(23, 0);
    for (seed, right) in [(8, false), (9, true)] {
        let (mut w, e) = fixture("SHADE", &clock, seed);
        w.apply_server_encounter(0.0, Some(e), 120.0);
        let p = w.view.pip.as_ref().unwrap();
        let b = p.size.bounds(p.x, p.y);
        assert_eq!(
            if right { b.x + b.w } else { b.x },
            if right {
                w.area.x + w.area.w - 8.0
            } else {
                w.area.x + 8.0
            }
        );
    }
    let (mut w, e) = fixture("SHADE", &clock, 8);
    let a = w.area;
    let blocked = Area {
        x: a.x,
        y: a.y,
        w: 150.0,
        h: a.h,
    };
    let safe = crate::desktop::DesktopSafeArea {
        screen_frame: a,
        os_visible_frame: a,
        final_luma_safe_area: a,
        detected_dock_bounds: vec![],
        rejected_dock_candidates: 0,
        fallback_safe_insets: Default::default(),
        retained_safe_insets: Default::default(),
    };
    w.set_spawn_environment(safe, (-9999.0, -9999.0), Some(vec![blocked]));
    w.apply_server_encounter(0.0, Some(e), 120.0);
    let p = w.view.pip.as_ref().unwrap();
    assert_eq!(p.size.bounds(p.x, p.y).x + p.size.width, a.x + a.w - 8.0);
    let before = (p.x, p.y);
    for i in 1..=40 {
        w.tick(f64::from(i) * 0.1, 0.1, before, false);
    }
    let p = w.view.pip.as_ref().unwrap();
    assert_eq!((p.x, p.y), before, "cursor blocks advanced motion");
}
#[test]
fn restart_night_restores_same_id_day_resolves_without_new_create_and_backoff() {
    let clock = FakeClock::at(23, 0);
    let (mut first, e) = fixture("LUNET", &clock, 7);
    first.apply_server_encounter(0.0, Some(e.clone()), 120.0);
    let (mut restored, _) = fixture("LUNET", &clock, 7);
    assert_eq!(restored.spawn_action(0.0), Some(Action::Reconcile));
    restored.complete_spawn(0.0, Action::Reconcile, Ok(Some(e.clone())));
    assert_eq!(
        restored.view.monster.as_ref().unwrap().encounter_id,
        Some(e.encounter_id)
    );
    clock.set(6, 0);
    // Already placed encounters retain server authority across dawn, without calendar polling.
    let reads = clock.reads.load(Ordering::Relaxed);
    for _ in 0..1000 {
        restored.tick(1.0, 0.0, (-9999.0, -9999.0), false);
        assert!(restored.spawn_action(1.0).is_none());
    }
    assert_eq!(clock.reads.load(Ordering::Relaxed), reads);
    let (mut daytime, _) = fixture("LUNET", &clock, 7);
    daytime.apply_server_encounter(0.0, Some(e.clone()), 120.0);
    assert!(daytime.view.pip.is_none());
    assert!(daytime.view.dex.discovered_codes.is_empty());
    let action = Action::Resolve(e.encounter_id);
    assert_eq!(daytime.spawn_action(0.0), Some(action));
    daytime.complete_spawn(0.0, action, Err("offline".into()));
    for i in 0..150 {
        assert!(daytime.spawn_action(f64::from(i) * 0.033).is_none());
    }
    assert_eq!(daytime.spawn_action(5.0), Some(action));
    daytime.complete_spawn(5.0, action, Ok(None));
    assert_eq!(daytime.spawn_runtime.director.state(), SpawnState::Cooldown);
}
#[test]
fn metadata_mismatch_and_unknown_windows_fail_closed_without_discovery() {
    let clock = FakeClock::at(23, 0);
    for field in ["rarity", "profile"] {
        let (mut w, mut e) = fixture("NOCT", &clock, 8);
        if field == "rarity" {
            e.monster.rarity = "COMMON".into();
        } else {
            e.monster.movement_profile = "GROUND".into();
        }
        w.apply_server_encounter(0.0, Some(e.clone()), 120.0);
        assert!(w.view.pip.is_none());
        assert_eq!(w.spawn_action(0.0), Some(Action::Resolve(e.encounter_id)));
    }
    let (mut w, e) = fixture("EMBER", &clock, 8);
    let a = w.area;
    w.set_spawn_environment(
        crate::desktop::DesktopSafeArea {
            screen_frame: a,
            os_visible_frame: a,
            final_luma_safe_area: a,
            detected_dock_bounds: vec![],
            rejected_dock_candidates: 0,
            fallback_safe_insets: Default::default(),
            retained_safe_insets: Default::default(),
        },
        (-9999.0, -9999.0),
        None,
    );
    w.apply_server_encounter(0.0, Some(e), 120.0);
    assert!(w.view.pip.is_none());
    assert!(w.view.dex.discovered_codes.is_empty());
}
