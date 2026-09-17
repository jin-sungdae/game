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
