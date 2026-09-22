#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod backend;
mod behaviors;
mod collection_dex;
mod companion;
mod desktop;
mod entities;
mod geometry;
mod monster_behavior;
mod movement;
mod overlay;
mod presentation;
pub mod spawn;
use behaviors::{Snapshot, World};
use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};
use tauri::{Emitter, Manager};
struct State {
    world: Mutex<World>,
    start: Instant,
    backend: Mutex<backend::Backend>,
    #[cfg(debug_assertions)]
    visual_smoke: Mutex<Option<presentation::smoke::Driver>>,
}
#[tauri::command]
fn snapshot(state: tauri::State<State>) -> Snapshot {
    state.world.lock().unwrap().view.clone()
}
#[tauri::command]
fn action(kind: String, app: tauri::AppHandle) -> Result<(), String> {
    app.clone()
        .run_on_main_thread(move || {
            let state = app.state::<State>();
            let now = state.start.elapsed().as_secs_f64();
            let mut world = state.world.lock().unwrap();
            eprintln!("[LUMA INPUT] {kind}");
            match kind.as_str() {
                "spawn" => world.debug_spawn(now), // explicit developer-only path

                "drag" => world.drag(now, overlay::cursor().0),
                "interact" => world.interact(),
                "close" => world.close(),
                "evolution" => world.open_evolution(),
                "dex" | "dex-refresh" => {
                    world.view.menu = true;
                    world.view.interaction = behaviors::InteractionMode::Dex;
                }
                "shop" | "inventory" | "battle-items" => {
                    world.view.menu = true;
                    world.view.interaction = match kind.as_str() {
                        "shop" => behaviors::InteractionMode::Shop,
                        "battle-items" => behaviors::InteractionMode::BattleItems,
                        _ => behaviors::InteractionMode::Inventory,
                    };
                }

                _ => {}
            }
            if !world.view.game.busy && !world.view.evolution.busy {
                let battle = world.view.game.battle.clone();
                if let Some(command) = world.view.items.command(&kind, battle.as_ref()) {
                    if !state.backend.lock().unwrap().request(command) {
                        world
                            .view
                            .items
                            .finish(Some("Request queue unavailable".into()));
                    }
                }
            }
            if kind == "evolve"
                && !world.view.items.busy
                && !world.view.game.busy
                && world.view.evolution.request()
                && !state
                    .backend
                    .lock()
                    .unwrap()
                    .request(backend::battle::Command::Evolve)
            {
                world
                    .view
                    .evolution
                    .fail("Request queue unavailable".into());
            }
            if !world.view.evolution.busy && !world.view.items.busy {
                let dex_request = matches!(kind.as_str(), "dex" | "dex-refresh");
                let game_action = if dex_request { "collection" } else { &kind };
                if let Some(command) = world.view.game.command(game_action) {
                    if dex_request {
                        world.view.dex.begin();
                    }
                    world.presentation.request(&kind, now);
                    if !state.backend.lock().unwrap().request(command) {
                        world.view.game.busy = false;
                        world.view.game.error = Some("Request queue unavailable".into());
                        world
                            .view
                            .dex
                            .finish(Some("Request queue unavailable".into()));
                        world.presentation.finish(true, now);
                    }
                }
            }
            state.backend.lock().unwrap().set_open(world.view.menu);
            world.view.visual = world.presentation.view.clone();
            let _ = app.emit("world", &world.view);
        })
        .map_err(|e| e.to_string())
}
fn main() {
    unsafe { overlay::luma_focus_audit_start() };
    let stopped = Arc::new(AtomicBool::new(false));
    let stop_setup = stopped.clone();
    let mut app = tauri::Builder::default()
        // Register first: a secondary exits before setup creates any entities/panels.
        // Deliberately ignore args/cwd; never focus, activate or reopen the primary.
        .plugin(tauri_plugin_single_instance::init(|_, _, _| {}))
        .invoke_handler(tauri::generate_handler![snapshot, action])
        .setup(move |app| {
            unsafe { overlay::luma_init() };
            for (index, label, w, h) in [
                (
                    0,
                    "moa",
                    geometry::MOA_SIZE.width,
                    geometry::MOA_SIZE.height,
                ),
                (
                    1,
                    "pip",
                    geometry::PIP_SIZE.width,
                    geometry::PIP_SIZE.height,
                ),
                (
                    2,
                    "interaction",
                    geometry::MENU_SIZE.width,
                    geometry::MENU_SIZE.height,
                ),
            ] {
                let window = tauri::WebviewWindowBuilder::new(
                    app,
                    label,
                    tauri::WebviewUrl::App(format!("index.html?entity={label}").into()),
                )
                .title(label)
                .inner_size(w, h)
                .visible(false)
                .focused(false)
                .focusable(false)
                .decorations(false)
                .transparent(true)
                .shadow(false)
                .always_on_top(true)
                .resizable(false)
                .accept_first_mouse(true)
                .build()?;
                unsafe { overlay::luma_attach(window.ns_window()?, index, w, h) };
            }
            let start = Instant::now();
            app.manage(State {
                world: Mutex::new(World::new(
                    overlay::area(),
                    0.0,
                    SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos() as u64,
                )),
                start,
                backend: Mutex::new(backend::Backend::start(stop_setup.clone())),
                #[cfg(debug_assertions)]
                visual_smoke: Mutex::new(
                    std::env::var_os("LUMA_VISUAL_SMOKE").map(|_| Default::default()),
                ),
            });
            app.state::<State>()
                .world
                .lock()
                .unwrap()
                .spawn_runtime
                .load_assets(|path| {
                    app.asset_resolver()
                        .get(path.to_owned())
                        .map(|asset| asset.bytes)
                });
            let handle = app.handle().clone();
            // Bounded dispatch: at most one outstanding tick even if AppKit is busy.
            let pending = Arc::new(AtomicBool::new(false));
            std::thread::spawn(move || {
                let mut last = Instant::now();
                let smoke = std::env::var_os("LUMA_SMOKE").is_some();
                let mut smoke_phase = 0;
                let visual_audit = std::env::var_os("LUMA_VISUAL_AUDIT").is_some();
                while !stop_setup.load(Ordering::Relaxed) {
                    std::thread::sleep(Duration::from_millis(33));
                    if pending.swap(true, Ordering::SeqCst) {
                        continue;
                    }
                    let dt = last.elapsed().as_secs_f64();
                    last = Instant::now();
                    let app = handle.clone();
                    let done = pending.clone();
                    let phase = if smoke {
                        let t = app.state::<State>().start.elapsed().as_secs();
                        let p = match t {
                            0..=1 => 0,
                            2..=3 => 1,
                            4..=5 => 2,
                            6..=7 => 3,
                            8..=9 => 4,
                            _ => 5,
                        };
                        if p > smoke_phase {
                            smoke_phase = p;
                            p
                        } else {
                            0
                        }
                    } else {
                        0
                    };
                    if handle
                        .run_on_main_thread(move || {
                            let state = app.state::<State>();
                            let now = state.start.elapsed().as_secs_f64();
                            let mut world = state.world.lock().unwrap();
                            world.area = overlay::area();
                            let (spawn_cursor, _) = overlay::cursor();
                            world.set_spawn_environment(
                                overlay::desktop_sample(),
                                spawn_cursor,
                                overlay::movement_windows(),
                            );
                            let mut backend_changed = false;
                            while let Some(event) = state.backend.lock().unwrap().event() {
                                backend_changed = true;
                                match event {
                                    backend::Event::SpawnCompleted(action, result) => {
                                        world.complete_spawn(now, action, result)
                                    }
                                    backend::Event::Items(value) => {
                                        world.view.items.inventory = Some(value);
                                    }
                                    backend::Event::Purchased(value) => {
                                        world.view.items.purchase(value)
                                    }
                                    backend::Event::ItemUsed(value) => {
                                        world.view.items.used(&value)
                                    }
                                    backend::Event::ItemsFinished(error) => {
                                        world.view.items.finish(error)
                                    }
                                    backend::Event::Evolution(value) => {
                                        world.view.evolution.eligibility = Some(value);
                                        if !world.view.evolution.busy {
                                            world.view.evolution.error = None;
                                        }
                                    }
                                    backend::Event::Evolved(value) => {
                                        world.apply_evolved(value, now)
                                    }
                                    backend::Event::EvolutionUnavailable(error) => {
                                        world.view.evolution.eligibility = None;
                                        world.view.evolution.error = Some(error);
                                    }
                                    backend::Event::EvolutionFailed(error) => {
                                        world.view.evolution.fail(error)
                                    }
                                    backend::Event::Battle(value) => world.apply_battle(value),
                                    backend::Event::Capture(value) => {
                                        world.presentation.capture(&value, now);
                                        world.view.game.capture_chance = Some(value.chance);
                                        world.view.game.capture_base_chance = value.base_chance;
                                        world.view.game.capture_item_bonus = value.item_bonus;
                                        world.view.game.capture_final_chance = value.final_chance;
                                        world.apply_battle(value.battle);
                                        world.view.game.feedback = Some(
                                            if value.success {
                                                "Captured"
                                            } else {
                                                "Capture failed"
                                            }
                                            .into(),
                                        );
                                        if let Some(c) = value.collection {
                                            world.view.dex.captured(&c);
                                            world.view.game.collection = vec![c];
                                        }
                                    }
                                    backend::Event::Collection(value) => {
                                        world.view.dex.loaded(value.clone());
                                        world.view.game.collection = value
                                    }
                                    backend::Event::Finished(error) => {
                                        world.presentation.finish(error.is_some(), now);
                                        world.view.dex.finish(error.clone());
                                        world.view.game.finish(error);
                                    }
                                    backend::Event::Bootstrap(value) => {
                                        world.apply_bootstrap(value)
                                    }
                                    backend::Event::Encounter(value) => {
                                        // Compute from the server timestamp when consumed, not when queued.
                                        let remaining = value
                                            .as_ref()
                                            .map_or(0.0, |e| e.remaining_at(chrono::Utc::now()));
                                        world.apply_server_encounter(now, value, remaining)
                                    }
                                }
                            }
                            let previous_visual = world.view.visual.serial;
                            #[cfg(debug_assertions)]
                            if let Some(driver) = state.visual_smoke.lock().unwrap().as_mut() {
                                if driver.tick(&mut world, &state.backend.lock().unwrap(), now) {
                                    app.exit(0);
                                }
                            }
                            let visual_changed = world.presentation.tick(now);
                            let evolution_changed = world.view.evolution.tick(now);
                            world.view.visual = world.presentation.view.clone();
                            if backend_changed
                                || visual_changed
                                || evolution_changed
                                || world.view.visual.serial != previous_visual
                            {
                                if visual_audit {
                                    eprintln!(
                                        "[LUMA VISUAL] phase={:?} serial={} damage={:?}",
                                        world.view.visual.phase,
                                        world.view.visual.serial,
                                        world.view.visual.damage
                                    );
                                }
                                let _ = app.emit("world", &world.view);
                            }
                            world.area = overlay::area();
                            let (cursor, down) = overlay::cursor();
                            match unsafe { overlay::luma_action() } {
                                1 => world.debug_spawn(now),
                                2 => world.despawn(now),
                                3 => {
                                    app.exit(0);
                                }
                                _ => {}
                            }
                            match phase {
                                1 => world.debug_spawn(now),
                                2 => world.interact(),
                                3 => world.close(),
                                4 => world.despawn(now),
                                5 => {
                                    eprintln!("[LUMA SMOKE] normal exit");
                                    app.exit(0);
                                }
                                _ => {}
                            }
                            world.set_movement_windows(overlay::movement_windows());
                            world.tick(now, dt, cursor, down);
                            if let Some(action) = world.spawn_action(now) {
                                if !state
                                    .backend
                                    .lock()
                                    .unwrap()
                                    .request(backend::battle::Command::Spawn(action))
                                {
                                    world.complete_spawn(
                                        now,
                                        action,
                                        Err("backend queue busy".into()),
                                    );
                                }
                            }
                            let view = &world.view;
                            unsafe {
                                overlay::place_entity(0, &view.moa, world.area);
                                if let Some(p) = &view.pip {
                                    overlay::place_entity(1, p, world.area);
                                } else {
                                    overlay::luma_place(1, 0.0, 0.0, 0);
                                }
                                // Keep a compact terminal result available until Close, even after PIP despawns.
                                let (anchor_x, anchor_y, anchor_size) = view
                                    .pip
                                    .as_ref()
                                    .filter(|_| {
                                        matches!(
                                            view.interaction,
                                            behaviors::InteractionMode::Encounter
                                                | behaviors::InteractionMode::BattleItems
                                        )
                                    })
                                    .map_or((view.moa.x, view.moa.y, view.moa.size), |p| {
                                        (p.x, p.y, p.size)
                                    });
                                let a = world.area;
                                let size = geometry::MENU_SIZE;
                                let (x, y) = a.menu_anchor(anchor_x, anchor_y, anchor_size);
                                let bounds = a.panel_bounds(x, y, size);
                                overlay::luma_place(
                                    2,
                                    bounds.x,
                                    bounds.y,
                                    (view.menu && a.fits(size)) as i32,
                                );
                            }
                            state.backend.lock().unwrap().set_open(view.menu);
                            // State events only: positions are native; no 30Hz React rendering.
                            let key = format!(
                                "{:?}:{:?}:{}:{}",
                                view.moa.state,
                                view.pip.as_ref().map(|p| (p.state, p.facing)),
                                view.moa.facing,
                                view.menu
                            );
                            LAST_KEY.with(|last| {
                                if *last.borrow() != key {
                                    eprintln!(
                                        "[LUMA STATE] t={now:.2} {key} moa=({:.1},{:.1}) pip={:?}",
                                        view.moa.x,
                                        view.moa.y,
                                        view.pip.as_ref().map(|p| (p.x, p.y))
                                    );
                                    if let Err(e) = app.emit("world", view) {
                                        eprintln!("[LUMA] emit: {e}");
                                    }
                                    *last.borrow_mut() = key;
                                }
                            });
                            ACTIVE.with(|last| {
                                let active = unsafe { overlay::luma_is_active() };
                                if active != last.get() {
                                    eprintln!("[LUMA FOCUS] app active={active} t={now:.2}");
                                    last.set(active);
                                }
                            });
                            done.store(false, Ordering::SeqCst);
                        })
                        .is_err()
                    {
                        break;
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("LUMA initialization failed");
    // Official pre-run API: policy is applied by Tao before launch handling.
    // The opt-in Tao patch removes startup activation requests (not restoration).
    app.set_activation_policy(tauri::ActivationPolicy::Accessory);
    app.run(move |_, event| {
        if let tauri::RunEvent::Exit = event {
            stopped.store(true, Ordering::Relaxed);
            unsafe {
                overlay::luma_cleanup();
                overlay::luma_focus_audit_end();
            };
            eprintln!("[LUMA EXIT] panels and status item cleaned");
        }
    });
}
thread_local! {static LAST_KEY:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static ACTIVE:std::cell::Cell<i32>=const{std::cell::Cell::new(-1)};}
