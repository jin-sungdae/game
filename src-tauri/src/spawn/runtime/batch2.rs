use super::*;
use crate::{behaviors::World, geometry::Area};
const CODES: [&str; 5] = ["PEBB", "PUFF", "TIKKI", "MIMI", "WISP"];
fn world() -> World {
    let mut w = World::new(
        Area {
            x: -4000.0,
            y: -1000.0,
            w: 4000.0,
            h: 1000.0,
        },
        0.0,
        42,
    );
    test_environment(&mut w);
    w
}
fn encounter(code: &str) -> Encounter {
    let id = identity(code).unwrap();
    Encounter {
        encounter_id: uuid::Uuid::from_u128(
            100 + CODES.iter().position(|c| *c == code).unwrap() as u128,
        ),
        monster: crate::backend::Monster {
            code: code.into(),
            name: code.into(),
            level: 1,
            rarity: id.rarity.clone(),
            movement_profile: serde_json::to_value(id.movement_profile)
                .unwrap()
                .as_str()
                .unwrap()
                .into(),
        },
        spawned_at: chrono::Utc::now(),
        expires_at: chrono::Utc::now() + chrono::Duration::seconds(60),
        battle_id: None,
        expiration_suspended: false,
    }
}
fn motion(w: &mut World, code: &str) {
    let start = w.view.pip.as_ref().unwrap().clone();
    let profile = w.view.monster.as_ref().unwrap().movement_profile;
    for i in 0..=120 {
        w.tick(0.6 + f64::from(i) * 0.1, 0.1, (-9999.0, -9999.0), false);
        let p = w.view.pip.as_ref().unwrap();
        let b = p.size.bounds(p.x, p.y);
        assert!(
            b.x >= w.area.x + 8.0 && b.x + b.w <= w.area.x + w.area.w - 8.0,
            "{code} x"
        );
        assert!(
            b.y >= w.area.ground_y() && b.y + b.h <= w.area.y + w.area.h - 8.0,
            "{code} y"
        );
        match profile {
            MovementProfile::Static => {
                assert_eq!((p.x, p.y), (start.x, start.y), "MIMI must remain STATIC")
            }
            MovementProfile::Ground => assert_eq!(p.y, w.area.ground_y()),
            MovementProfile::Floating => {}
            _ => panic!("unexpected Batch2 profile"),
        }
    }
    // Idle/pauses are valid; personality trajectories are verified in World behavior tests.
}
#[test]
fn all_five_production_placement_movement_identity_and_restart() {
    for code in CODES {
        let mut w = world();
        let e = encounter(code);
        w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
        let p = w.view.pip.as_ref().unwrap();
        let a = w.area;
        if ["PEBB", "TIKKI"].contains(&code) {
            assert_eq!(p.y, a.ground_y());
        }
        if code == "MIMI" {
            let b = p.size.bounds(p.x, p.y);
            assert!(b.x == a.x + 8.0 || b.x + b.w == a.x + a.w - 8.0);
        }
        let id = w.view.monster.as_ref().unwrap();
        assert_eq!(id.monster_code, code);
        assert_eq!(id.asset_identity, code.to_lowercase());
        assert!(w.view.dex.discovered_codes.is_empty());
        assert!(w.discovery.contains(code));
        motion(&mut w, code);
        let mut restored = world();
        assert_eq!(restored.spawn_action(0.0), Some(Action::Reconcile));
        restored.complete_spawn(0.0, Action::Reconcile, Ok(Some(e.clone())));
        assert_eq!(
            restored.view.monster.as_ref().unwrap().encounter_id,
            Some(e.encounter_id)
        );
        assert!(restored.spawn_action(1.0).is_none());
        restored.apply_server_encounter(2.0, None, 0.0);
        restored.tick(3.0, 0.1, (-9999.0, -9999.0), false);
        assert!(restored.view.pip.is_none());
        assert_eq!(
            restored.spawn_runtime.director.state(),
            SpawnState::Cooldown
        );
    }
}
#[test]
fn missing_asset_unsupported_content_and_unsafe_placement_never_discover() {
    for code in CODES {
        let mut w = world();
        w.spawn_runtime.load_assets(|_| None);
        w.apply_server_encounter(0.0, Some(encounter(code)), 60.0);
        assert!(w.view.pip.is_none());
        assert!(w.view.dex.discovered_codes.is_empty());
        assert!(matches!(w.spawn_action(0.0), Some(Action::Resolve(_))));
        let mut w = world();
        let mut e = encounter(code);
        e.monster.movement_profile = "JUMP".into();
        w.apply_server_encounter(0.0, Some(e), 60.0);
        assert!(w.view.pip.is_none());
        let mut w = world();
        w.set_spawn_environment(
            crate::desktop::DesktopSafeArea {
                screen_frame: w.area,
                os_visible_frame: w.area,
                detected_dock_bounds: vec![w.area],
                rejected_dock_candidates: 0,
                fallback_safe_insets: Default::default(),
                retained_safe_insets: Default::default(),
                final_luma_safe_area: w.area,
            },
            (-9999.0, -9999.0),
            Some(vec![]),
        );
        w.apply_server_encounter(0.0, Some(encounter(code)), 60.0);
        assert!(w.view.pip.is_none());
        assert!(w.view.dex.discovered_codes.is_empty());
    }
    let mut w = world();
    w.debug_spawn(0.0);
    assert!(w.view.monster.is_none());
    assert!(w.view.dex.discovered_codes.is_empty());
}
#[test]
#[ignore = "requires isolated test-only LUMA_TEST_BATCH2 Spring fixture"]
fn live_batch2_world_capture_and_collection() {
    let url = std::env::var("LUMA_GAME_SERVER_URL").unwrap();
    let api = crate::backend::Api::new(&url).unwrap();
    assert!(api.encounter(false).unwrap().is_none());
    for code in CODES {
        let mut w = world();
        assert_eq!(w.spawn_action(0.0), Some(Action::Reconcile));
        w.complete_spawn(0.0, Action::Reconcile, Ok(api.encounter(false).unwrap()));
        let t = w.spawn_runtime.director.next_spawn_at().as_secs_f64();
        assert!(w.spawn_action(t).is_none());
        assert_eq!(w.spawn_action(t), Some(Action::Create));
        let e = api.encounter(true).unwrap().unwrap();
        assert_eq!(e.monster.code, code);
        // Use a fresh World monotonic origin for deterministic movement sampling.
        w = world();
        w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
        motion(&mut w, code);
        let mut restored = world();
        assert_eq!(restored.spawn_action(0.0), Some(Action::Reconcile));
        restored.complete_spawn(0.0, Action::Reconcile, Ok(api.encounter(false).unwrap()));
        assert_eq!(
            restored.view.monster.as_ref().unwrap().encounter_id,
            Some(e.encounter_id)
        );
        assert!(restored.spawn_action(1.0).is_none()); // no POST during restoration
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
        assert_eq!(potion.current_hp, Some(100));
        let charm = api.use_item("CAPTURE_CHARM", Some(b.battle_id)).unwrap();
        assert_eq!(charm.armed, Some(true));
        let capture = api.capture(b.battle_id).unwrap();
        let base = if ["PEBB", "PUFF"].contains(&code) {
            0.35
        } else {
            0.25
        };
        assert!((capture.base_chance.unwrap() - (base + 0.20)).abs() < 1e-9);
        assert_eq!(capture.item_bonus, Some(0.10));
        assert!((capture.final_chance.unwrap() - (base + 0.30)).abs() < 1e-9);
        assert!(capture.success);
        assert_eq!(capture.collection.as_ref().unwrap().monster_code, code);
        restored.view.dex.loaded(api.collection().unwrap());
        restored
            .view
            .dex
            .captured(capture.collection.as_ref().unwrap());
        restored.apply_battle(capture.battle);
        restored.apply_server_encounter(2.0, api.encounter(false).unwrap(), 0.0);
        restored.tick(3.0, 0.1, (-9999.0, -9999.0), false);
        assert!(restored.view.pip.is_none());
        assert_eq!(
            restored.spawn_runtime.director.state(),
            SpawnState::Cooldown
        );
        assert!(restored.spawn_action(3.0).is_none());
        let row = restored
            .view
            .dex
            .records
            .as_ref()
            .unwrap()
            .iter()
            .find(|c| c.monster_code == code)
            .unwrap();
        assert_eq!(row.capture_count, 1);
        assert_eq!(row.monster_name, code);
        assert!(row.first_captured_at <= row.last_captured_at);
        eprintln!("BATCH2 LIVE PASS {code}: spawn/movement/restart/battle/hit/capture/collection/cooldown encounter={}",e.encounter_id);
    }
    let records = api.collection().unwrap();
    assert_eq!(records.len(), 5);
    assert!(CODES.iter().all(|code| records
        .iter()
        .any(|r| r.monster_code == *code && r.capture_count == 1)));
    if let Ok(path) = std::env::var("LUMA_TEST_COLLECTION_OUTPUT") {
        std::fs::write(path, serde_json::to_vec(&records).unwrap()).unwrap();
    }
}
