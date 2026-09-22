use super::*;
use crate::{backend::evolution::Status as EvolutionStatus, behaviors::World, entities::Area};
fn world() -> World {
    World::new(
        Area {
            x: 0.0,
            y: 180.0,
            w: 1200.0,
            h: 700.0,
        },
        0.0,
        42,
    )
}
fn purchase() -> Purchase {
    Purchase {
        purchase_id: Uuid::from_u128(1),
        item_code: "SMALL_POTION".into(),
        quantity: 1,
        unit_price: 20,
        total_price: 20,
        gold_after: 7,
        remaining_quantity: 3,
    }
}
fn used(code: &str) -> Used {
    Used {
        item_code: code.into(),
        remaining_quantity: 0,
        healed_amount: None,
        current_hp: None,
        max_hp: None,
        bond_before: None,
        bond_after: None,
        armed: None,
        bonus: None,
        battle_id: None,
    }
}
fn inventory() -> Inventory {
    serde_json::from_value(serde_json::json!({"gold":100,"shop":[{"itemCode":"SMALL_POTION","itemName":"Small Potion","itemType":"BATTLE_CONSUMABLE","price":20,"ownedQuantity":2,"maxStack":99}],"owned":[{"itemCode":"SMALL_POTION","itemName":"Small Potion","itemType":"BATTLE_CONSUMABLE","quantity":2}],"effects":[]})).unwrap()
}
#[test]
fn shop_inventory_wire_contract() {
    let value = inventory();
    assert_eq!(value.shop[0].price, 20);
    assert_eq!(value.owned[0].quantity, 2);
    assert_eq!(serde_json::to_value(value).unwrap()["gold"], 100);
}
#[test]
fn purchase_server_gold_and_quantity_win() {
    let mut p = Presentation {
        inventory: Some(inventory()),
        ..Default::default()
    };
    p.purchase(purchase());
    assert_eq!(p.inventory.as_ref().unwrap().gold, 7);
    assert_eq!(p.inventory.as_ref().unwrap().owned[0].quantity, 3);
    assert_eq!(p.inventory.as_ref().unwrap().shop[0].owned_quantity, 3);
}
#[test]
fn loading_guard_and_no_mutation_retry() {
    let mut p = Presentation::default();
    assert!(matches!(
        p.command("buy:SMALL_POTION", None),
        Some(Command::Purchase(_))
    ));
    assert!(p.command("buy:SMALL_POTION", None).is_none());
    p.finish(Some("server unavailable".into()));
    assert!(!p.busy);
    assert!(p.inventory.is_none());
    assert!(p.feedback.is_none());
    assert!(p.error.is_some());
}
#[test]
fn invalid_context_and_codes_fail_closed() {
    let mut p = Presentation::default();
    assert!(p.command("use:SMALL_POTION", None).is_none());
    assert!(p.command("buy:../fake", None).is_none());
    assert!(matches!(
        p.command("use:BOND_BERRY", None),
        Some(Command::UseItem(_, None))
    ));
}
#[test]
fn potion_actual_heal_presentation() {
    let mut p = Presentation::default();
    let mut u = used("SMALL_POTION");
    u.healed_amount = Some(7);
    u.current_hp = Some(100);
    u.max_hp = Some(100);
    p.used(&u);
    assert_eq!(p.feedback.as_deref(), Some("HP +7"));
}
#[test]
fn berry_actual_bond_presentation() {
    let mut p = Presentation::default();
    let mut u = used("BOND_BERRY");
    u.bond_before = Some(4);
    u.bond_after = Some(5);
    p.used(&u);
    assert_eq!(p.feedback.as_deref(), Some("Bond 4 → 5 ♥"));
}
#[test]
fn charm_presentation_has_no_local_effect_application() {
    let mut p = Presentation::default();
    let mut u = used("CAPTURE_CHARM");
    u.armed = Some(true);
    u.bonus = Some(0.10);
    p.used(&u);
    assert_eq!(p.feedback.as_deref(), Some("Charm Ready"));
    assert!(p.inventory.is_none());
}
#[test]
fn effect_state_deserializes_after_restart() {
    let value:Effect=serde_json::from_value(serde_json::json!({"battleId":Uuid::from_u128(1),"effectType":"CAPTURE_BONUS","value":0.1,"armed":false,"consumedAt":"2026-09-22T00:00:00Z"})).unwrap();
    assert!(!value.armed);
    assert!(value.consumed_at.is_some());
}
fn endpoint(body: String, status: &str) -> (String, std::thread::JoinHandle<String>) {
    use std::{
        io::{Read, Write},
        net::TcpListener,
    };
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let url = format!("http://{}", listener.local_addr().unwrap());
    let status = status.to_owned();
    let task = std::thread::spawn(move || {
        let (mut socket, _) = listener.accept().unwrap();
        socket
            .set_read_timeout(Some(std::time::Duration::from_secs(3)))
            .unwrap();
        let mut bytes = Vec::new();
        let mut chunk = [0; 4096];
        loop {
            let n = socket.read(&mut chunk).unwrap();
            bytes.extend_from_slice(&chunk[..n]);
            if let Some(pos) = bytes.windows(4).position(|s| s == b"\r\n\r\n") {
                let headers = String::from_utf8_lossy(&bytes[..pos]);
                let len = headers
                    .lines()
                    .find_map(|l| {
                        l.to_lowercase()
                            .strip_prefix("content-length:")
                            .and_then(|v| v.trim().parse::<usize>().ok())
                    })
                    .unwrap_or(0);
                if bytes.len() >= pos + 4 + len {
                    break;
                }
            }
            if n == 0 {
                break;
            }
        }
        write!(
            socket,
            "HTTP/1.1 {status}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            body.len()
        )
        .unwrap();
        String::from_utf8(bytes).unwrap()
    });
    (url, task)
}
#[test]
fn purchase_post_contains_only_identifiers_and_quantity() {
    let (url, t) = endpoint(serde_json::to_string(&purchase()).unwrap(), "200 OK");
    let p = Api::new(&url).unwrap().purchase("SMALL_POTION", 1).unwrap();
    assert_eq!(p.gold_after, 7);
    let req = t.join().unwrap();
    assert!(req.starts_with("POST /api/v1/shop/purchases "));
    let json: serde_json::Value =
        serde_json::from_str(req.split_once("\r\n\r\n").unwrap().1).unwrap();
    assert_eq!(
        json,
        serde_json::json!({"itemCode":"SMALL_POTION","quantity":1})
    );
}
#[test]
fn purchase_failure_maps_safe_domain_error() {
    let (url, t) = endpoint(r#"{"code":"INSUFFICIENT_GOLD"}"#.into(), "409 Conflict");
    assert_eq!(
        Api::new(&url)
            .unwrap()
            .purchase("SMALL_POTION", 1)
            .unwrap_err(),
        "INSUFFICIENT_GOLD"
    );
    t.join().unwrap();
}
#[test]
fn item_use_post_cannot_supply_effect_magnitude() {
    let mut u = used("BOND_BERRY");
    u.bond_before = Some(4);
    u.bond_after = Some(5);
    let (url, t) = endpoint(serde_json::to_string(&u).unwrap(), "200 OK");
    assert_eq!(
        Api::new(&url)
            .unwrap()
            .use_item("BOND_BERRY", None)
            .unwrap()
            .bond_after,
        Some(5)
    );
    let request = t.join().unwrap();
    let body: serde_json::Value =
        serde_json::from_str(request.split_once("\r\n\r\n").unwrap().1).unwrap();
    assert_eq!(body, serde_json::json!({"battleId":null}));
}
#[test]
fn malformed_server_values_do_not_apply() {
    let mut p = purchase();
    p.total_price = 999;
    let (url, t) = endpoint(serde_json::to_string(&p).unwrap(), "200 OK");
    assert!(Api::new(&url).unwrap().purchase("SMALL_POTION", 1).is_err());
    t.join().unwrap();
}
#[test]
#[ignore = "requires fresh isolated PG/Spring fixture with success RNG; LUMA_LIVE_TEST_URL"]
fn live_item_economy_world_slice() {
    let api = Api::new(&std::env::var("LUMA_LIVE_TEST_URL").unwrap()).unwrap();
    let mut w = world();
    let position = (w.view.moa.x, w.view.moa.y);
    w.apply_bootstrap(api.bootstrap().unwrap());
    let initial_gold = w.bootstrap.as_ref().unwrap().player.gold;
    // Earn enough gold through ordinary battles, with fixed test-only encounter/capture RNG.
    for _ in 0..10 {
        if let Some(e) = api.encounter(false).unwrap() {
            api.ignore(e.encounter_id).unwrap();
        }
        let e = api.encounter(true).unwrap().unwrap();
        let mut b = api.battle(e.encounter_id, Some("start")).unwrap();
        while b.status == Status::Active {
            b = api.battle(b.battle_id, Some("attack")).unwrap();
        }
        api.ignore(e.encounter_id).unwrap();
    }
    assert!(api.bootstrap().unwrap().player.gold >= initial_gold + 100);
    w.view.items.inventory = Some(api.items(None).unwrap());
    w.view
        .items
        .purchase(api.purchase("SMALL_POTION", 1).unwrap());
    let e = api.encounter(true).unwrap().unwrap();
    crate::spawn::runtime::test_environment(&mut w);
    w.apply_server_encounter(0.0, Some(e.clone()), 60.0);
    let b = api.battle(e.encounter_id, Some("start")).unwrap();
    let damaged = api.battle(b.battle_id, Some("attack")).unwrap();
    assert!(damaged.companion.hp < damaged.companion.max_hp);
    let u = api.use_item("SMALL_POTION", Some(b.battle_id)).unwrap();
    assert!(u.healed_amount.unwrap() > 0);
    w.view.items.used(&u);
    w.apply_battle(api.battle(b.battle_id, None).unwrap());
    assert_eq!(
        w.view.game.battle.as_ref().unwrap().companion.hp,
        u.current_hp.unwrap()
    );
    w.view
        .items
        .purchase(api.purchase("CAPTURE_CHARM", 1).unwrap());
    let armed = api.use_item("CAPTURE_CHARM", Some(b.battle_id)).unwrap();
    assert_eq!(armed.bonus, Some(0.1));
    w.view.items.used(&armed);
    let c = api.capture(b.battle_id).unwrap();
    assert_eq!(c.item_bonus, Some(0.1));
    assert!((c.final_chance.unwrap() - c.base_chance.unwrap() - 0.1).abs() < 1e-9);
    assert!(!api.items(Some(b.battle_id)).unwrap().effects[0].armed);
    w.view
        .items
        .purchase(api.purchase("BOND_BERRY", 1).unwrap());
    let u = api.use_item("BOND_BERRY", None).unwrap();
    w.view.items.used(&u);
    w.apply_bootstrap(api.bootstrap().unwrap());
    assert_eq!(
        w.view.identity.as_ref().unwrap().bond,
        u.bond_after.unwrap()
    );
    assert_eq!(position, (w.view.moa.x, w.view.moa.y));
    eprintln!(
        "ITEM LIVE PASS gold={} heal={:?} charm={:?} bond={:?}",
        w.bootstrap.as_ref().unwrap().player.gold,
        w.view.game.battle.as_ref().unwrap().companion.hp,
        c.item_bonus,
        u.bond_after
    );
}
#[test]
#[ignore = "requires isolated fixture Lv3 Bond4 and >=30G; LUMA_LIVE_TEST_URL and LUMA_GAME_SERVER_URL"]
fn live_berry_evolution_world_slice() {
    let api = Api::new(&std::env::var("LUMA_LIVE_TEST_URL").unwrap()).unwrap();
    let mut w = world();
    assert_eq!(api.evolution().unwrap().status, EvolutionStatus::Locked);
    w.view
        .items
        .purchase(api.purchase("BOND_BERRY", 1).unwrap());
    // Drive the actual bounded worker used by the native action handler, not a local eligibility rule.
    use crate::backend::{Backend, Event};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    let stopped = Arc::new(AtomicBool::new(false));
    let backend = Backend::start(stopped.clone());
    let command = w.view.items.command("use:BOND_BERRY", None).unwrap();
    assert!(backend.request(command));
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(15);
    while w.view.items.busy && std::time::Instant::now() < deadline {
        while let Some(event) = backend.event() {
            match event {
                Event::Bootstrap(b) => w.apply_bootstrap(b),
                Event::Evolution(e) => w.view.evolution.eligibility = Some(e),
                Event::ItemUsed(u) => {
                    assert_eq!((u.bond_before, u.bond_after), (Some(4), Some(5)));
                    w.view.items.used(&u);
                }
                Event::Items(i) => w.view.items.inventory = Some(i),
                Event::ItemsFinished(error) => w.view.items.finish(error),
                _ => {}
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
    stopped.store(true, Ordering::Relaxed);
    assert!(!w.view.items.busy, "worker completion timed out");
    assert!(w.view.items.error.is_none(), "{:?}", w.view.items.error);
    assert_eq!(
        w.view.evolution.eligibility.as_ref().unwrap().status,
        EvolutionStatus::Available
    );
    assert_eq!(w.view.identity.as_ref().unwrap().bond, 5);
    assert_eq!(w.view.identity.as_ref().unwrap().evolution_stage, 1);
    eprintln!("BERRY LIVE PASS bond=5 evolution=AVAILABLE no auto evolution");
}
