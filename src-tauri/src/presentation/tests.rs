use super::*;
fn battle() -> Battle {
    serde_json::from_value(serde_json::json!({"battleId":"00000000-0000-0000-0000-000000000002","encounterId":"00000000-0000-0000-0000-000000000001","turn":1,"status":"ACTIVE","encounterStatus":"ACTIVE","companion":{"hp":95,"maxHp":100},"monster":{"hp":18,"maxHp":30},"events":["PLAYER_ATTACK","MONSTER_ATTACK"],"presentationEvents":[{"type":"PLAYER_ATTACK","damage":12},{"type":"MONSTER_ATTACK","damage":5}],"reward":null})).unwrap()
}
#[test]
fn server_damage_order_and_immutable_hp() {
    let mut c = Controller::default();
    let b = battle();
    let original = b.clone();
    c.request("attack", 0.0);
    c.battle(&b);
    assert!(c.tick(0.0));
    assert_eq!(c.view.phase, Phase::PlayerAttack);
    c.tick(0.15);
    assert_eq!(c.view.phase, Phase::MonsterHit);
    assert_eq!(c.view.damage, Some(12));
    c.tick(0.81);
    assert_eq!(c.view.phase, Phase::MonsterAttack);
    c.tick(0.96);
    assert_eq!(c.view.phase, Phase::PlayerHit);
    assert_eq!(c.view.damage, Some(5));
    c.tick(1.62);
    assert_eq!(c.view.phase, Phase::Idle);
    assert_eq!(b, original);
}
#[test]
fn poll_and_duplicate_do_not_replay() {
    let mut c = Controller::default();
    let b = battle();
    c.battle(&b);
    let n = c.queue.len();
    c.battle(&b);
    assert_eq!(c.queue.len(), n);
    let mut poll = b;
    poll.events.clear();
    c.battle(&poll);
    assert_eq!(c.queue.len(), n);
}
#[test]
fn old_contract_never_guesses_damage() {
    let mut b = battle();
    b.presentation_events.clear();
    let mut c = Controller::default();
    c.battle(&b);
    assert!(!c.tick(0.0));
    assert_eq!(c.view.damage, None);
}
#[test]
fn victory_and_reward_expire() {
    let mut b = battle();
    b.events = vec!["VICTORY".into(), "REWARD".into()];
    b.presentation_events.clear();
    b.reward = Some(Reward {
        gold: 10,
        exp: 20,
        bond: 1,
    });
    let mut c = Controller::default();
    c.battle(&b);
    c.tick(0.0);
    assert_eq!(c.view.phase, Phase::Victory);
    c.tick(0.51);
    assert_eq!(c.view.phase, Phase::Reward);
    assert_eq!(c.view.reward.as_ref().unwrap().gold, 10);
    c.tick(3.02);
    assert_eq!(c.view.phase, Phase::Idle);
}
#[test]
fn capture_request_success_and_failure_counter() {
    for success in [true, false] {
        let mut c = Controller::default();
        c.request("capture", 0.0);
        assert_eq!(c.view.phase, Phase::Capturing);
        let mut b = battle();
        b.events = if success {
            vec![]
        } else {
            vec!["MONSTER_ATTACK".into()]
        };
        b.presentation_events
            .retain(|e| !success && e.r#type == "MONSTER_ATTACK");
        let capture = Capture {
            battle_id: b.battle_id,
            encounter_id: b.encounter_id,
            success,
            chance: 0.6,
            base_chance: None,
            item_bonus: None,
            final_chance: None,
            battle: b,
            collection: None,
        };
        c.capture(&capture, 0.1);
        assert_eq!(
            c.view.phase,
            if success {
                Phase::CaptureSuccess
            } else {
                Phase::CaptureFail
            }
        );
        c.tick(0.51);
        assert_eq!(
            c.view.phase,
            if success {
                Phase::Idle
            } else {
                Phase::MonsterAttack
            }
        );
    }
}
#[test]
fn level_up_only_from_confirmed_same_companion() {
    let mut c = Controller::default();
    let mut b:Bootstrap=serde_json::from_value(serde_json::json!({"player":{"playerId":1,"name":"LOCAL_PLAYER","gold":0},"activeCompanion":{"playerCompanionId":1,"species":"MOA","evolutionStage":1,"evolutionName":"MOA","level":1,"exp":0,"bond":0}})).unwrap();
    c.bootstrap(&b);
    assert!(!c.tick(0.0));
    b.active_companion.level = 2;
    c.bootstrap(&b);
    c.tick(0.1);
    assert_eq!(c.view.phase, Phase::LevelUp);
    assert_eq!(c.view.level.as_ref().unwrap().from, 1);
    assert_eq!(c.view.level.as_ref().unwrap().to, 2);
    c.tick(2.2);
    c.bootstrap(&b);
    assert!(!c.tick(2.3));
}
#[test]
fn network_error_releases_request_visual() {
    let mut c = Controller::default();
    c.request("capture", 0.0);
    c.finish(true, 0.1);
    assert_eq!(c.view.phase, Phase::Error);
    c.tick(2.2);
    assert_eq!(c.view.phase, Phase::Idle);
    c.request("battle", 3.0);
    c.finish(false, 3.1);
    c.tick(3.1);
    assert_eq!(c.view.phase, Phase::Idle);
}
#[test]
fn bounded_queue_and_adaptive_panel_clamp() {
    let mut c = Controller::default();
    let mut b = battle();
    for t in 1..100 {
        b.turn = t;
        c.battle(&b);
    }
    assert!(c.queue.len() <= 24);
    use crate::geometry::*;
    for area in [
        Area {
            x: 0.0,
            y: 192.0,
            w: 1700.0,
            h: 900.0,
        },
        Area {
            x: -1700.0,
            y: -900.0,
            w: 1600.0,
            h: 900.0,
        },
    ] {
        for x in [area.x, area.x + area.w] {
            let (a, y) = area.menu_anchor(x, area.y, PIP_SIZE);
            let bounds = area.panel_bounds(a, y, MENU_SIZE);
            assert!(bounds.x >= area.x);
            assert!(bounds.x + bounds.w <= area.x + area.w);
            assert!(bounds.y >= area.y + PIP_SIZE.height);
            assert!(bounds.y + bounds.h <= area.y + area.h);
            if x == area.x {
                assert!(a > x);
            } else {
                assert!(a < x);
            }
        }
    }
}

#[test]
fn capture_does_not_discard_pending_reward() {
    let mut c = Controller::default();
    let mut b = battle();
    b.events = vec!["VICTORY".into(), "REWARD".into()];
    b.reward = Some(Reward {
        gold: 10,
        exp: 20,
        bond: 1,
    });
    c.battle(&b);
    c.request("capture", 0.0);
    let result = Capture {
        battle_id: b.battle_id,
        encounter_id: b.encounter_id,
        success: true,
        chance: 0.85,
        base_chance: None,
        item_bonus: None,
        final_chance: None,
        battle: b,
        collection: None,
    };
    c.capture(&result, 0.1);
    assert!(c.queue.iter().any(|x| x.phase == Phase::Reward));
}

#[test]
#[ignore = "requires explicit dedicated live Spring Boot / PostgreSQL test server"]
fn live_gameplay_visual_sequence() {
    use crate::backend::Api;
    let api = Api::new(&std::env::var("LUMA_LIVE_TEST_URL").unwrap()).unwrap();
    if let Some(e) = api.encounter(false).unwrap() {
        api.ignore(e.encounter_id).unwrap();
    }
    let mut c = Controller::default();
    c.bootstrap(&api.bootstrap().unwrap());
    let e = api.encounter(true).unwrap().unwrap();
    let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
    let mut now = 0.0;
    let mut phases = vec![];
    let mut damage = vec![];
    while b.status == crate::backend::battle::Status::Active {
        c.request("attack", now);
        b = api.battle(b.battle_id, Some("attack")).unwrap();
        c.battle(&b);
        c.finish(false, now);
        for _ in 0..60 {
            if c.tick(now) {
                phases.push(c.view.phase);
                if let Some(d) = c.view.damage {
                    damage.push(d);
                }
            }
            now += 0.1;
        }
    }
    assert!(phases.contains(&Phase::PlayerAttack));
    assert!(phases.contains(&Phase::MonsterAttack));
    assert!(phases.contains(&Phase::Victory));
    assert!(phases.contains(&Phase::Reward));
    assert!(damage.iter().all(|d| *d > 0));
    c.request("capture", now);
    assert_eq!(c.view.phase, Phase::Capturing);
    let r = api.capture(b.battle_id).unwrap();
    c.capture(&r, now);
    assert_eq!(
        c.view.phase,
        if r.success {
            Phase::CaptureSuccess
        } else {
            Phase::CaptureFail
        }
    );
    eprintln!(
        "LIVE VISUAL encounter={} phases={phases:?} damage={damage:?} capture={}",
        e.encounter_id, r.success
    );
}
