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
            let before = w.view.pip.as_ref().unwrap().clone();
            w.tick(t, 1. / 30., FAR, false);
            let after = w.view.pip.as_ref().unwrap();
            let vx = (after.x - before.x) * 30.;
            if before.state == PipState::Roaming {
                let expected = if vx > 3. {
                    1
                } else if vx < -3. {
                    -1
                } else {
                    before.facing
                };
                assert_eq!(after.facing, expected, "{code} vx={vx}");
            }
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

#[test]
fn rarity_arrival_holds_behavior_preserves_identity_and_yields_to_battle() {
    for code in [
        "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP", "SHADE",
        "EMBER", "LUNET", "NOVA", "NOCT",
    ] {
        let mut w = world(code);
        let id = w.view.monster.as_ref().unwrap().clone();
        let hold = crate::presentation::spawn::hold_seconds(&id.rarity);
        assert!((0.6..=1.0).contains(&hold));
        let p = w.view.pip.as_ref().unwrap();
        let start = (p.x, p.y);
        w.tick(hold - 0.001, 0.1, FAR, false);
        let p = w.view.pip.as_ref().unwrap();
        assert_eq!(p.state, PipState::Spawning);
        assert_eq!((p.x, p.y), start);
        w.tick(hold, 0.001, FAR, false);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Roaming);
        assert_eq!(
            w.view.monster.as_ref().unwrap().encounter_id,
            id.encounter_id
        );
        for at in [0.1, hold + 0.1] {
            let mut b = world(code);
            b.tick(at, 0.1, FAR, false);
            battle(&mut b, crate::backend::battle::Status::Active, "ACTIVE");
            b.tick(at + 0.1, 0.1, FAR, false);
            assert_eq!(
                b.view.monster.as_ref().unwrap().encounter_id,
                id.encounter_id
            );
            battle(&mut b, crate::backend::battle::Status::Captured, "CAPTURED");
            b.apply_server_encounter(at + 0.2, None, 0.);
            b.tick(at + 2., 0.1, FAR, false);
            assert!(b.view.pip.is_none());
        }
    }
}

#[test]
fn server_monster_facing_follows_accepted_motion_for_all_profiles() {
    use crate::movement::FACING_SPEED_EPSILON;
    for (code, profile) in [
        ("PIP", MovementProfile::Ground),
        ("MELLO", MovementProfile::Jump),
        ("CHIRP", MovementProfile::Flying),
        ("PUFF", MovementProfile::Floating),
        ("SHADE", MovementProfile::Edge),
        ("EMBER", MovementProfile::Free2d),
        ("NOVA", MovementProfile::Free2d),
        ("MIMI", MovementProfile::Static),
    ] {
        let mut w = world(code);
        assert_eq!(w.view.monster.as_ref().unwrap().movement_profile, profile);
        w.view.pip.as_mut().unwrap().state = PipState::Roaming;
        w.monster_behavior.as_mut().unwrap().hold(true); // deterministic test-only decision freeze
        w.monster_behavior.as_mut().unwrap().current.speed = 20.;
        let area = w.area;
        let size = w.view.pip.as_ref().unwrap().size;
        let start = match profile {
            MovementProfile::Flying => area.clamp(-1800., f64::MAX, size),
            MovementProfile::Edge => area.clamp(f64::MIN, area.ground_y() + 80., size),
            MovementProfile::Floating => (-1800., area.ground_y() + 80.),
            _ => area.ground(-1800., size),
        };
        {
            let p = w.view.pip.as_mut().unwrap();
            p.x = start.0;
            p.y = start.1;
            p.facing = -1;
        }
        let mut seen = std::collections::BTreeSet::new();
        let mut now = 1.;
        for sign in [1., -1., 1., -1.] {
            let p = w.view.pip.as_ref().unwrap();
            let from = (p.x, p.y);
            w.monster_movement.start_ambient(
                profile,
                crate::monster_behavior::Decision {
                    intent: Intent::Wander,
                    direction: sign,
                    distance: 40.,
                    speed: 20.,
                },
                from,
                None,
                crate::movement::ambient::Environment {
                    area,
                    size,
                    cursor: FAR,
                    windows: Some(&[]),
                },
            );
            for _ in 0..65 {
                let before = w.view.pip.as_ref().unwrap().clone();
                now += 0.05;
                w.tick(now, 0.05, FAR, false);
                let after = w.view.pip.as_ref().unwrap();
                let vx = (after.x - before.x) / 0.05;
                let expected = if vx > FACING_SPEED_EPSILON {
                    1
                } else if vx < -FACING_SPEED_EPSILON {
                    -1
                } else {
                    before.facing
                };
                assert_eq!(after.facing, expected, "{profile:?} vx={vx}");
                if vx.abs() > FACING_SPEED_EPSILON {
                    seen.insert(after.facing);
                }
                if matches!(profile, MovementProfile::Static | MovementProfile::Edge) {
                    assert_eq!(after.facing, -1);
                }
            }
        }
        if !matches!(profile, MovementProfile::Static | MovementProfile::Edge) {
            assert_eq!(seen, [-1, 1].into_iter().collect(), "{profile:?}");
        }
        // Locked and stationary motion cannot reset a RIGHT-facing monster.
        w.view.pip.as_mut().unwrap().facing = 1;
        w.view.menu = true;
        for _ in 0..10 {
            now += 0.05;
            w.tick(now, 0.05, FAR, false);
            assert_eq!(w.view.pip.as_ref().unwrap().facing, 1);
        }
    }
}

#[test]
fn floating_batch_timid_avoidance_emits_active_completion_and_native_facing() {
    for code in ["WISP", "LUNET"] {
        let mut w = world(code); // LUNET uses the existing test-only NIGHT calendar.
        assert_eq!(w.monster_behavior.as_ref().unwrap().profile, Profile::Timid);
        assert_eq!(
            w.view.monster.as_ref().unwrap().movement_profile,
            MovementProfile::Floating
        );
        w.view.pip.as_mut().unwrap().state = PipState::Roaming;
        w.monster_behavior.as_mut().unwrap().hold(true);
        w.monster_behavior.as_mut().unwrap().current.speed = 20.;
        let area = w.area;
        let size = w.view.pip.as_ref().unwrap().size;
        let mut now = 1.;
        for sign in [1., -1.] {
            let from = (-1800., area.ground_y() + 80.);
            {
                let p = w.view.pip.as_mut().unwrap();
                p.x = from.0;
                p.y = from.1;
            }
            w.monster_movement.start_ambient(
                MovementProfile::Floating,
                crate::monster_behavior::Decision {
                    intent: Intent::AvoidCompanion,
                    direction: sign,
                    distance: 40.,
                    speed: 20.,
                },
                from,
                Some((from.0 - sign * 100., from.1)),
                crate::movement::ambient::Environment {
                    area,
                    size,
                    cursor: FAR,
                    windows: Some(&[]),
                },
            );
            let mut active = false;
            let mut moving = false;
            for _ in 0..70 {
                now += 0.05;
                w.tick(now, 0.05, FAR, false);
                let sample = w.view.animation.floating.as_ref().unwrap();
                active |= sample.active;
                if sample.vx.abs() > crate::movement::FACING_SPEED_EPSILON {
                    moving = true;
                    assert_eq!(sample.facing, sign as i8, "{code}");
                    assert_eq!(w.view.pip.as_ref().unwrap().facing, sample.facing);
                }
                inside(&w);
            }
            assert!(active && moving, "{code}");
            assert!(
                !w.view.animation.floating.as_ref().unwrap().active,
                "{code} completion"
            );
        }
    }
}

#[test]
fn noct_edge_batch_timid_avoidance_boundary_reversal_and_facing_retention() {
    for side in [f64::MIN, f64::MAX] {
        let mut w = world("NOCT"); // Existing NIGHT eligibility remains domain-owned.
        assert_eq!(w.monster_behavior.as_ref().unwrap().profile, Profile::Timid);
        assert_eq!(
            w.view.monster.as_ref().unwrap().movement_profile,
            MovementProfile::Edge
        );
        w.view.pip.as_mut().unwrap().state = PipState::Roaming;
        w.monster_behavior.as_mut().unwrap().hold(true);
        w.monster_behavior.as_mut().unwrap().current.speed = 20.;
        let area = w.area;
        let size = w.view.pip.as_ref().unwrap().size;
        let mut now = 1.;
        for (intent, y, sign, expected) in [
            (Intent::AvoidCompanion, area.ground_y() + 80., 1., 1.),
            (Intent::AvoidCompanion, area.ground_y() + 80., -1., -1.),
            (Intent::Wander, f64::MAX, 1., -1.),
            (Intent::Wander, f64::MIN, -1., 1.),
        ] {
            let from = area.clamp(side, y, size);
            {
                let p = w.view.pip.as_mut().unwrap();
                p.x = from.0;
                p.y = from.1;
                p.facing = if side < 0. { -1 } else { 1 };
            }
            let facing = w.view.pip.as_ref().unwrap().facing;
            w.monster_movement.start_ambient(
                MovementProfile::Edge,
                crate::monster_behavior::Decision {
                    intent,
                    direction: sign,
                    distance: 40.,
                    speed: 20.,
                },
                from,
                Some((from.0, from.1 - sign * 100.)),
                crate::movement::ambient::Environment {
                    area,
                    size,
                    cursor: FAR,
                    windows: Some(&[]),
                },
            );
            let mut moved = false;
            let mut measured_speed = 0.;
            for _ in 0..70 {
                let before = w.view.pip.as_ref().map(|p| (p.x, p.y)).unwrap();
                now += 0.05;
                w.tick(now, 0.05, FAR, false);
                let p = w.view.pip.as_ref().unwrap();
                assert_eq!(p.x, from.0);
                assert_eq!(p.facing, facing);
                // Same read-only accepted-displacement adapter used by main.rs.
                measured_speed =
                    crate::presentation::animation::speed(before, (p.x, p.y), 0.05, measured_speed);
                moved |= measured_speed >= 8.;
                inside(&w);
            }
            assert!(moved, "{intent:?}");
            assert!(
                (w.view.pip.as_ref().unwrap().y - from.1) * expected > 0.,
                "{intent:?}"
            );
            assert_eq!(w.monster_movement.profile(), None);
            assert_eq!(measured_speed, 0.);
        }
    }
}

#[test]
fn ground_batch_consumers_keep_profiles_ground_facing_and_pause() {
    for (code, profile, speed, intent) in [
        ("MOSSY", Profile::Sleepy, 8., Intent::Wander),
        ("PEBB", Profile::Passive, 10., Intent::Wander),
        ("TIKKI", Profile::Curious, 14., Intent::ApproachCompanion),
    ] {
        let mut w = world(code);
        assert_eq!(w.monster_behavior.as_ref().unwrap().profile, profile);
        assert_eq!(
            w.view.monster.as_ref().unwrap().movement_profile,
            MovementProfile::Ground
        );
        w.view.pip.as_mut().unwrap().state = PipState::Roaming;
        w.monster_behavior.as_mut().unwrap().hold(true);
        w.monster_behavior.as_mut().unwrap().current.speed = speed;
        let area = w.area;
        let size = w.view.pip.as_ref().unwrap().size;
        let mut now = 1.;
        for sign in [1., -1.] {
            let from = area.ground(-1800., size);
            {
                let p = w.view.pip.as_mut().unwrap();
                p.x = from.0;
                p.y = from.1;
            }
            w.monster_movement.start_ambient(
                MovementProfile::Ground,
                crate::monster_behavior::Decision {
                    intent,
                    direction: sign,
                    distance: 24.,
                    speed,
                },
                from,
                Some((from.0 + sign * 600., from.1)),
                crate::movement::ambient::Environment {
                    area,
                    size,
                    cursor: FAR,
                    windows: Some(&[]),
                },
            );
            let mut moved = false;
            for _ in 0..100 {
                let before = w.view.pip.as_ref().unwrap().clone();
                now += 0.05;
                w.tick(now, 0.05, FAR, false);
                let p = w.view.pip.as_ref().unwrap();
                assert_eq!(p.y, from.1);
                if (p.x - before.x).abs() / 0.05 > crate::movement::FACING_SPEED_EPSILON {
                    moved = true;
                    assert_eq!(p.facing, sign as i8);
                }
                inside(&w);
            }
            assert!(moved, "{code}");
            assert_eq!(w.monster_movement.profile(), None);
            let stopped = w.view.pip.as_ref().unwrap().clone();
            now += 0.05;
            w.tick(now, 0.05, FAR, false);
            let p = w.view.pip.as_ref().unwrap();
            assert_eq!((p.x, p.y, p.facing), (stopped.x, stopped.y, stopped.facing));
        }
    }
}

#[test]
fn bubu_jump_batch_playful_short_burst_native_phases_ground_and_facing() {
    for code in ["MELLO", "BUBU"] {
        let mut w = world(code);
        if code == "BUBU" {
            assert_eq!(
                w.monster_behavior.as_ref().unwrap().profile,
                Profile::Playful
            );
        }
        assert_eq!(
            w.view.monster.as_ref().unwrap().movement_profile,
            MovementProfile::Jump
        );
        w.view.pip.as_mut().unwrap().state = PipState::Roaming;
        w.monster_behavior.as_mut().unwrap().hold(true);
        w.monster_behavior.as_mut().unwrap().current.speed = 24.;
        let area = w.area;
        let size = w.view.pip.as_ref().unwrap().size;
        let mut now = 1.;
        for sign in [1., -1., 0.] {
            let from = area.ground(-1800., size);
            {
                let p = w.view.pip.as_mut().unwrap();
                p.x = from.0;
                p.y = from.1;
                p.facing = -1;
            }
            w.monster_movement.start_ambient(
                MovementProfile::Jump,
                crate::monster_behavior::Decision {
                    intent: Intent::ShortBurst,
                    direction: sign,
                    distance: 40.,
                    speed: 24.,
                },
                from,
                None,
                crate::movement::ambient::Environment {
                    area,
                    size,
                    cursor: FAR,
                    windows: Some(&[]),
                },
            );
            let mut phases = std::collections::BTreeSet::new();
            let mut last_progress = 0.;
            for _ in 0..50 {
                now += 0.05;
                w.tick(now, 0.05, FAR, false);
                let p = w.view.pip.as_ref().unwrap();
                if sign == 0. {
                    assert_eq!(p.facing, -1);
                }
                if let Some(s) = w.view.animation.jump {
                    assert!(s.progress >= last_progress);
                    last_progress = s.progress;
                    phases.insert(s.phase);
                    assert_eq!((s.x, s.y), (p.x, p.y));
                    if s.vx.abs() > crate::movement::FACING_SPEED_EPSILON {
                        assert_eq!(s.facing, sign as i8);
                    }
                    assert_eq!(s.phase == "LAND", s.grounded);
                    if s.grounded {
                        assert_eq!(p.y, from.1);
                        assert_eq!(s.phase, "LAND");
                    }
                    if (0.45..=0.55).contains(&s.progress) {
                        assert_eq!(s.phase, "APEX");
                    }
                    if s.phase == "DESCEND" {
                        assert!(!s.grounded);
                        assert!(p.y > from.1);
                    }
                }
                inside(&w);
            }
            assert_eq!(
                phases,
                ["LAUNCH", "ASCEND", "APEX", "DESCEND", "LAND"]
                    .into_iter()
                    .collect()
            );
            assert_eq!(w.view.pip.as_ref().unwrap().y, from.1);
            assert!(w.view.animation.jump.is_none());
        }
    }
}

#[test]
fn bubu_jump_batch_uses_existing_apex_band_boundaries() {
    for (p, phase) in [
        (0.449, "ASCEND"),
        (0.45, "APEX"),
        (0.5, "APEX"),
        (0.55, "APEX"),
        (0.551, "DESCEND"),
    ] {
        assert_eq!(
            crate::movement::jump::sample(p, 16., 1., (10., 10.), 0.).phase,
            phase
        );
    }
    assert_ne!(
        crate::movement::jump::sample(1., 16., 1., (10., 10.), 0.).phase,
        "LAND"
    );
    assert_eq!(
        crate::movement::jump::sample(1., 16., 1., (10., 0.), 0.).phase,
        "LAND"
    );
}
