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
        "stage3-available" => {
            assert_eq!(status.current_stage, 2);
            assert_eq!(status.status, Status::Available);
            let before = api.bootstrap().unwrap();
            let position = (w.view.moa.x, w.view.moa.y);
            w.view.evolution.eligibility = Some(status);
            assert!(w.view.evolution.request());
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
            let response = api.evolve().unwrap();
            assert_eq!(response.result, Outcome::Evolved);
            let after = &response.bootstrap;
            assert_eq!(after.active_companion.evolution_name, "NEBLA");
            assert_eq!(before.player.gold, after.player.gold);
            assert_eq!(before.active_companion.level, after.active_companion.level);
            assert_eq!(before.active_companion.exp, after.active_companion.exp);
            assert_eq!(before.active_companion.bond, after.active_companion.bond);
            w.apply_evolved(response, 1.0);
            assert_eq!(w.view.evolution.phase, Phase::Glow);
            assert_eq!(
                w.view.evolution.previous.as_ref().unwrap().evolution_stage,
                2
            );
            w.view.evolution.tick(1.9);
            assert_eq!(w.view.evolution.phase, Phase::Reveal);
            assert_eq!(position, (w.view.moa.x, w.view.moa.y));
            assert_eq!(api.evolve().unwrap().result, Outcome::AlreadyEvolved);
        }
        "stage3-restored" => {
            assert_eq!(status.current_stage, 3);
            assert_eq!(status.current_name, "NEBLA");
            assert_eq!(status.next_stage, None);
            assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 3);
            assert_eq!(w.view.evolution.phase, Phase::Idle);
            assert_eq!(api.evolve().unwrap().result, Outcome::AlreadyEvolved);
        }
        _ => panic!("unknown fixture"),
    }
    eprintln!(
        "[EVOLUTION LIVE] {mode} PASS identity={:?}",
        w.view.identity
    );
}
#[test]
fn stage_three_acknowledgement_transition_restart_and_retry() {
    let mut w = world();
    w.apply_bootstrap(bootstrap(2));
    let position = (w.view.moa.x, w.view.moa.y);
    let mut r = result(Outcome::Evolved);
    r.bootstrap.active_companion.evolution_stage = 3;
    r.bootstrap.active_companion.evolution_name = "NEBLA".into();
    r.evolution.current_stage = 3;
    r.evolution.current_name = "NEBLA".into();
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
    w.apply_evolved(r.clone(), 1.0);
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "NEBLA");
    assert_eq!(w.view.evolution.phase, Phase::Glow);
    assert_eq!(
        w.view.evolution.previous.as_ref().unwrap().evolution_stage,
        2
    );
    w.view.evolution.tick(1.9);
    assert_eq!(w.view.evolution.phase, Phase::Reveal);
    assert_eq!(position, (w.view.moa.x, w.view.moa.y));
    let mut restored = world();
    restored.apply_bootstrap(r.bootstrap.clone());
    assert_eq!(restored.view.identity.as_ref().unwrap().evolution_stage, 3);
    r.result = Outcome::AlreadyEvolved;
    restored.apply_evolved(r, 3.0);
    assert_eq!(restored.view.evolution.phase, Phase::Idle);
}

#[test]
#[ignore = "fresh isolated fixed-RNG Spring/PostgreSQL required; no progression SQL writes"]
fn live_nebla_natural_production_trace() {
    let api = Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    let mode = std::env::var("LUMA_NEBLA_MODE").unwrap();
    let mut w = world();
    w.apply_bootstrap(api.bootstrap().unwrap());
    let mut frames = Vec::new();
    let frame = |label: &str, w: &World| serde_json::json!({"label":label,"snapshot":w.view});
    if mode == "natural" {
        assert_eq!(api.bootstrap().unwrap().active_companion.exp, 0);
        for i in 1..=75 {
            let now = f64::from(i) * 10.0;
            let e = api.encounter(true).unwrap().unwrap();
            crate::spawn::runtime::test_environment(&mut w);
            w.apply_server_encounter(now, Some(e.clone()), 60.0);
            assert!(w.view.pip.is_some());
            let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
            w.apply_battle(b.clone());
            while b.status == crate::backend::battle::Status::Active {
                b = api.battle(b.battle_id, Some("attack")).unwrap();
                w.apply_battle(b.clone());
            }
            assert_eq!(b.status, crate::backend::battle::Status::Victory);
            assert_eq!(b.reward.as_ref().unwrap().exp, 20);
            api.ignore(e.encounter_id).unwrap();
            w.apply_server_encounter(now + 1.0, None, 0.0);
            w.tick(now + 2.0, 0.1, (-9999.0, -9999.0), false);
            let boot = api.bootstrap().unwrap();
            assert_eq!(boot.active_companion.exp, u64::from(i as u32) * 20);
            assert_eq!(boot.active_companion.bond, if i <= 15 { 0 } else { 5 });
            w.apply_bootstrap(boot);
            if i == 15 {
                api.purchase("BOND_BERRY", 5).unwrap();
                for _ in 0..5 {
                    api.use_item("BOND_BERRY", None).unwrap();
                }
                w.apply_evolved(api.evolve().unwrap(), now + 3.0);
                w.view.evolution.tick(now + 5.0);
            }
            if i == 74 {
                assert_eq!(w.view.identity.as_ref().unwrap().level, 5);
                assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
                frames.push(frame("mokori-lv5", &w));
            }
        }
        let c = api.bootstrap().unwrap().active_companion;
        assert_eq!(c.level, 6);
        assert_eq!(c.bond, 5);
        api.purchase("BOND_BERRY", 7).unwrap();
        for _ in 0..6 {
            api.use_item("BOND_BERRY", None).unwrap();
        }
        let used = api.use_item("BOND_BERRY", None).unwrap();
        assert_eq!(used.bond_after, Some(12));
        w.apply_bootstrap(api.bootstrap().unwrap());
        w.view.evolution.eligibility = Some(api.evolution().unwrap());
        assert_eq!(
            w.view.evolution.eligibility.as_ref().unwrap().status,
            Status::Available
        );
        assert!(w.view.evolution.request());
        assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 2);
        frames.push(frame("request-before-ack", &w));
        let before = api.bootstrap().unwrap();
        let result = api.evolve().unwrap();
        assert_eq!(result.result, Outcome::Evolved);
        assert_eq!(before.player.gold, result.bootstrap.player.gold);
        assert_eq!(
            before.active_companion.exp,
            result.bootstrap.active_companion.exp
        );
        assert_eq!(
            before.active_companion.level,
            result.bootstrap.active_companion.level
        );
        assert_eq!(
            before.active_companion.bond,
            result.bootstrap.active_companion.bond
        );
        w.apply_evolved(result, 800.0);
        assert_eq!(w.view.evolution.phase, Phase::Glow);
        frames.push(frame("glow", &w));
        w.view.evolution.tick(800.9);
        assert_eq!(w.view.evolution.phase, Phase::Reveal);
        frames.push(frame("reveal", &w));
    } else {
        assert_eq!(mode, "restored");
        let c = w.view.identity.as_ref().unwrap();
        assert_eq!(c.evolution_name, "NEBLA");
        assert_eq!(c.evolution_stage, 3);
        assert_eq!(c.level, 6);
        assert_eq!(c.exp, 1500);
        assert_eq!(c.bond, 12);
        assert_eq!(w.view.evolution.phase, Phase::Idle);
        frames.push(frame("restored", &w));
    }
    std::fs::write(
        std::env::var("LUMA_NEBLA_TRACE_PATH").unwrap(),
        serde_json::to_vec_pretty(&frames).unwrap(),
    )
    .unwrap();
    eprintln!("NEBLA LIVE {mode} PASS: real API → compiled World, trace exported");
}

fn revision_bootstrap(stage: u32, revision: u64) -> Bootstrap {
    let mut value = bootstrap(stage);
    value.player.active_selection_revision = Some(revision);
    value
}
#[test]
fn command_requires_real_revision_and_reuses_ambiguous_intent() {
    let mut view = Presentation {
        eligibility: Some(eligibility(Status::Available)),
        ..Default::default()
    };
    assert!(view.command(Some(&bootstrap(1))).is_none());
    let first = view.command(Some(&revision_bootstrap(1, 7))).unwrap();
    assert_eq!(first.expected_selection_revision, 7);
    assert!(view.command(Some(&revision_bootstrap(1, 7))).is_none());
    view.fail("server unavailable".into());
    // A poll may already show the committed next stage. This remains the same user intent.
    assert_eq!(
        first,
        view.command(Some(&revision_bootstrap(2, 7))).unwrap()
    );
    view.fail("STALE_SELECTION".into());
    let next = view.command(Some(&revision_bootstrap(1, 9))).unwrap();
    assert_ne!(first.command_id, next.command_id);
    assert_eq!(next.expected_selection_revision, 9);
}
#[test]
fn receipt_confirmation_does_not_restore_an_old_selection_or_replay_animation() {
    let mut w = world();
    let original = revision_bootstrap(1, 0);
    w.apply_bootstrap(original.clone());
    w.view.evolution.eligibility = Some(eligibility(Status::Available));
    let request = w.view.evolution.command(Some(&original)).unwrap();
    let mut saved = result(Outcome::Evolved);
    saved.bootstrap.player.active_selection_revision = Some(0);
    let mut live = revision_bootstrap(1, 2);
    live.active_companion.player_companion_id = 2;
    live.active_companion.species = "RUU".into();
    live.active_companion.evolution_name = "RUU".into();
    w.apply_evolved_command(request.clone(), saved.clone(), live.clone(), 1.0);
    assert_eq!(w.view.identity.as_ref().unwrap().species, "RUU");
    assert_eq!(w.view.evolution.phase, Phase::Idle);
    // A duplicate channel delivery cannot overwrite the current bootstrap or start glow.
    w.apply_evolved_command(request, saved.clone(), saved.bootstrap.clone(), 2.0);
    assert_eq!(w.view.identity.as_ref().unwrap().species, "RUU");
    assert_eq!(w.view.evolution.phase, Phase::Idle);
}
#[test]
fn acknowledged_command_plays_once_then_next_user_action_has_new_uuid() {
    let mut view = Presentation {
        eligibility: Some(eligibility(Status::Available)),
        ..Default::default()
    };
    let first = view.command(Some(&revision_bootstrap(1, 0))).unwrap();
    let mut saved = result(Outcome::Evolved);
    saved.bootstrap.player.active_selection_revision = Some(0);
    assert!(view.acknowledge_command(&first, &saved, &saved.bootstrap, None, 1.0));
    assert_eq!(view.phase, Phase::Glow);
    assert!(!view.acknowledge_command(&first, &saved, &saved.bootstrap, None, 1.2));
    view.tick(3.0);
    view.eligibility = Some(eligibility(Status::Available));
    let next = view.command(Some(&revision_bootstrap(2, 0))).unwrap();
    assert_ne!(first.command_id, next.command_id);
    assert_eq!(next.expected_stage, 2);
}
#[test]
fn structured_http_retries_identical_payload_for_all_species_and_stages() {
    use std::{
        io::{Read, Write},
        net::TcpListener,
    };
    for species in ["MOA", "RUU", "NOX"] {
        for stage in 1..=4 {
            let listener = TcpListener::bind("127.0.0.1:0").unwrap();
            let url = format!("http://{}", listener.local_addr().unwrap());
            let request = Request {
                command_id: uuid::Uuid::new_v4(),
                expected_companion_id: 1,
                expected_stage: stage,
                expected_selection_revision: 4,
            };
            let mut response = result(Outcome::Evolved);
            response.bootstrap.player.active_selection_revision = Some(4);
            response.bootstrap.active_companion.species = species.into();
            response.bootstrap.active_companion.evolution_stage = stage + 1;
            response.evolution.species = species.into();
            response.evolution.current_stage = stage + 1;
            response.evolution.next_stage = None;
            response.evolution.next_name = None;
            response.evolution.requirements = None;
            response.evolution.status = if stage == 4 {
                Status::MaxStage
            } else {
                Status::Locked
            };
            let body = serde_json::to_string(&response).unwrap();
            let task = std::thread::spawn(move || {
                let mut payloads = Vec::new();
                for _ in 0..2 {
                    let (mut stream, _) = listener.accept().unwrap();
                    stream
                        .set_read_timeout(Some(std::time::Duration::from_secs(3)))
                        .unwrap();
                    let mut bytes = Vec::new();
                    loop {
                        let mut part = [0; 4096];
                        let n = stream.read(&mut part).unwrap();
                        assert!(n > 0);
                        bytes.extend_from_slice(&part[..n]);
                        let text = String::from_utf8_lossy(&bytes);
                        if let Some((header, data)) = text.split_once("\r\n\r\n") {
                            let length: usize = header
                                .lines()
                                .find_map(|l| {
                                    l.to_ascii_lowercase()
                                        .strip_prefix("content-length: ")
                                        .map(|v| v.parse().unwrap())
                                })
                                .unwrap();
                            if data.len() >= length {
                                assert!(
                                    header.starts_with("POST /api/v1/companions/active/evolve ")
                                );
                                payloads
                                    .push(serde_json::from_str::<serde_json::Value>(data).unwrap());
                                break;
                            }
                        }
                    }
                    write!(
                        stream,
                        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                        body.len(),
                        body
                    )
                    .unwrap();
                }
                payloads
            });
            let api = Api::new(&url).unwrap();
            for _ in 0..2 {
                assert_eq!(
                    api.evolve_command(&request)
                        .unwrap()
                        .bootstrap
                        .active_companion
                        .evolution_stage,
                    stage + 1
                );
            }
            let bodies = task.join().unwrap();
            assert_eq!(bodies[0], serde_json::to_value(&request).unwrap());
            assert_eq!(bodies[0], bodies[1]);
        }
    }
}

#[test]
fn legacy_compatibility_requires_missing_revision_and_original_moa_scope() {
    let mut view = Presentation {
        eligibility: Some(eligibility(Status::Available)),
        ..Default::default()
    };
    assert!(!view.request_legacy(Some(&revision_bootstrap(1, 0))));
    let mut other = bootstrap(1);
    other.active_companion.species = "RUU".into();
    assert!(!view.request_legacy(Some(&other)));
    assert!(!view.request_legacy(Some(&bootstrap(3))));
    assert!(view.request_legacy(Some(&bootstrap(1))));
    assert!(!view.request_legacy(Some(&bootstrap(1))));
    view.fail("server unavailable".into());
    assert!(view.command(Some(&revision_bootstrap(1, 0))).is_some());
    view.fail("server unavailable".into());
    assert!(!view.request_legacy(Some(&bootstrap(1))));
}
