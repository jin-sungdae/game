use super::*;
use crate::{
    monster_behavior::{Intent, Profile},
    movement::MovementProfile,
};
const FAR: (f64, f64) = (-9999., -9999.);
fn world(code: &str) -> World {
    let screen = Area {
        x: -3000.,
        y: -1000.,
        w: 2600.,
        h: 1200.,
    };
    let safe = crate::desktop::SafeAreaTracker::default().update(
        1,
        screen,
        Area { h: 1172., ..screen },
        &[],
    );
    let mut w = World::new(safe.final_luma_safe_area, 0., 42);
    w.set_spawn_environment(safe, FAR, Some(vec![]));
    w.spawn_runtime.load_assets(|p| {
        std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../public")
                .join(p),
        )
        .ok()
    });
    // Use the existing placement authority; NIGHT snapshots injected through test-only calendar.
    struct Night;
    impl crate::spawn::conditions::CalendarClock for Night {
        fn local_now(&self) -> chrono::DateTime<chrono::FixedOffset> {
            chrono::DateTime::parse_from_rfc3339("2026-09-22T23:00:00+09:00").unwrap()
        }
    }
    w.spawn_runtime.set_test_calendar(Box::new(Night));
    let id = crate::spawn::identity(code).unwrap();
    let now = chrono::Utc::now();
    let e = crate::backend::Encounter {
        encounter_id: uuid::Uuid::from_u128(8),
        monster: crate::backend::Monster {
            code: code.into(),
            name: code.into(),
            rarity: id.rarity,
            level: 1,
            movement_profile: serde_json::to_value(id.movement_profile)
                .unwrap()
                .as_str()
                .unwrap()
                .into(),
        },
        spawned_at: now,
        expires_at: now + chrono::Duration::seconds(120),
        battle_id: None,
        expiration_suspended: false,
    };
    w.apply_server_encounter(0., Some(e), 120.);
    w.view.identity = Some(crate::backend::Companion {
        player_companion_id: 1,
        species: "MOA".into(),
        evolution_stage: 1,
        evolution_name: "MOA".into(),
        level: 1,
        exp: 0,
        bond: 0,
    });
    w
}
fn inside(w: &World) {
    let p = w.view.pip.as_ref().unwrap();
    let b = p.size.bounds(p.x, p.y);
    let a = w.area;
    assert!(b.x >= a.x + 8. - 1e-6 && b.x + b.w <= a.x + a.w - 8. + 1e-6);
    assert!(b.y >= a.ground_y() - 1e-6 && b.y + b.h <= a.y + a.h - 8. + 1e-6);
}
#[test]
fn all_fifteen_world_traces_preserve_identity_constraints_and_companion() {
    let codes = [
        "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP", "SHADE",
        "EMBER", "LUNET", "NOVA", "NOCT",
    ];
    let mut traces = Vec::new();
    for code in codes {
        let mut w = world(code);
        let start = w.view.pip.as_ref().unwrap().clone();
        let mut control = World::new(w.area, 0., 42);
        let id = w.view.monster.as_ref().unwrap().clone();
        let mut rows = Vec::new();
        let mut previous = 0;
        for i in 1..=1800 {
            let t = f64::from(i) / 30.;
            w.tick(t, 1. / 30., FAR, false);
            control.tick(t, 1. / 30., FAR, false);
            inside(&w);
            assert_eq!(
                (w.view.moa.x, w.view.moa.y),
                (control.view.moa.x, control.view.moa.y)
            );
            let p = w.view.pip.as_ref().unwrap();
            match id.movement_profile {
                MovementProfile::Static => assert_eq!((p.x, p.y), (start.x, start.y)),
                MovementProfile::Edge => assert_eq!(p.x, start.x),
                MovementProfile::Ground => assert_eq!(p.y, w.area.ground_y()),
                MovementProfile::Flying => assert!(p.y > w.area.y + w.area.h - 300.),
                _ => {}
            }
            assert!(w.view.game.battle.is_none());
            assert!(!w.view.game.busy);
            assert_eq!(
                w.view.monster.as_ref().unwrap().encounter_id,
                id.encounter_id
            );
            let b = w.monster_behavior.as_ref().unwrap();
            if b.decisions != previous {
                rows.push(serde_json::json!({"t":t,"intent":format!("{:?}",b.current.intent),"x":p.x,"y":p.y}));
                previous = b.decisions;
            }
        }
        assert!(previous <= 30 && previous >= 10, "{code}: {previous}");
        let b = w.monster_behavior.as_ref().unwrap();
        if b.profile == Profile::Sleepy {
            assert_eq!(rows[0]["intent"], "Pause");
        }
        traces.push(serde_json::json!({"species":code,"profile":format!("{:?}",b.profile),"decisions":rows}));
    }
    let representatives = ["MELLO", "WISP", "PIP", "EMBER", "MOSSY", "SHADE", "PEBB"];
    let patterns: std::collections::BTreeSet<_> = traces
        .iter()
        .filter(|r| representatives.contains(&r["species"].as_str().unwrap()))
        .map(|r| {
            r["decisions"]
                .as_array()
                .unwrap()
                .iter()
                .map(|d| d["intent"].as_str().unwrap())
                .collect::<Vec<_>>()
                .join(",")
        })
        .collect();
    assert_eq!(
        patterns.len(),
        7,
        "seven distinct deterministic decision patterns"
    );
    // Replay proof uses actual World paths, not just the RNG unit test.
    let mut a = world("MELLO");
    let mut b = world("MELLO");
    for i in 1..=900 {
        let t = f64::from(i) / 30.;
        a.tick(t, 1. / 30., FAR, false);
        b.tick(t, 1. / 30., FAR, false);
        assert_eq!(
            (
                a.view.pip.as_ref().unwrap().x,
                a.view.pip.as_ref().unwrap().y
            ),
            (
                b.view.pip.as_ref().unwrap().x,
                b.view.pip.as_ref().unwrap().y
            )
        );
    }
    if let Ok(path) = std::env::var("LUMA_BEHAVIOR_TRACE") {
        std::fs::write(path, serde_json::to_vec_pretty(&traces).unwrap()).unwrap();
    }
}
fn battle(w: &mut World, status: crate::backend::battle::Status, encounter_status: &str) {
    use crate::backend::battle::{Battle, Hp};
    w.apply_battle(Battle {
        battle_id: uuid::Uuid::from_u128(7),
        encounter_id: w.view.game.encounter_id.unwrap(),
        turn: 1,
        status,
        encounter_status: encounter_status.into(),
        companion: Hp {
            hp: 100,
            max_hp: 100,
        },
        monster: Hp { hp: 30, max_hp: 30 },
        events: vec![],
        presentation_events: vec![],
        reward: None,
    });
}
#[test]
fn battle_interaction_drag_suspend_resume_terminal_never_resumes() {
    use crate::backend::battle::Status;
    let mut w = world("EMBER");
    w.tick(1., 0.1, FAR, false);
    w.tick(1.1, 0.1, FAR, false);
    let id = w.view.monster.as_ref().unwrap().encounter_id;
    battle(&mut w, Status::Active, "ACTIVE");
    let before = w.view.pip.as_ref().unwrap().clone();
    let n = w.monster_behavior.as_ref().unwrap().decisions;
    for i in 2..10 {
        w.tick(f64::from(i), 0.1, FAR, false);
        assert_eq!(
            (
                w.view.pip.as_ref().unwrap().x,
                w.view.pip.as_ref().unwrap().y
            ),
            (before.x, before.y)
        );
    }
    assert_eq!(w.monster_behavior.as_ref().unwrap().decisions, n);
    battle(&mut w, Status::Victory, "ACTIVE");
    w.tick(10., 0.1, FAR, false);
    w.tick(12., 0.1, FAR, false);
    assert!(w.monster_behavior.as_ref().unwrap().decisions > n);
    for lock in 0..4 {
        let before = w.view.pip.as_ref().unwrap().clone();
        if lock == 0 {
            w.interact();
        }
        if lock == 1 {
            w.view.items.busy = true;
        }
        if lock == 2 {
            w.drag(13., (w.view.moa.x, w.view.moa.y));
        }
        w.tick(14. + f64::from(lock), 0.1, FAR, lock >= 2);
        assert_eq!(
            (
                w.view.pip.as_ref().unwrap().x,
                w.view.pip.as_ref().unwrap().y
            ),
            (before.x, before.y)
        );
        w.close();
        w.view.items.busy = false;
    }
    battle(&mut w, Status::Captured, "CAPTURED");
    let n = w.monster_behavior.as_ref().unwrap().decisions;
    for i in 20..40 {
        w.tick(f64::from(i), 0.1, FAR, false);
    }
    assert_eq!(w.monster_behavior.as_ref().unwrap().decisions, n);
    assert_eq!(w.view.monster.as_ref().unwrap().encounter_id, id);
}
#[test]
fn unavailable_companion_and_cached_obstacles_fail_safe() {
    for code in ["MELLO", "WISP", "PIP", "EMBER", "MOSSY", "SHADE", "PEBB"] {
        let mut w = world(code);
        w.view.identity = None;
        for i in 1..100 {
            w.tick(f64::from(i) * 0.033, 0.033, FAR, false);
            assert!(!matches!(
                w.monster_behavior.as_ref().unwrap().current.intent,
                Intent::ApproachCompanion | Intent::AvoidCompanion
            ));
        }
        w.spawn_environment.as_mut().unwrap().windows = None;
        let p = w.view.pip.as_ref().unwrap().clone();
        for i in 100..500 {
            w.tick(f64::from(i) * 0.033, 0.033, FAR, false);
        }
        assert_eq!(
            (
                w.view.pip.as_ref().unwrap().x,
                w.view.pip.as_ref().unwrap().y
            ),
            (p.x, p.y)
        );
    }
}

#[test]
fn timid_near_avoids_and_reconciliation_preserves_controller() {
    let mut w = world("WISP");
    let companion = (w.view.moa.x, w.view.moa.y);
    // Test-only initial proximity, then all displacement is produced by MovementController.
    let p = w.view.pip.as_mut().unwrap();
    p.x = companion.0 - 120.;
    p.y = companion.1;
    let start = p.x;
    w.tick(1., 0.1, FAR, false);
    w.tick(1.1, 0.1, FAR, false);
    assert_eq!(
        w.monster_behavior.as_ref().unwrap().current.intent,
        Intent::AvoidCompanion
    );
    assert!(w.view.pip.as_ref().unwrap().x < start);
    let n = w.monster_behavior.as_ref().unwrap().decisions;
    let due = w.monster_behavior.as_ref().unwrap().next_decision_at;
    let encounter = w.spawn_runtime.encounter.clone();
    w.apply_server_encounter(1.2, encounter, 100.);
    assert_eq!(w.monster_behavior.as_ref().unwrap().decisions, n);
    assert_eq!(w.monster_behavior.as_ref().unwrap().next_decision_at, due);
}
#[test]
fn curious_jump_lands_before_pausing_in_stop_radius() {
    let mut w = world("MELLO");
    for i in 1..1800 {
        w.tick(f64::from(i) / 30., 1. / 30., FAR, false);
    }
    assert_eq!(
        w.monster_behavior.as_ref().unwrap().current.intent,
        Intent::Pause
    );
    assert!((w.view.pip.as_ref().unwrap().y - w.area.ground_y()).abs() < 1e-6);
}
