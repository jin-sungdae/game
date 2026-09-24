//! Opt-in certification against an actual bootJar and a newly migrated isolated DB.
//! Only the World clock/environment are injected; server RNG/rewards are production.
use super::*;
use crate::{behaviors::World, entities::Area};
use chrono::Timelike;
use serde_json::{json, Value};
use std::path::PathBuf;

struct Night;
impl crate::spawn::conditions::CalendarClock for Night {
    fn local_now(&self) -> chrono::DateTime<chrono::FixedOffset> {
        // Preserve the actual UTC instant/lease while making local calendar hour22.
        let utc = Utc::now();
        utc.with_timezone(&chrono::FixedOffset::east_opt((22 - utc.hour() as i32) * 3600).unwrap())
    }
}
fn world(api: Option<&Api>) -> World {
    let mut w = World::new(
        Area {
            x: 0.,
            y: 0.,
            w: 1800.,
            h: 1000.,
        },
        0.,
        42,
    );
    crate::spawn::runtime::test_environment(&mut w);
    w.spawn_runtime.set_test_calendar(Box::new(Night));
    if let Some(api) = api {
        refresh(api, &mut w);
    }
    w
}
fn refresh(api: &Api, w: &mut World) {
    w.apply_bootstrap(api.bootstrap().unwrap());
    w.view.evolution.eligibility = Some(api.evolution().unwrap());
    w.view.items.inventory = Some(api.items(None).unwrap());
    w.view.dex.loaded_dex(&api.dex().unwrap());
}
fn output() -> PathBuf {
    PathBuf::from(std::env::var("LUMA_ALPHA_OUTPUT").unwrap())
}
fn save(name: &str, value: &Value) {
    std::fs::write(
        output().join(name),
        serde_json::to_vec_pretty(value).unwrap(),
    )
    .unwrap();
}
fn read(name: &str) -> Value {
    serde_json::from_slice(&std::fs::read(output().join(name)).unwrap()).unwrap()
}
fn state(api: &Api) -> Value {
    json!({"bootstrap":api.bootstrap().unwrap(),"inventory":api.items(None).unwrap(),
           "dex":api.request::<Value>("/api/v1/dex",false).unwrap().unwrap(),
           "collection":api.request::<Value>("/api/v1/collection",false).unwrap().unwrap(),
           "evolution":api.evolution().unwrap()})
}
fn frame(label: &str, w: &World) -> Value {
    json!({"label":label,"snapshot":w.view})
}
fn spawn(api: &Api, w: &mut World, now: &mut f64) -> Encounter {
    for _ in 0..12 {
        if let Some(action) = w.spawn_action(*now) {
            let result = api.spawn_action(action).unwrap();
            let created = result.clone();
            w.complete_spawn(*now, action, Ok(result));
            if let Some(e) = created {
                assert!(
                    w.view.pip.is_some(),
                    "production placement {}",
                    e.monster.code
                );
                assert_eq!(
                    w.view.monster.as_ref().unwrap().monster_code,
                    e.monster.code
                );
                return e;
            }
        }
        *now += 301.; // Test World clock only; no cooldown configuration changed.
    }
    panic!("bounded automatic Director never produced an encounter");
}
fn discover(api: &Api, w: &mut World, now: f64) {
    while let Some(job) = w.discovery.next(now) {
        let row = api.discover(&job).unwrap();
        w.discovery.complete(&job, now, true, true);
        w.view.dex.acknowledged(&row);
    }
}
fn evolve(api: &Api, w: &mut World, now: f64, frames: &mut Vec<Value>, name: &str) {
    refresh(api, w);
    assert!(w.view.evolution.request());
    frames.push(frame(&format!("{name}-before-ack"), w));
    let result = api.evolve().unwrap();
    assert_eq!(result.result, evolution::Outcome::Evolved);
    w.apply_evolved(result, now);
    frames.push(frame(&format!("{name}-glow"), w));
    w.view.evolution.tick(now + 0.9);
    frames.push(frame(&format!("{name}-reveal"), w));
    w.view.evolution.tick(now + 2.);
    assert_eq!(
        api.evolve().unwrap().result,
        evolution::Outcome::AlreadyEvolved
    );
}
fn berries(api: &Api, w: &mut World, count: u32) {
    api.purchase("BOND_BERRY", count).unwrap();
    for _ in 0..count {
        let before = api.bootstrap().unwrap();
        let u = api.use_item("BOND_BERRY", None).unwrap();
        assert_eq!(u.bond_after, Some(before.active_companion.bond + 1));
    }
    refresh(api, w);
}
#[test]
#[ignore = "actual isolated PostgreSQL16/bootJar; use scripts/analysis/run_alpha_vertical_slice.py"]
fn live_alpha_vertical_slice() {
    let api = Api::new(&std::env::var("LUMA_GAME_SERVER_URL").unwrap()).unwrap();
    let phase = std::env::var("LUMA_ALPHA_PHASE").unwrap();
    if phase == "offline" {
        let before = read("discovered.json");
        let mut w = world(None);
        w.apply_bootstrap(serde_json::from_value(before["bootstrap"].clone()).unwrap());
        let original = serde_json::to_value(&w.view.identity).unwrap();
        assert!(api.bootstrap().is_err());
        w.view.bond.request();
        w.apply_companion_interaction(api.interact_companion().map_err(str::to_owned), 0.);
        assert_eq!(original, serde_json::to_value(&w.view.identity).unwrap());
        let e: Encounter = serde_json::from_value(read("first-encounter.json")).unwrap();
        w.discovery.placed(e.encounter_id, &e.monster.code, 0.);
        for now in [0., 5., 20., 50.] {
            let job = w.discovery.next(now).unwrap();
            assert!(api.discover(&job).is_err());
            w.discovery.complete(&job, now, false, true);
        }
        assert!(w.discovery.next(999.).is_none());
        save(
            "offline.json",
            &json!({"serverUnavailable":"PASS","interactionUnchanged":"PASS","discoveryAttempts":4,"automaticRetriesExhausted":true}),
        );
        return;
    }
    let mut w = world(Some(&api));
    let mut now = 0.;
    if phase == "fresh" {
        let b = api.bootstrap().unwrap();
        assert_eq!(
            (
                b.active_companion.evolution_stage,
                b.active_companion.level,
                b.active_companion.exp,
                b.active_companion.bond,
                b.player.gold
            ),
            (1, 1, 0, 0, 0)
        );
        assert_eq!(b.active_companion.evolution_name, "MOA");
        assert!(api.items(None).unwrap().owned.is_empty());
        assert!(api
            .dex()
            .unwrap()
            .iter()
            .all(|r| r.state == "UNDISCOVERED" && r.monster_code.is_none()));
        save("fresh.json", &state(&api));
        save("frames-fresh.json", &json!([frame("fresh-moa", &w)]));
        let e = spawn(&api, &mut w, &mut now);
        // DTO receipt/placement is not itself persisted; acknowledgement is explicit.
        assert!(api.dex().unwrap().iter().all(|r| r.state == "UNDISCOVERED"));
        assert!(w.discovery.contains(&e.monster.code));
        discover(&api, &mut w, now);
        let row = api
            .dex()
            .unwrap()
            .into_iter()
            .find(|r| r.monster_code.as_deref() == Some(&e.monster.code))
            .unwrap();
        assert_eq!(row.state, "DISCOVERED");
        assert_eq!(row.capture_count, 0);
        api.ignore(e.encounter_id).unwrap();
        let first = api.interact_companion().unwrap();
        assert_eq!(first.bond_delta, 1);
        w.apply_companion_interaction(Ok(first.clone()), now);
        let cooldown = api.interact_companion().unwrap();
        assert_eq!(cooldown.bond_delta, 0);
        assert_eq!(first.next_available_at, cooldown.next_available_at);
        save("first-encounter.json", &json!(e));
        save("discovered.json", &state(&api));
        save("interaction-first.json", &json!(first));
        return;
    }
    if phase == "restored" {
        assert_eq!(state(&api), read("final-state.json"));
        assert_eq!(w.view.identity.as_ref().unwrap().evolution_name, "NEBLA");
        assert_eq!(w.view.evolution.phase, evolution::Phase::Idle);
        save(
            "frames-restored.json",
            &json!([frame("restored-nebla", &w)]),
        );
        save("restored-state.json", &state(&api));
        return;
    }
    assert_eq!(phase, "progress");
    let initial = read("discovered.json");
    assert_eq!(state(&api), initial);
    let first_code = read("first-encounter.json")["monster"]["code"]
        .as_str()
        .unwrap()
        .to_owned();
    assert!(w.view.dex.discovered_codes.contains(&first_code));
    assert!(w.view.dex.records.as_ref().unwrap().is_empty());
    // Runner advances ONLY persisted interaction clock after restart, not progression.
    let second = api.interact_companion().unwrap();
    assert_eq!(second.bond_delta, 1);
    assert_eq!(second.bootstrap.active_companion.bond, 2);
    w.apply_companion_interaction(Ok(second), 0.);
    let mut frames = vec![frame("discovery-restored", &w)];
    let mut log = vec![];
    let (
        mut wins,
        mut captures,
        mut capture_failures,
        mut mokori_wins,
        mut potion_used,
        mut charm_used,
    ) = (0, 0, 0, 0, false, false);
    let (mut potion_bought, mut charm_bought, mut bond8) = (false, false, false);
    for encounter_number in 1..=100 {
        let boot = api.bootstrap().unwrap();
        if !charm_bought && boot.player.gold >= 40 {
            let p = api.purchase("CAPTURE_CHARM", 1).unwrap();
            assert_eq!(p.gold_after, boot.player.gold - 40);
            charm_bought = true;
            // First threshold crossing earns at most60G: same purchase cannot overdraw.
            assert!(api.purchase("CAPTURE_CHARM", 1).is_err());
        }
        if !potion_bought && api.bootstrap().unwrap().player.gold >= 20 {
            api.purchase("SMALL_POTION", 1).unwrap();
            potion_bought = true;
        }
        let e = spawn(&api, &mut w, &mut now);
        discover(&api, &mut w, now);
        let before = api.bootstrap().unwrap();
        let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
        w.apply_battle(b.clone());
        if charm_bought && !charm_used {
            let u = api.use_item("CAPTURE_CHARM", Some(b.battle_id)).unwrap();
            assert_eq!(u.bonus, Some(0.1));
            assert!(api.use_item("CAPTURE_CHARM", Some(b.battle_id)).is_err());
            let c = api.capture(b.battle_id).unwrap();
            assert_eq!(c.item_bonus, Some(0.1));
            assert!((c.chance - (c.base_chance.unwrap() + 0.1).clamp(0.05, 0.95)).abs() < 1e-9);
            if c.success {
                captures += 1;
            } else {
                capture_failures += 1;
            }
            b = c.battle;
            charm_used = true;
        }
        while b.status == battle::Status::Active {
            if potion_bought && !potion_used && b.companion.hp < b.companion.max_hp {
                let u = api.use_item("SMALL_POTION", Some(b.battle_id)).unwrap();
                assert_eq!(
                    u.healed_amount,
                    Some(30.min(b.companion.max_hp - b.companion.hp))
                );
                assert!(api.use_item("SMALL_POTION", Some(b.battle_id)).is_err());
                potion_used = true;
            }
            b = api.battle(b.battle_id, Some("attack")).unwrap();
            w.apply_battle(b.clone());
        }
        if b.status == battle::Status::Victory {
            wins += 1;
            let reward = b.reward.as_ref().unwrap();
            assert_eq!(
                (reward.exp, reward.gold, reward.bond),
                (
                    u64::from(e.monster.level) * 20,
                    u64::from(e.monster.level) * 10,
                    0
                )
            );
            let c = api.capture(b.battle_id).unwrap();
            if c.success {
                captures += 1;
            } else {
                capture_failures += 1;
            }
            assert!(api.capture(b.battle_id).is_err());
            let after = api.bootstrap().unwrap();
            assert_eq!(after.active_companion.bond, before.active_companion.bond);
            assert_eq!(
                after.active_companion.exp,
                before.active_companion.exp + reward.exp
            );
        }
        w.apply_server_encounter(now, None, 0.);
        w.tick(now + 1., 0.1, (-9999., -9999.), false);
        now += 2.;
        refresh(&api, &mut w);
        let c = w.view.identity.as_ref().unwrap().clone();
        log.push(json!({"encounter":encounter_number,"code":e.monster.code,"monsterLevel":e.monster.level,"wins":wins,"bootstrap":api.bootstrap().unwrap()}));
        if c.level >= 3 && c.evolution_stage == 1 && potion_bought && charm_bought {
            berries(&api, &mut w, 3);
            assert_eq!(w.view.identity.as_ref().unwrap().bond, 5);
            evolve(&api, &mut w, now, &mut frames, "mokori");
            mokori_wins = wins;
        }
        if c.level >= 5 && !bond8 {
            berries(&api, &mut w, 3);
            bond8 = true;
            frames.push(frame("mokori-level5-bond8", &w));
        }
        if c.level >= 6 {
            assert_eq!(api.bootstrap().unwrap().active_companion.bond, 8);
            assert_eq!(api.evolution().unwrap().status, evolution::Status::Locked);
            berries(&api, &mut w, 3);
            assert_eq!(api.bootstrap().unwrap().active_companion.bond, 11);
            assert_eq!(api.evolution().unwrap().status, evolution::Status::Locked);
            frames.push(frame("level6-bond11-locked", &w));
            berries(&api, &mut w, 1);
            assert_eq!(
                api.evolution().unwrap().status,
                evolution::Status::Available
            );
            evolve(&api, &mut w, now, &mut frames, "nebla");
            break;
        }
    }
    assert!(potion_used && charm_used && captures > 0 && capture_failures > 0);
    let b = api.bootstrap().unwrap();
    assert_eq!(
        (
            b.active_companion.evolution_stage,
            b.active_companion.level,
            b.active_companion.bond
        ),
        (3, 6, 12)
    );
    assert_eq!(b.player.gold, b.active_companion.exp / 2 - 360);
    refresh(&api, &mut w);
    frames.push(frame("final-nebla", &w));
    save("frames-progress.json", &json!(frames));
    save("battle-log.json", &json!(log));
    save("final-state.json", &state(&api));
    save(
        "summary.json",
        &json!({"mokoriWins":mokori_wins,"neblaWins":wins,"interactionsAwarded":2,"berriesUsed":10,"potionUsed":1,"charmUsed":1,"goldEarned":b.active_companion.exp/2,"goldSpent":360,"goldRemaining":b.player.gold,"captureSuccesses":captures,"captureFailures":capture_failures,"final":b}),
    );
}
