use super::*;
use crate::{
    behaviors::World,
    entities::{Area, PipState},
};
use std::{
    io::{Read, Write},
    net::TcpListener,
};
fn endpoint(status: &str, body: &str) -> (String, std::thread::JoinHandle<String>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap();
    let reply=format!("HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len());
    let thread = std::thread::spawn(move || {
        let (mut socket, _) = listener.accept().unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(3)))
            .unwrap();
        let mut request = Vec::new();
        let mut chunk = [0; 1024];
        while !request.windows(4).any(|w| w == b"\r\n\r\n") {
            let n = socket.read(&mut chunk).unwrap();
            if n == 0 {
                break;
            }
            request.extend_from_slice(&chunk[..n]);
        }
        socket.write_all(reply.as_bytes()).unwrap();
        String::from_utf8(request).unwrap()
    });
    (format!("http://{address}"), thread)
}
fn bootstrap_json() -> &'static str {
    r#"{"player":{"playerId":1,"name":"LOCAL_PLAYER","gold":0},"activeCompanion":{"playerCompanionId":1,"species":"MOA","evolutionStage":1,"evolutionName":"MOA","level":1,"exp":0,"bond":0}}"#
}
fn encounter() -> Encounter {
    Encounter {
        encounter_id: uuid::Uuid::from_u128(1),
        battle_id: None,
        expiration_suspended: false,
        monster: Monster {
            code: "PIP".into(),
            name: "PIP".into(),
            level: 2,
            rarity: "COMMON".into(),
            movement_profile: "GROUND".into(),
        },
        spawned_at: "2026-01-01T00:00:00Z".parse().unwrap(),
        expires_at: "2026-01-01T00:01:00Z".parse().unwrap(),
    }
}
fn world() -> World {
    World::new(
        Area {
            x: 0.0,
            y: 200.0,
            w: 1200.0,
            h: 700.0,
        },
        0.0,
        42,
    )
}
#[test]
fn bootstrap_http_and_world_storage() {
    let (url, thread) = endpoint("200 OK", bootstrap_json());
    let b = Api::new(&url).unwrap().bootstrap().unwrap();
    assert_eq!(b.player.player_id, 1);
    let mut w = world();
    w.apply_bootstrap(b);
    assert_eq!(w.bootstrap.unwrap().active_companion.species, "MOA");
    assert!(thread
        .join()
        .unwrap()
        .starts_with("GET /api/v1/game/bootstrap "));
}
#[test]
fn unavailable_and_invalid_json_leave_local_companion_running() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let url = format!("http://{}", listener.local_addr().unwrap());
    drop(listener);
    let mut w = world();
    assert!(Api::new(&url).unwrap().bootstrap().is_err());
    w.tick(0.1, 0.03, (9999.0, 9999.0), false);
    assert!(w.bootstrap.is_none());
    assert!(w.view.pip.is_none());
    assert!(w.view.moa.y >= w.area.ground_y());
    let (url, thread) = endpoint("200 OK", "{}");
    assert!(Api::new(&url).unwrap().bootstrap().is_err());
    thread.join().unwrap();
}
#[test]
fn post_has_no_client_selection_fields_and_maps_response() {
    let value = encounter();
    let (url, thread) = endpoint("200 OK", &serde_json::to_string(&value).unwrap());
    let response = Api::new(&url).unwrap().encounter(true).unwrap().unwrap();
    assert_eq!(response.encounter_id, value.encounter_id);
    let request = thread.join().unwrap();
    assert!(request.starts_with("POST /api/v1/encounters "));
    assert!(!request.contains("monsterLevel"));
    assert_eq!(response.remaining_at(value.spawned_at), 60.0);
}
#[test]
fn pip_mapping_reuse_expiry_and_debug_separation() {
    let mut w = world();
    let value = encounter();
    w.apply_server_encounter(0.0, Some(value.clone()), 60.0);
    assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Spawning);
    w.tick(1.0, 0.03, (9999.0, 9999.0), false);
    let x = w.view.pip.as_ref().unwrap().x;
    w.apply_server_encounter(1.0, Some(value), 59.0);
    assert_eq!(w.view.pip.as_ref().unwrap().x, x);
    w.despawn(2.0);
    assert_ne!(w.view.pip.as_ref().unwrap().state, PipState::Despawning);
    w.tick(60.0, 0.03, (9999.0, 9999.0), false);
    assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Despawning);
    w.tick(60.6, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
    w.spawn(61.0);
    w.apply_server_encounter(61.1, None, 0.0);
    assert!(w.view.pip.is_some());
}
#[test]
fn unknown_monster_profile_and_expired_lease_do_not_spawn() {
    for (code, profile, remaining) in [
        ("UNKNOWN", "GROUND", 60.0),
        ("PIP", "FLYING", 60.0),
        ("PIP", "GROUND", 0.0),
    ] {
        let mut e = encounter();
        e.monster.code = code.into();
        e.monster.movement_profile = profile.into();
        let mut w = world();
        w.apply_server_encounter(0.0, Some(e), remaining);
        assert!(w.view.pip.is_none());
    }
}
#[test]
fn active_lookup_no_content_expires_server_visual() {
    let (url, thread) = endpoint("204 No Content", "");
    let response = Api::new(&url).unwrap().encounter(false).unwrap();
    assert!(response.is_none());
    thread.join().unwrap();
    let mut w = world();
    w.apply_server_encounter(0.0, Some(encounter()), 60.0);
    w.apply_server_encounter(1.0, response, 0.0);
    assert_eq!(w.view.pip.unwrap().state, PipState::Despawning);
}
#[test]
fn configuration_rejects_remote_origins_and_redirects() {
    for url in [
        "http://example.com",
        "https://127.0.0.1:8081",
        "http://user:secret@localhost",
        "http://localhost/api",
    ] {
        assert!(Api::new(url).is_err());
    }
    let (url, thread) = endpoint("302 Found", "");
    assert!(Api::new(&url).unwrap().bootstrap().is_err());
    thread.join().unwrap();
}

#[test]
#[ignore = "requires a running Spring Boot server and dedicated test PostgreSQL"]
fn live_postgres_server_to_desktop_world_vertical_slice() {
    let url = std::env::var("LUMA_LIVE_TEST_URL")
        .expect("set LUMA_LIVE_TEST_URL to an isolated local test server");
    let api = Api::new(&url).unwrap();
    let mut w = world();
    w.apply_bootstrap(api.bootstrap().unwrap());
    let first = api.encounter(true).unwrap().unwrap();
    let retry = api.encounter(true).unwrap().unwrap();
    assert_eq!(first.encounter_id, retry.encounter_id);
    let active = api.encounter(false).unwrap().unwrap();
    assert_eq!(first.encounter_id, active.encounter_id);
    let remaining = first.remaining_at(Utc::now());
    assert!(remaining > 0.0 && remaining <= 60.0);
    w.apply_server_encounter(0.0, Some(first), remaining);
    assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Spawning);
    w.tick(0.7, 0.03, (9999.0, 9999.0), false);
    assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Roaming);
    w.tick(remaining, 0.03, (9999.0, 9999.0), false);
    assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Despawning);
    w.tick(remaining + 0.6, 0.03, (9999.0, 9999.0), false);
    assert!(w.view.pip.is_none());
}

fn battle_json(status: &str) -> String {
    format!(
        r#"{{"battleId":"00000000-0000-0000-0000-000000000002","encounterId":"00000000-0000-0000-0000-000000000001","turn":1,"status":"{status}","encounterStatus":"ACTIVE","companion":{{"hp":95,"maxHp":100}},"monster":{{"hp":18,"maxHp":30}},"events":["PLAYER_ATTACK","MONSTER_ATTACK"],"reward":null}}"#
    )
}
#[test]
fn battle_start_and_attack_mapping_use_empty_body() {
    for (id, action) in [(1, "start"), (2, "attack")] {
        let (base, t) = endpoint("200 OK", &battle_json("ACTIVE"));
        let b = Api::new(&base)
            .unwrap()
            .battle(uuid::Uuid::from_u128(id), Some(action))
            .unwrap();
        assert_eq!(b.monster.hp, 18);
        assert_eq!(b.companion.hp, 95);
        let request = t.join().unwrap();
        assert!(request.starts_with("POST "));
        assert!(request.ends_with("\r\n\r\n"));
    }
}
#[test]
fn capture_collection_and_ignore_mapping() {
    let id = uuid::Uuid::from_u128(2);
    let body = format!(
        r#"{{"battleId":"{id}","encounterId":"00000000-0000-0000-0000-000000000001","success":false,"chance":0.55,"battle":{},"collection":null}}"#,
        battle_json("ACTIVE")
    );
    let (base, t) = endpoint("200 OK", &body);
    assert!(!Api::new(&base).unwrap().capture(id).unwrap().success);
    t.join().unwrap();
    let (base, t) = endpoint(
        "200 OK",
        r#"[{"monsterCode":"PIP","monsterName":"PIP","captureCount":2,"firstCapturedAt":"2026-01-01T00:00:00Z","lastCapturedAt":"2026-01-02T00:00:00Z"}]"#,
    );
    assert_eq!(
        Api::new(&base).unwrap().collection().unwrap()[0].capture_count,
        2
    );
    t.join().unwrap();
    let (base, t) = endpoint(
        "200 OK",
        r#"{"encounterId":"00000000-0000-0000-0000-000000000001","encounterStatus":"ESCAPED"}"#,
    );
    assert_eq!(
        Api::new(&base)
            .unwrap()
            .ignore(uuid::Uuid::from_u128(1))
            .unwrap()
            .encounter_status,
        "ESCAPED"
    );
    t.join().unwrap();
}
#[test]
fn loading_guard_server_wins_and_terminal_presentation() {
    use super::battle::*;
    let mut p = Presentation {
        encounter_id: Some(uuid::Uuid::from_u128(1)),
        ..Default::default()
    };
    assert!(p.command("battle").is_some());
    assert!(p.command("battle").is_none());
    let b: Battle = serde_json::from_str(&battle_json("ACTIVE")).unwrap();
    p.apply_battle(b.clone());
    assert_eq!(p.battle.as_ref().unwrap().companion.hp, 95);
    p.finish(Some("network error".into()));
    assert!(!p.busy);
    assert_eq!(p.error.as_deref(), Some("network error"));
    assert!(p.command("attack").is_some());
    assert!(p.error.is_none());
    let mut terminal = b;
    terminal.status = Status::Victory;
    terminal.monster.hp = 0;
    terminal.events = vec!["VICTORY".into()];
    p.apply_battle(terminal);
    assert_eq!(p.battle.unwrap().monster.hp, 0);
    assert_eq!(p.feedback.as_deref(), Some("VICTORY"));
}
#[test]
fn unknown_invalid_and_network_response_do_not_mutate_presentation() {
    for text in [
        battle_json("UNKNOWN"),
        battle_json("ACTIVE").replace("\"hp\":95", "\"hp\":999"),
    ] {
        let (base, t) = endpoint("200 OK", &text);
        assert!(Api::new(&base)
            .unwrap()
            .battle(uuid::Uuid::from_u128(2), None)
            .is_err());
        t.join().unwrap();
    }
    let (base, t) = endpoint("503 Unavailable", "{}");
    assert!(Api::new(&base)
        .unwrap()
        .battle(uuid::Uuid::from_u128(2), Some("attack"))
        .is_err());
    t.join().unwrap();
}
#[test]
fn active_battle_suspends_visual_ttl_and_server_resolution_wins() {
    let mut e = encounter();
    e.battle_id = Some(uuid::Uuid::from_u128(2));
    e.expiration_suspended = true;
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
    let remaining = e.remaining_at(e.expires_at + chrono::Duration::seconds(100));
    w.apply_server_encounter(0.0, Some(e), remaining);
    w.tick(100.0, 0.033, (0.0, 0.0), false);
    assert!(w.view.pip.is_some());
    w.apply_server_encounter(101.0, None, 0.0);
    w.tick(102.0, 0.033, (0.0, 0.0), false);
    assert!(w.view.pip.is_none());
}

#[test]
#[ignore = "requires isolated live Spring Boot/PostgreSQL, LUMA_LIVE_TEST_URL"]
fn live_battle_capture_reward_world_slice() {
    let base = std::env::var("LUMA_LIVE_TEST_URL").expect("explicit isolated server URL");
    let api = Api::new(&base).unwrap();
    let before = api.bootstrap().unwrap();
    if let Some(old) = api.encounter(false).unwrap() {
        api.ignore(old.encounter_id).unwrap();
    }
    let e = api.encounter(true).unwrap().unwrap();
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
    w.apply_bootstrap(before.clone());
    w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
    assert!(w.view.pip.is_some());
    let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
    assert_eq!(
        api.battle(e.encounter_id, Some("start")).unwrap().battle_id,
        b.battle_id
    );
    let suspended = api.encounter(false).unwrap().unwrap();
    assert!(suspended.expiration_suspended);
    while b.status == battle::Status::Active {
        b = api.battle(b.battle_id, Some("attack")).unwrap();
        w.view.game.apply_battle(b.clone());
    }
    assert_eq!(b.status, battle::Status::Victory);
    let reward = b.reward.clone().unwrap();
    let c = api.capture(b.battle_id).unwrap();
    let collection = api.collection().unwrap();
    if c.success {
        assert!(collection
            .iter()
            .any(|x| x.monster_code == "PIP" && x.capture_count > 0));
    }
    let after = api.bootstrap().unwrap();
    assert_eq!(after.player.gold, before.player.gold + reward.gold);
    assert_eq!(
        after.active_companion.exp,
        before.active_companion.exp + reward.exp
    );
    assert_eq!(
        after.active_companion.bond,
        before.active_companion.bond + reward.bond
    );
    assert!(api.encounter(false).unwrap().is_none());
    w.apply_server_encounter(5.0, None, 0.0);
    w.tick(6.0, 0.033, (0.0, 0.0), false);
    assert!(w.view.pip.is_none());
    eprintln!(
        "LIVE battle={} encounter={} capture={} gold={} exp={} bond={} level={} collection={}",
        b.battle_id,
        e.encounter_id,
        c.success,
        after.player.gold,
        after.active_companion.exp,
        after.active_companion.bond,
        after.active_companion.level,
        collection.len()
    );
    let e = api.encounter(true).unwrap().unwrap();
    assert_eq!(
        api.ignore(e.encounter_id).unwrap().encounter_status,
        "ESCAPED"
    );
}

#[test]
#[ignore = "requires test-only LiveValidationServer with failure RNG"]
fn live_capture_failure_defeat_world_slice() {
    let api = Api::new(&std::env::var("LUMA_LIVE_TEST_URL").unwrap()).unwrap();
    let before = api.bootstrap().unwrap();
    if let Some(e) = api.encounter(false).unwrap() {
        api.ignore(e.encounter_id).unwrap();
    }
    let e = api.encounter(true).unwrap().unwrap();
    let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
    let mut w = World::new(
        Area {
            x: 0.0,
            y: 0.0,
            w: 1200.0,
            h: 800.0,
        },
        0.0,
        42,
    );
    w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
    while b.status == battle::Status::Active {
        let c = api.capture(b.battle_id).unwrap();
        assert!(!c.success);
        b = c.battle;
        w.view.game.apply_battle(b.clone());
        assert!(b.turn <= 100);
    }
    assert_eq!(b.status, battle::Status::Defeat);
    assert_eq!(b.encounter_status, "PLAYER_DEFEATED");
    assert_eq!(b.companion.hp, 0);
    assert_eq!(api.bootstrap().unwrap().player.gold, before.player.gold);
    w.apply_server_encounter(3.0, None, 0.0);
    w.tick(4.0, 0.033, (0.0, 0.0), false);
    assert!(w.view.pip.is_none());
    let e = api.encounter(true).unwrap().unwrap();
    let mut v = api.battle(e.encounter_id, Some("start")).unwrap();
    while v.status == battle::Status::Active {
        v = api.battle(v.battle_id, Some("attack")).unwrap();
    }
    let hp = v.companion.hp;
    let c = api.capture(v.battle_id).unwrap();
    assert!(!c.success);
    assert_eq!(c.battle.companion.hp, hp);
    assert_eq!(c.battle.encounter_status, "DEFEATED");
    assert!(api.capture(v.battle_id).is_err());
    eprintln!(
        "LIVE FAILURE defeat={} turns={} victory_capture_failure={} no_counter_hp={hp}",
        b.battle_id, b.turn, v.battle_id
    );
}

#[test]
fn battle_response_suspends_original_lease_before_reconciliation() {
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
    w.apply_server_encounter(0.0, Some(encounter()), 1.0);
    w.apply_battle(serde_json::from_str(&battle_json("ACTIVE")).unwrap());
    w.tick(61.0, 0.033, (0.0, 0.0), false);
    assert!(w.view.pip.is_some());
}

#[test]
fn debug_pip_cannot_reuse_a_resolved_server_battle() {
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
    w.apply_server_encounter(0.0, Some(encounter()), 1.0);
    w.view
        .game
        .apply_battle(serde_json::from_str(&battle_json("VICTORY")).unwrap());
    w.apply_server_encounter(2.0, None, 0.0);
    w.tick(3.0, 0.033, (0.0, 0.0), false);
    w.debug_spawn(4.0);
    assert!(w.view.pip.is_some());
    assert!(w.view.game.encounter_id.is_none());
    assert!(w.view.game.command("interact").is_none());
}
