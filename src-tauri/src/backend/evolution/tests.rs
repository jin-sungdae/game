use super::*;
use crate::{
    behaviors::{InteractionMode, World},
    entities::Area,
};
fn world() -> World {
    World::new(
        Area {
            x: -1000.0,
            y: 180.0,
            w: 1000.0,
            h: 700.0,
        },
        0.0,
        42,
    )
}
fn bootstrap(stage: u32) -> Bootstrap {
    serde_json::from_value(
        serde_json::json!({"player":{"playerId":1,"name":"LOCAL_PLAYER","gold":73},
      "activeCompanion":{"playerCompanionId":1,"species":"MOA","evolutionStage":stage,
      "evolutionName":if stage==1 {"MOA"} else {"MOKORI"},"level":3,"exp":321,"bond":5}}),
    )
    .unwrap()
}
fn eligibility(status: Status) -> Eligibility {
    Eligibility {
        status,
        species: "MOA".into(),
        current_stage: 1,
        current_name: "MOA".into(),
        next_stage: Some(2),
        next_name: Some("MOKORI".into()),
        requirements: Some(Requirements {
            level: Requirement {
                required: 3,
                current: 3,
                met: true,
            },
            bond: Requirement {
                required: 5,
                current: 5,
                met: true,
            },
        }),
    }
}
fn result(outcome: Outcome) -> Result {
    Result {
        result: outcome,
        evolution: Eligibility {
            status: Status::Locked,
            species: "MOA".into(),
            current_stage: 2,
            current_name: "MOKORI".into(),
            next_stage: None,
            next_name: None,
            requirements: None,
        },
        bootstrap: bootstrap(2),
    }
}
#[test]
fn server_status_mapping_never_recalculates_requirements() {
    for status in [Status::Locked, Status::Available, Status::MaxStage] {
        let mut value = eligibility(status.clone());
        value.requirements.as_mut().unwrap().level.current = 0;
        let restored: Eligibility =
            serde_json::from_str(&serde_json::to_string(&value).unwrap()).unwrap();
        assert_eq!(restored.status, status);
    }
}
#[test]
fn explicit_request_guard_and_failure_do_not_evolve() {
    let mut view = Presentation::default();
    assert!(!view.request());
    view.eligibility = Some(eligibility(Status::Locked));
    assert!(!view.request());
    view.eligibility = Some(eligibility(Status::Available));
    assert!(view.request());
    assert!(!view.request());
    assert_eq!(view.phase, Phase::Idle);
    assert!(view.previous.is_none());
    view.fail("server unavailable".into());
    assert!(!view.busy);
    assert_eq!(view.phase, Phase::Idle);
    assert!(view.request());
}
#[test]
fn success_only_timeline_and_position_preservation() {
    let mut w = world();
    w.apply_bootstrap(bootstrap(1));
    w.view.evolution.eligibility = Some(eligibility(Status::Available));
    let position = (w.view.moa.x, w.view.moa.y);
    w.open_evolution();
    assert!(w.view.menu);
    assert!(w.view.evolution.request());
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 1);
    w.apply_evolved(result(Outcome::Evolved), 10.0);
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "MOKORI");
    assert_eq!(position, (w.view.moa.x, w.view.moa.y));
    assert_eq!(w.view.evolution.phase, Phase::Glow);
    assert_eq!(
        w.view.evolution.previous.as_ref().unwrap().evolution_stage,
        1
    );
    assert!(!w.view.evolution.request());
    assert!(!w.view.evolution.tick(10.79));
    assert!(w.view.evolution.tick(10.81));
    assert_eq!(w.view.evolution.phase, Phase::Reveal);
    assert!(w.view.evolution.previous.is_none());
    assert!(w.view.evolution.tick(11.61));
    assert_eq!(w.view.evolution.phase, Phase::Idle);
}
#[test]
fn restart_and_retry_restore_stage_two_without_replaying() {
    let mut w = world();
    w.apply_bootstrap(bootstrap(2));
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
    w.apply_evolved(result(Outcome::AlreadyEvolved), 1.0);
    assert_eq!(w.view.evolution.phase, Phase::Idle);
    assert!(w.view.evolution.previous.is_none());
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "MOKORI");
}
#[test]
fn evolution_menu_survives_pip_despawn_and_closes_explicitly() {
    let mut w = world();
    w.debug_spawn(0.0);
    w.open_evolution();
    w.despawn(1.0);
    assert_eq!(w.view.interaction as u8, InteractionMode::Evolution as u8);
    assert!(w.view.menu);
    w.close();
    assert!(!w.view.menu);
}
#[test]
fn malformed_identity_fails_closed() {
    let mut value = eligibility(Status::Available);
    assert!(value.valid());
    value.next_stage = Some(4);
    assert!(!value.valid());
    value.next_stage = None;
    value.next_name = None;
    value.requirements = None;
    assert!(!value.valid());
}
#[test]
fn http_post_has_no_body_and_only_server_success_changes_identity() {
    use std::{
        io::{Read, Write},
        net::TcpListener,
    };
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let url = format!("http://{}", listener.local_addr().unwrap());
    let task = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        let mut bytes = [0; 4096];
        let n = stream.read(&mut bytes).unwrap();
        let body = serde_json::to_string(&result(Outcome::Evolved)).unwrap();
        write!(
            stream,
            "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        )
        .unwrap();
        String::from_utf8(bytes[..n].to_vec()).unwrap()
    });
    assert_eq!(
        Api::new(&url).unwrap().evolve().unwrap().result,
        Outcome::Evolved
    );
    let request = task.join().unwrap();
    assert!(request.starts_with("POST /api/v1/companions/active/evolve "));
    assert_eq!(request.split_once("\r\n\r\n").unwrap().1, "");
}
#[test]
#[ignore = "requires isolated Spring Boot/PostgreSQL fixture; see docs/evolution-v01.md"]
fn live_evolution_world_slice() {
    let api =
        Api::new(&std::env::var("LUMA_GAME_SERVER_URL").expect("isolated server URL")).unwrap();
    let mode = std::env::var("LUMA_EVOLUTION_FIXTURE").expect("locked, available or restored");
    let mut w = world();
    w.apply_bootstrap(api.bootstrap().unwrap());
    let status = api.evolution().unwrap();
    match mode.as_str() {
        "locked" => {
            assert_eq!(status.status, Status::Locked);
            assert_eq!(status.current_stage, 1);
            assert!(api.evolve().is_err());
        }
        "available" => {
            assert_eq!(status.status, Status::Available);
            w.view.evolution.eligibility = Some(status);
            let position = (w.view.moa.x, w.view.moa.y);
            assert!(w.view.evolution.request());
            w.apply_evolved(api.evolve().unwrap(), 1.0);
            assert_eq!(position, (w.view.moa.x, w.view.moa.y));
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "MOKORI");
            assert_eq!(api.evolve().unwrap().result, Outcome::AlreadyEvolved);
        }
        "restored" => {
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "MOKORI");
            assert_eq!(status.current_stage, 2);
        }
        _ => panic!("unknown fixture"),
    }
    eprintln!(
        "[EVOLUTION LIVE] {mode} PASS identity={:?}",
        w.view.identity
    );
}
