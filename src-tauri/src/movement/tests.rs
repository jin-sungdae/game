use super::*;
const SIZE: Size = Size {
    width: 96.0,
    height: 104.0,
};
fn area() -> Area {
    Area {
        x: -1200.0,
        y: -800.0,
        w: 1000.0,
        h: 700.0,
    }
}
fn intent(profile: MovementProfile) -> MovementIntent {
    MovementIntent {
        profile,
        target: (-500.0, -700.0),
        duration: 1.0,
        height: 48.0,
    }
}
fn inside(p: (f64, f64), a: Area, size: Size) {
    let b = size.bounds(p.0, p.1);
    assert!(b.x >= a.x + crate::geometry::LAYOUT.side_margin - 1e-9);
    assert!(b.x + b.w <= a.x + a.w - crate::geometry::LAYOUT.side_margin + 1e-9);
    assert!(b.y >= a.ground_y() - 1e-9);
    assert!(b.y + b.h <= a.y + a.h - crate::geometry::LAYOUT.top_margin + 1e-9);
}
#[test]
fn ground_preserves_constant_speed() {
    let a = area();
    let mut c = MovementController::default();
    let start = a.ground(-700.0, SIZE);
    c.start(intent(MovementProfile::Ground), start, a, SIZE);
    let (p, done) = c.tick(start, 0.1, a, SIZE, 40.0);
    assert_eq!(p, (start.0 + 4.0, a.ground_y()));
    assert!(!done);
}
#[test]
fn jump_arc_and_exact_ground_return() {
    let a = area();
    let mut c = MovementController::default();
    let mut p = a.ground(-700.0, SIZE);
    c.start(intent(MovementProfile::Jump), p, a, SIZE);
    for _ in 0..5 {
        p = c.tick(p, 0.1, a, SIZE, 40.0).0;
    }
    assert!((p.0 + 600.0).abs() < 1e-9);
    assert!((p.1 - a.ground_y() - 48.0).abs() < 1e-9);
    for _ in 0..6 {
        p = c.tick(p, 0.1, a, SIZE, 40.0).0;
    }
    assert_eq!(p.1, a.ground_y());
    assert_eq!(c.profile(), None);
}
#[test]
fn free2d_returns_and_all_profiles_stay_inside_different_sizes() {
    for size in [
        SIZE,
        Size {
            width: 180.0,
            height: 240.0,
        },
    ] {
        for profile in [
            MovementProfile::Ground,
            MovementProfile::Jump,
            MovementProfile::Free2d,
            MovementProfile::Floating,
            MovementProfile::Flying,
            MovementProfile::Edge,
            MovementProfile::Static,
        ] {
            for target in [(-99999.0, -99999.0), (99999.0, 99999.0)] {
                let a = area();
                let mut c = MovementController::default();
                let mut p = a.ground(-700.0, size);
                let mut i = intent(profile);
                i.target = target;
                i.height = 99999.0;
                c.start(i, p, a, size);
                for _ in 0..12 {
                    p = c.tick(p, 0.1, a, size, 40.0).0;
                    inside(p, a, size);
                }
                if matches!(profile, MovementProfile::Jump | MovementProfile::Free2d) {
                    assert_eq!(p.1, a.ground_y());
                }
            }
        }
    }
}
#[test]
fn completion_static_float_flying_edge_are_deterministic() {
    let a = area();
    for profile in [
        MovementProfile::Static,
        MovementProfile::Floating,
        MovementProfile::Flying,
        MovementProfile::Edge,
    ] {
        let mut c = MovementController::default();
        let mut p = a.ground(-700.0, SIZE);
        let start = p;
        c.start(intent(profile), p, a, SIZE);
        for _ in 0..11 {
            let (next, done) = c.tick(p, 0.1, a, SIZE, 40.0);
            p = next;
            if done {
                break;
            }
        }
        assert_eq!(c.profile(), None);
        match profile {
            MovementProfile::Static => assert_eq!(p, start),
            MovementProfile::Floating => assert!((p.1 - start.1).abs() < 1e-9),
            MovementProfile::Flying => assert_eq!(p, intent(profile).target),
            MovementProfile::Edge => assert_eq!(p, a.ground(-500.0, SIZE)),
            _ => unreachable!(),
        }
    }
}
#[test]
fn local_targets_cursor_windows_and_unknown_metadata() {
    let a = area();
    let start = a.ground(-700.0, SIZE);
    let cfg = MOA_MOVEMENT;
    for unit in [0.0, 0.5, 1.0] {
        let p = bounded_target(start, unit, a, SIZE, cfg);
        inside(p, a, SIZE);
        assert!((p.0 - start.0).abs() <= cfg.radius);
        assert!(p.1 <= a.ground_y() + cfg.height);
    }
    let target = bounded_target(start, 1.0, a, SIZE, cfg);
    let far = (99999.0, 99999.0);
    assert!(unobstructed(
        start,
        target,
        0.0,
        SIZE,
        far,
        Some(&[]),
        100.0
    ));
    assert!(!unobstructed(start, target, 0.0, SIZE, far, None, 100.0));
    assert!(!unobstructed(
        start,
        target,
        0.0,
        SIZE,
        start,
        Some(&[]),
        100.0
    ));
    assert!(!unobstructed(
        start,
        target,
        0.0,
        SIZE,
        far,
        Some(&[SIZE.bounds(target.0, target.1)]),
        100.0
    ));
}
#[test]
fn changing_safe_area_cancels_and_lands() {
    let a = area();
    let mut c = MovementController::default();
    let p = a.ground(-700.0, SIZE);
    c.start(intent(MovementProfile::Free2d), p, a, SIZE);
    let new = Area {
        x: 0.0,
        y: 200.0,
        w: 500.0,
        h: 400.0,
    };
    let (p, done) = c.tick(p, 0.1, new, SIZE, 40.0);
    assert!(done);
    inside(p, new, SIZE);
    assert_eq!(p.1, new.ground_y());
}
#[test]
fn selection_uses_data_and_allowed_profiles() {
    assert_eq!(MOA_MOVEMENT.choose(0.0), MovementProfile::Ground);
    assert_eq!(MOA_MOVEMENT.choose(0.91), MovementProfile::Jump);
    assert_eq!(MOA_MOVEMENT.choose(0.99), MovementProfile::Free2d);
    let cfg = MovementConfig {
        allowed: &[MovementProfile::Ground],
        ..MOA_MOVEMENT
    };
    assert_eq!(cfg.choose(0.99), MovementProfile::Ground);
}

#[test]
fn resized_entity_remains_clamped_and_cancel_stops_motion() {
    let a = area();
    let mut c = MovementController::default();
    let mut p = a.ground(-700.0, SIZE);
    c.start(intent(MovementProfile::Jump), p, a, SIZE);
    let bigger = Size {
        width: 300.0,
        height: 500.0,
    };
    for _ in 0..5 {
        p = c.tick(p, 0.1, a, bigger, 40.0).0;
        inside(p, a, bigger);
    }
    c.cancel();
    let held = c.tick(p, 0.1, a, bigger, 40.0);
    assert_eq!(held, (p, true));
}

#[test]
fn movement_uses_final_desktop_safe_area_not_raw_screen() {
    let screen = Area {
        x: -1200.0,
        y: -800.0,
        w: 1200.0,
        h: 800.0,
    };
    let mut tracker = crate::desktop::SafeAreaTracker::default();
    let safe = tracker.update(1, screen, screen, &[]).final_luma_safe_area;
    assert!(safe.y > screen.y);
    for profile in [
        MovementProfile::Ground,
        MovementProfile::Jump,
        MovementProfile::Free2d,
    ] {
        let mut c = MovementController::default();
        let mut p = safe.ground(-700.0, SIZE);
        let mut i = intent(profile);
        i.target = (screen.x + screen.w, screen.y);
        c.start(i, p, safe, SIZE);
        for _ in 0..30 {
            p = c.tick(p, 0.1, safe, SIZE, 40.0).0;
            inside(p, safe, SIZE);
        }
    }
}

#[test]
fn batch1_profiles_fit_existing_entity_bounds() {
    let definitions: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).unwrap();
    for (code, expected, zone) in [
        ("MELLO", MovementProfile::Jump, "BOTTOM"),
        ("MOSSY", MovementProfile::Ground, "LOWER_CORNER"),
        ("CHIRP", MovementProfile::Flying, "TOP"),
        ("BUBU", MovementProfile::Jump, "BOTTOM"),
    ] {
        let metadata = definitions
            .iter()
            .find(|m| m["monsterCode"] == code)
            .unwrap();
        let profile: MovementProfile =
            serde_json::from_value(metadata["movementProfile"].clone()).unwrap();
        assert_eq!(profile, expected);
        assert_eq!(metadata["spawnProfile"], zone);
        assert_eq!(metadata["enabled"], true);
        let a = area();
        let mut position = a.clamp(-700.0, a.ground_y() + 80.0, SIZE);
        let mut controller = MovementController::default();
        controller.start(intent(profile), position, a, SIZE);
        assert_eq!(controller.profile(), Some(expected));
        for _ in 0..120 {
            let (next, done) = controller.tick(position, 0.1, a, SIZE, 40.0);
            inside(next, a, SIZE);
            position = next;
            if done {
                break;
            }
        }
        assert_eq!(
            controller.profile(),
            None,
            "{code}: finite motion completes"
        );
    }
}
