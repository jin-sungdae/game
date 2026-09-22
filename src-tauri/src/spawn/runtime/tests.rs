use super::*;
use crate::{behaviors::World, geometry::Area};
fn world() -> World {
    let mut w = World::new(
        Area {
            x: -1200.0,
            y: -600.0,
            w: 1100.0,
            h: 700.0,
        },
        0.0,
        42,
    );
    test_environment(&mut w);
    w
}
fn encounter() -> Encounter {
    Encounter {
        encounter_id: uuid::Uuid::from_u128(9),
        monster: crate::backend::Monster {
            code: "PIP".into(),
            name: "PIP".into(),
            level: 2,
            rarity: "COMMON".into(),
            movement_profile: "GROUND".into(),
        },
        spawned_at: chrono::Utc::now(),
        expires_at: chrono::Utc::now() + chrono::Duration::seconds(60),
        battle_id: None,
        expiration_suspended: false,
    }
}
fn due(w: &mut World) -> f64 {
    let t = w.spawn_runtime.director.next_spawn_at().as_secs_f64();
    assert!(w.spawn_action(t).is_none());
    t
}
#[test]
fn startup_empty_schedule_one_opportunity_and_no_duplicate() {
    let mut w = world();
    assert_eq!(w.spawn_action(0.0), Some(Action::Reconcile));
    for _ in 0..100 {
        assert!(w.spawn_action(0.0).is_none());
    }
    w.complete_spawn(0.0, Action::Reconcile, Ok(None));
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
    let t = due(&mut w);
    assert!((120.0..=300.0).contains(&t));
    assert_eq!(w.spawn_action(t), Some(Action::Create));
    for _ in 0..100 {
        assert!(w.spawn_action(t + 100.0).is_none());
    }
    w.complete_spawn(t, Action::Create, Ok(Some(encounter())));
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Active);
    let p = w.view.pip.as_ref().unwrap();
    assert_eq!(p.y, w.area.ground_y());
    let identity = w.view.monster.as_ref().unwrap();
    assert_eq!(identity.monster_code, "PIP");
    assert_eq!(identity.asset_identity, "pip");
    assert_eq!(identity.level, 2);
    assert_eq!(identity.movement_profile, MovementProfile::Ground);
    assert_eq!(w.view.dex.discovered_codes, vec!["PIP"]);
}
#[test]
fn startup_existing_and_restart_restore_without_post() {
    let e = encounter();
    for _ in 0..2 {
        let mut w = world();
        assert_eq!(w.spawn_action(0.0), Some(Action::Reconcile));
        w.complete_spawn(0.0, Action::Reconcile, Ok(Some(e.clone())));
        assert!(w.view.pip.is_some());
        assert!(w.spawn_action(600.0).is_none());
    }
}
#[test]
fn backend_failure_backoff_reconciles_lost_post_before_retry() {
    let mut w = world();
    let mut t = 0.0;
    for delay in [5.0, 10.0, 30.0, 30.0] {
        assert_eq!(w.spawn_action(t), Some(Action::Reconcile));
        w.complete_spawn(t, Action::Reconcile, Err("offline".into()));
        assert_eq!(
            w.spawn_runtime.director.next_spawn_at().as_secs_f64(),
            t + delay
        );
        assert!(w.spawn_action(t + delay - 0.01).is_none());
        t = due(&mut w);
    }
    assert_eq!(w.spawn_action(t), Some(Action::Reconcile));
    w.complete_spawn(t, Action::Reconcile, Ok(Some(encounter())));
    assert!(w.view.pip.is_some());
}
#[test]
fn unsupported_content_and_profile_resolve_without_discovery_or_new_post() {
    for (code, profile) in [("UNKNOWN", "GROUND"), ("MELLO", "JUMP"), ("PIP", "FLYING")] {
        let mut w = world();
        let mut e = encounter();
        e.monster.code = code.into();
        e.monster.movement_profile = profile.into();
        w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
        assert!(w.view.pip.is_none());
        assert!(w.view.dex.discovered_codes.is_empty());
        assert_eq!(w.spawn_action(0.0), Some(Action::Resolve(e.encounter_id)));
        w.complete_spawn(0.0, Action::Resolve(e.encounter_id), Err("offline".into()));
        assert!(w.spawn_action(4.9).is_none());
        assert_eq!(w.spawn_action(5.0), Some(Action::Resolve(e.encounter_id)));
        w.complete_spawn(5.0, Action::Resolve(e.encounter_id), Ok(None));
        assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
    }
}
#[test]
fn bounded_placement_retries_keep_identity_and_never_create_another_encounter() {
    let mut w = world();
    let e = encounter();
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
        (0.0, 0.0),
        None,
    );
    w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
    assert!(w.view.pip.is_none());
    assert!(w.view.dex.discovered_codes.is_empty());
    for t in [1.0, 5.0, 15.0] {
        w.tick(t, 0.03, (0.0, 0.0), false);
        assert!(w.spawn_action(t).is_none());
    }
    w.tick(45.0, 0.03, (0.0, 0.0), false);
    assert_eq!(w.spawn_action(45.0), Some(Action::Resolve(e.encounter_id)));
    assert_eq!(
        w.spawn_runtime.encounter.as_ref().unwrap().encounter_id,
        e.encounter_id
    );
}
#[test]
fn placement_recovers_locally_and_terminal_reconciliation_releases_budget() {
    let mut w = World::new(
        Area {
            x: 0.0,
            y: 200.0,
            w: 1200.0,
            h: 700.0,
        },
        0.0,
        1,
    );
    let e = encounter();
    w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
    assert!(w.view.pip.is_none());
    test_environment(&mut w);
    w.tick(5.0, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_some());
    assert!(w.spawn_action(5.0).is_none());
    w.apply_server_encounter(6.0, None, 0.0);
    w.tick(7.0, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
}
#[test]
fn debug_is_not_budget_or_discovery_and_authority_replaces_one_visual() {
    let mut w = world();
    w.debug_spawn(0.0);
    assert!(w.view.dex.discovered_codes.is_empty());
    assert_eq!(w.spawn_action(0.0), Some(Action::Reconcile));
    w.complete_spawn(0.0, Action::Reconcile, Ok(Some(encounter())));
    assert!(w.view.monster.as_ref().unwrap().encounter_id.is_some());
    assert_eq!(w.view.dex.discovered_codes, vec!["PIP"]);
    w.debug_spawn(2.0);
    assert!(w.view.monster.is_some());
}
#[test]
fn lease_expiry_never_authorizes_another_post_without_server_confirmation() {
    let mut w = world();
    w.apply_server_encounter(0.0, Some(encounter()), 1.0);
    w.tick(2.0, 0.03, (9999.0, 9999.0), false);
    w.tick(3.0, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    assert!(w.spawn_action(600.0).is_none());
    assert!(w.spawn_runtime.encounter.is_some());
    w.apply_server_encounter(601.0, None, 0.0);
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
}

#[test]
#[ignore = "requires isolated PostgreSQL/Spring fixture and LUMA_GAME_SERVER_URL"]
fn live_spawn_encounter_world_slice() {
    use crate::backend::{battle::Command, Backend, Event};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    fn pump(backend: &Backend, w: &mut World, now: f64, spawn: bool) {
        let deadline = std::time::Instant::now() + Duration::from_secs(20);
        loop {
            while let Some(event) = backend.event() {
                match event {
                    Event::SpawnCompleted(a, r) => {
                        assert!(r.is_ok(), "spawn {r:?}");
                        w.complete_spawn(now, a, r);
                        if spawn {
                            return;
                        }
                    }
                    Event::Encounter(value) => {
                        let remaining = value
                            .as_ref()
                            .map_or(0.0, |e| e.remaining_at(chrono::Utc::now()));
                        w.apply_server_encounter(now, value, remaining);
                    }
                    Event::Battle(b) => w.apply_battle(b),
                    Event::Capture(c) => {
                        assert!(c.success);
                        w.view.dex.captured(c.collection.as_ref().unwrap());
                        w.apply_battle(c.battle);
                    }
                    Event::Bootstrap(b) => w.apply_bootstrap(b),
                    Event::Finished(error) => {
                        assert!(error.is_none(), "{error:?}");
                        if !spawn {
                            return;
                        }
                    }
                    _ => {}
                }
            }
            assert!(
                std::time::Instant::now() < deadline,
                "worker response timeout"
            );
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    fn command(backend: &Backend, w: &mut World, now: f64, cmd: Command) {
        assert!(backend.request(cmd));
        pump(backend, w, now, false);
    }
    fn action(backend: &Backend, w: &mut World, now: f64, expected: Action) {
        assert_eq!(w.spawn_action(now), Some(expected));
        assert!(backend.request(Command::Spawn(expected)));
        pump(backend, w, now, true);
    }
    let stopped = Arc::new(AtomicBool::new(false));
    struct Stop(Arc<AtomicBool>);
    impl Drop for Stop {
        fn drop(&mut self) {
            self.0.store(true, Ordering::Relaxed);
        }
    }
    let _stop = Stop(stopped.clone());
    let backend = Backend::start(stopped);
    let mut w = world();
    action(&backend, &mut w, 0.0, Action::Reconcile);
    assert!(w.spawn_runtime.encounter.is_none());
    let t = due(&mut w);
    action(&backend, &mut w, t, Action::Create);
    let id = w.spawn_runtime.encounter.as_ref().unwrap().encounter_id;
    let before = w.view.pip.as_ref().unwrap().x;
    for i in 1..30 {
        w.tick(t + f64::from(i) * 0.1, 0.1, (9999.0, 9999.0), false);
    }
    assert_ne!(before, w.view.pip.as_ref().unwrap().x);
    let mut restarted = world();
    action(&backend, &mut restarted, t + 3.0, Action::Reconcile);
    assert_eq!(
        restarted
            .spawn_runtime
            .encounter
            .as_ref()
            .unwrap()
            .encounter_id,
        id
    );
    w = restarted;
    command(&backend, &mut w, t + 4.0, Command::StartBattle(id));
    assert!(w.spawn_action(t + 1000.0).is_none());
    let battle_id = w.view.game.battle.as_ref().unwrap().battle_id;
    command(&backend, &mut w, t + 5.0, Command::Capture(battle_id));
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
    w.tick(t + 6.0, 0.1, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    let t = due(&mut w);
    action(&backend, &mut w, t, Action::Reconcile);
    action(&backend, &mut w, t, Action::Create);
    let second = w.spawn_runtime.encounter.as_ref().unwrap().encounter_id;
    assert_ne!(id, second);
    command(&backend, &mut w, t + 1.0, Command::Ignore(second));
    w.tick(t + 2.0, 0.1, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
    assert_eq!(w.view.dex.discovered_codes, vec!["PIP"]);
    eprintln!("LIVE SPAWN PASS first={id} second={second} automatic_create=2 restore_create=0 capture=1 ignore=1 cooldown={:?}",w.spawn_runtime.director.next_spawn_at());
}

#[test]
fn confirmed_capture_ignore_expiry_and_defeat_release_budget_after_despawn() {
    for terminal in [
        "CAPTURED",
        "ESCAPED",
        "EXPIRED",
        "PLAYER_DEFEATED",
        "DEFEATED",
    ] {
        let mut w = world();
        let e = encounter();
        w.apply_server_encounter(0.0, Some(e), 60.0);
        // GET active returns None after each server-owned terminal transition.
        w.apply_server_encounter(1.0, None, 0.0);
        w.tick(2.0, 0.03, (9999.0, 9999.0), false);
        assert!(w.view.pip.is_none(), "{terminal}");
        assert_eq!(
            w.spawn_runtime.director.state(),
            SpawnState::Cooldown,
            "{terminal}"
        );
        let t = due(&mut w);
        assert!((121.0..=301.0).contains(&t));
        assert_eq!(w.spawn_action(t), Some(Action::Reconcile));
        w.complete_spawn(t, Action::Reconcile, Ok(None));
        assert_eq!(
            w.spawn_action(t),
            Some(Action::Create),
            "must not double cooldown after {terminal}"
        );
    }
}
#[test]
fn unknown_environment_does_not_discover_and_battle_occupies_budget() {
    let mut w = world();
    let e = encounter();
    let id = e.encounter_id;
    w.apply_server_encounter(0.0, Some(e), 1.0);
    let b=serde_json::from_value(serde_json::json!({"battleId":uuid::Uuid::from_u128(5),"encounterId":id,"turn":0,"status":"ACTIVE","encounterStatus":"ACTIVE","companion":{"hp":100,"maxHp":100},"monster":{"hp":30,"maxHp":30},"events":[],"reward":null})).unwrap();
    w.apply_battle(b);
    w.tick(1000.0, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_some());
    assert!(w.spawn_action(1000.0).is_none());
}

#[test]
#[ignore = "requires isolated Spring server; waits for unchanged 60-second server TTL"]
fn live_spawn_expiration_world_slice() {
    let api = crate::backend::Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    let mut w = world();
    let a = w.spawn_action(0.0).unwrap();
    let response = api.spawn_action(a).unwrap();
    assert!(response.is_none());
    w.complete_spawn(0.0, a, Ok(response));
    let t = due(&mut w);
    let a = w.spawn_action(t).unwrap();
    assert_eq!(a, Action::Create);
    let response = api.spawn_action(a).unwrap();
    let e = response.as_ref().unwrap().clone();
    w.complete_spawn(t, a, Ok(response));
    assert!(w.view.pip.is_some());
    std::thread::sleep(Duration::from_secs_f64(
        e.remaining_at(chrono::Utc::now()) + 0.2,
    ));
    w.tick(t + 61.0, 0.03, (9999.0, 9999.0), false);
    w.tick(t + 62.0, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    assert!(w.spawn_action(t + 62.0).is_none());
    let response = api.spawn_action(Action::Reconcile).unwrap();
    assert!(response.is_none());
    w.apply_server_encounter(t + 62.0, response, 0.0);
    assert_eq!(w.spawn_runtime.director.state(), SpawnState::Cooldown);
    eprintln!(
        "LIVE EXPIRATION PASS encounter={} create=1 active_get=2 unchanged_server_ttl=60s",
        e.encounter_id
    );
}
