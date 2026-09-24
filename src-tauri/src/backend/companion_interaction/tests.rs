use super::*;
use crate::{behaviors::World, entities::Area};
fn result() -> Result {
    serde_json::from_value(serde_json::json!({
        "outcome":"AWARDED","bondDelta":1,
        "serverTime":"2026-09-24T00:00:00Z","nextAvailableAt":"2026-09-24T00:05:00Z",
        "bootstrap":{"player":{"playerId":1,"name":"LOCAL_PLAYER","gold":0},"activeCompanion":{"playerCompanionId":1,"species":"MOA","evolutionStage":1,"evolutionName":"MOA","level":1,"exp":0,"bond":1}},
        "evolution":{"status":"LOCKED","species":"MOA","currentStage":1,"currentName":"MOA","nextStage":2,"nextName":"MOKORI","requirements":{"level":{"required":3,"current":1,"met":false},"bond":{"required":5,"current":1,"met":false}}}
    })).unwrap()
}
#[test]
fn server_ack_only_cooldown_silent_and_feedback_expires() {
    let mut w = World::new(
        Area {
            x: 0.0,
            y: 0.0,
            w: 1280.0,
            h: 800.0,
        },
        0.0,
        1,
    );
    assert!(w.view.bond.request());
    assert!(!w.view.bond.request());
    assert!(w.view.identity.is_none());
    w.apply_companion_interaction(Err("offline".into()), 0.0);
    assert!(w.view.identity.is_none());
    assert!(w.view.bond.feedback.is_none());
    assert!(!w.view.bond.busy);
    w.apply_companion_interaction(Ok(result()), 1.0);
    assert_eq!(w.view.identity.as_ref().unwrap().bond, 1);
    assert_eq!(w.view.bond.feedback.as_deref(), Some("Bond +1"));
    assert!(!w.view.bond.tick(3.9));
    assert!(w.view.bond.tick(4.0));
    assert!(!w.view.menu);
    let mut cooldown = result();
    cooldown.outcome = Outcome::Cooldown;
    cooldown.bond_delta = 0;
    w.apply_companion_interaction(Ok(cooldown), 5.0);
    assert!(w.view.bond.feedback.is_none());
    assert_eq!(w.view.identity.as_ref().unwrap().bond, 1);
}
#[test]
fn malformed_award_identity_and_timestamp_are_rejected() {
    assert!(result().valid());
    let mut r = result();
    r.bond_delta = 100;
    assert!(!r.valid());
    let mut r = result();
    r.outcome = Outcome::Cooldown;
    assert!(!r.valid());
    let mut r = result();
    r.next_available_at = r.server_time;
    assert!(!r.valid());
    let mut r = result();
    r.bootstrap.active_companion.evolution_stage = 3;
    assert!(!r.valid());
}
#[test]
fn http_command_is_bodyless_and_validated() {
    use std::{
        io::{Read, Write},
        net::TcpListener,
    };
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let base = format!("http://{}", listener.local_addr().unwrap());
    let worker = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream
            .set_read_timeout(Some(std::time::Duration::from_secs(3)))
            .unwrap();
        let mut request = Vec::new();
        let mut byte = [0; 1];
        while !request.ends_with(b"\r\n\r\n") {
            stream.read_exact(&mut byte).unwrap();
            request.push(byte[0]);
        }
        let request = String::from_utf8(request).unwrap();
        assert!(request.starts_with("POST /api/v1/companions/active/interact HTTP/1.1"));
        let body = serde_json::to_string(&result()).unwrap();
        write!(stream,"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",body.len(),body).unwrap();
    });
    assert_eq!(
        Api::new(&base)
            .unwrap()
            .interact_companion()
            .unwrap()
            .bond_delta,
        1
    );
    worker.join().unwrap();
}

#[test]
#[ignore = "requires fresh isolated Spring/PostgreSQL; LUMA_GAME_SERVER_URL and LUMA_BOND_LIVE_PHASE=fresh/restored"]
fn live_companion_bond_worker_slice() {
    use crate::backend::{battle::Command, Backend, Event};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    let api = Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    let phase = std::env::var("LUMA_BOND_LIVE_PHASE").unwrap();
    let fresh = phase == "fresh";
    assert!(fresh || phase == "restored");
    let stopped = Arc::new(AtomicBool::new(false));
    let worker = Backend::start(stopped.clone());
    let mut w = World::new(
        Area {
            x: 0.0,
            y: 0.0,
            w: 1280.0,
            h: 800.0,
        },
        0.0,
        1,
    );
    let boot = api.bootstrap().unwrap();
    assert_eq!(boot.active_companion.bond, if fresh { 0 } else { 2 });
    w.apply_bootstrap(boot);
    for attempt in 0..2 {
        assert!(w.view.bond.request());
        assert!(worker.request(Command::InteractCompanion));
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
        let mut completed = false;
        while std::time::Instant::now() < deadline && !completed {
            while let Some(event) = worker.event() {
                match event {
                    Event::CompanionInteracted(result) => {
                        let result = result.unwrap();
                        assert_eq!(result.bond_delta, if fresh && attempt == 0 { 1 } else { 0 });
                        w.apply_companion_interaction(Ok(result), 1.0);
                        completed = true;
                    }
                    Event::Bootstrap(boot) => w.apply_bootstrap(boot),
                    _ => {}
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
        assert!(completed);
        assert!(!w.view.bond.busy);
        assert!(!w.view.menu);
    }
    assert!(w.view.bond.feedback.is_none());
    if fresh {
        for _ in 0..3 {
            let e = api.encounter(true).unwrap().unwrap();
            let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
            while b.status == crate::backend::battle::Status::Active {
                b = api.battle(b.battle_id, Some("attack")).unwrap();
            }
            assert_eq!(b.reward.unwrap().bond, 0);
            api.ignore(e.encounter_id).unwrap();
        }
        assert_eq!(api.bootstrap().unwrap().active_companion.bond, 1);
        api.purchase("BOND_BERRY", 1).unwrap();
        assert_eq!(
            api.use_item("BOND_BERRY", None).unwrap().bond_after,
            Some(2)
        );
    }
    stopped.store(true, Ordering::Relaxed);
    assert_eq!(api.bootstrap().unwrap().active_companion.bond, 2);
    eprintln!("BOND LIVE PASS phase={phase}: bounded worker, award/cooldown, authoritative bootstrap, Berry, battle Bond0");
}
