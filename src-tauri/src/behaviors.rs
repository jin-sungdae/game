use crate::companion::{
    config::{MOA_BEHAVIOR, MOA_PERSONALITY},
    CompanionController,
};
use crate::entities::*;
use serde::Serialize;
#[derive(Clone, Copy, Default, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum InteractionMode {
    #[default]
    Encounter,
    Evolution,
    Shop,
    Inventory,
    BattleItems,
    Dex,
}
#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub animation: crate::presentation::animation::Motion,
    pub moa: Entity<CompanionState>,
    pub pip: Option<Entity<PipState>>,
    pub monster: Option<crate::spawn::MonsterIdentity>,
    pub menu: bool,
    pub interaction: InteractionMode,
    pub identity: Option<crate::backend::Companion>,
    pub evolution: crate::backend::evolution::Presentation,
    pub items: crate::backend::items::Presentation,
    pub bond: crate::backend::companion_interaction::Presentation,
    pub game: crate::backend::battle::Presentation,
    pub dex: crate::collection_dex::Presentation,
    pub visual: crate::presentation::Visual,
}
struct SpawnEnvironment {
    safe: crate::desktop::DesktopSafeArea,
    cursor: (f64, f64),
    windows: Option<Vec<Area>>,
}
pub struct World {
    pub discovery: crate::discovery_sync::Sync,
    pub spawn_runtime: crate::spawn::runtime::Runtime,
    spawn_environment: Option<SpawnEnvironment>,
    monster_movement: crate::movement::MovementController,
    monster_behavior: Option<crate::monster_behavior::Controller>,
    behavior_seed: u64,
    pub view: Snapshot,
    pub area: Area,
    companion: CompanionController,
    pip_deadline: f64,
    pub bootstrap: Option<crate::backend::Bootstrap>,
    pub presentation: crate::presentation::Controller,
    server_encounter: Option<(uuid::Uuid, f64)>,
}
impl World {
    pub fn new(area: Area, now: f64, seed: u64) -> Self {
        let companion = CompanionController::new(area, now, seed, MOA_PERSONALITY, MOA_BEHAVIOR);
        Self {
            view: Snapshot {
                animation: Default::default(),
                moa: companion.entity().clone(),
                pip: None,
                monster: None,
                menu: false,
                interaction: Default::default(),
                identity: None,
                evolution: Default::default(),
                items: Default::default(),
                bond: Default::default(),
                game: Default::default(),
                dex: Default::default(),
                visual: Default::default(),
            },
            area,
            companion,
            pip_deadline: 0.0,
            bootstrap: None,
            presentation: Default::default(),
            server_encounter: None,
            spawn_runtime: crate::spawn::runtime::Runtime::new(seed),
            discovery: crate::discovery_sync::Sync::default(),
            spawn_environment: None,
            monster_movement: Default::default(),
            monster_behavior: None,
            behavior_seed: seed,
        }
    }
    pub fn apply_battle(&mut self, value: crate::backend::battle::Battle) {
        if self.view.game.encounter_id != Some(value.encounter_id) {
            return;
        }
        // An authoritative ACTIVE battle response suspends the old spawn lease immediately,
        // even if the following encounter reconciliation HTTP request is delayed.
        if value.status == crate::backend::battle::Status::Active
            && value.encounter_status == "ACTIVE"
        {
            if let Some((id, deadline)) = &mut self.server_encounter {
                if *id == value.encounter_id {
                    *deadline = f64::MAX / 2.0;
                    self.spawn_runtime.deadline = f64::MAX / 2.0;
                }
            }
        }
        self.presentation.battle(&value);
        self.view.game.apply_battle(value);
    }
    pub fn apply_bootstrap(&mut self, value: crate::backend::Bootstrap) {
        eprintln!(
            "[LUMA BACKEND] bootstrap player={} companion={}/stage{}",
            value.player.player_id,
            value.active_companion.species,
            value.active_companion.evolution_stage
        );
        self.presentation.bootstrap(&value);
        self.view.identity = Some(value.active_companion.clone());
        self.bootstrap = Some(value);
    }
    pub fn apply_evolved(&mut self, value: crate::backend::evolution::Result, now: f64) {
        self.view
            .evolution
            .acknowledge(&value, self.view.identity.clone(), now);
        self.apply_bootstrap(value.bootstrap);
    }
    pub fn take_companion_click(&mut self) -> bool {
        self.companion.take_click()
    }
    pub fn apply_companion_interaction(
        &mut self,
        result: Result<crate::backend::companion_interaction::Result, String>,
        now: f64,
    ) {
        match result {
            Ok(value) => {
                self.view.bond.acknowledge(&value, now);
                self.view.evolution.eligibility = Some(value.evolution);
                self.apply_bootstrap(value.bootstrap);
            }
            Err(error) => {
                eprintln!("[LUMA BOND] {error}; no local reward or automatic retry");
                self.view.bond.fail();
            }
        }
    }
    pub fn open_evolution(&mut self) {
        self.view.interaction = InteractionMode::Evolution;
        self.view.menu = true;
    }
    pub fn apply_server_encounter(
        &mut self,
        now: f64,
        value: Option<crate::backend::Encounter>,
        remaining: f64,
    ) {
        self.spawn_runtime.observe(now, value.clone(), remaining);
        let Some(encounter) = value else {
            if self.server_encounter.take().is_some() {
                self.despawn(now);
            }
            return;
        };
        if self.view.game.encounter_id != Some(encounter.encounter_id) {
            self.view.game.battle = None;
            self.view.game.feedback = None;
            self.view.game.capture_chance = None;
            self.view.game.capture_base_chance = None;
            self.view.game.capture_item_bonus = None;
            self.view.game.capture_final_chance = None;
        }
        self.view.game.encounter_id = Some(encounter.encounter_id);
        self.view.game.monster_level = encounter.monster.level;
        if self.server_encounter.as_ref().map(|e| e.0) != Some(encounter.encounter_id) {
            // Reuse the one existing PIP presentation; never add another native panel.
            self.view.pip = None;
            if self.view.interaction == InteractionMode::Encounter {
                self.view.menu = false;
            }
            self.view.monster = None;
            self.monster_movement.cancel();
            self.monster_behavior = None;
        }
        self.server_encounter = Some((encounter.encounter_id, now + remaining));
        self.place_server_monster(now);
    }
    pub fn debug_spawn(&mut self, now: f64) {
        if self.server_encounter.is_none() && self.view.pip.is_none() {
            self.view.game = Default::default();
            self.presentation = Default::default();
            self.spawn(now);
        }
    }
    pub fn spawn(&mut self, now: f64) {
        if self.view.pip.is_some() {
            return;
        }
        let (x, y) = self
            .area
            .ground(self.area.x + self.area.w - PIP_SIZE.width / 2.0, PIP_SIZE);
        self.view.monster = None; // explicit debug identity, never server/discovery
        self.view.pip = Some(Entity {
            x,
            y,
            size: PIP_SIZE,
            state: PipState::Spawning,
            facing: -1,
        });
        self.pip_deadline = now + 0.6;
    }
    pub fn despawn(&mut self, now: f64) {
        // Developer despawn cannot resolve a server-owned encounter.
        if self.server_encounter.is_some() {
            return;
        }
        if let Some(p) = &mut self.view.pip {
            p.state = PipState::Despawning;
            self.pip_deadline = now + 0.5;
        }
        if self.view.game.battle.is_none() && self.view.interaction == InteractionMode::Encounter {
            self.view.menu = false;
        }
    }
    pub fn set_spawn_environment(
        &mut self,
        safe: crate::desktop::DesktopSafeArea,
        cursor: (f64, f64),
        windows: Option<Vec<Area>>,
    ) {
        self.spawn_environment = Some(SpawnEnvironment {
            safe,
            cursor,
            windows,
        });
    }
    fn place_server_monster(&mut self, now: f64) {
        let Some(context) = &self.spawn_environment else {
            return;
        };
        let environment = crate::spawn::Environment {
            safe_area: &context.safe,
            cursor: Some(context.cursor),
            windows: context.windows.as_deref(),
        };
        let Some(intent) = self.spawn_runtime.place(now, &environment) else {
            return;
        };
        let encounter = self
            .spawn_runtime
            .encounter
            .as_ref()
            .expect("placement has authority");
        let Some(mut identity) = self.spawn_runtime.identity(&encounter.monster.code) else {
            return;
        };
        identity.level = encounter.monster.level;
        identity.encounter_id = Some(encounter.encounter_id);
        self.view.pip = Some(Entity {
            x: intent.position.0,
            y: intent.position.1,
            size: PIP_SIZE,
            state: PipState::Spawning,
            facing: -1,
        });
        self.discovery
            .placed(encounter.encounter_id, &identity.monster_code, now);
        eprintln!(
            "[LUMA SPAWN] placed {} encounter={} at={:?}",
            identity.monster_code, encounter.encounter_id, intent.position
        );
        self.monster_behavior =
            crate::monster_behavior::profile(&identity.monster_code).map(|profile| {
                let id = encounter.encounter_id.as_u128();
                crate::monster_behavior::Controller::new(
                    profile,
                    crate::monster_behavior::Seeded::new(
                        self.behavior_seed ^ id as u64 ^ (id >> 64) as u64,
                    ),
                    now,
                )
            });
        self.pip_deadline = now + crate::presentation::spawn::hold_seconds(&identity.rarity);
        self.view.monster = Some(identity);
    }
    pub fn spawn_action(&mut self, now: f64) -> Option<crate::spawn::runtime::Action> {
        self.spawn_runtime.action(now)
    }
    pub fn complete_spawn(
        &mut self,
        now: f64,
        action: crate::spawn::runtime::Action,
        result: Result<Option<crate::backend::Encounter>, String>,
    ) {
        let accepted = result.is_ok();
        self.spawn_runtime.complete(now, action, result);
        if accepted {
            let value = self.spawn_runtime.encounter.clone();
            let remaining = (self.spawn_runtime.deadline - now).max(0.0);
            self.apply_server_encounter(now, value, remaining);
        }
    }
    pub fn drag(&mut self, now: f64, cursor: (f64, f64)) {
        self.companion.begin_drag(now, self.area, cursor);
        self.view.moa = self.companion.entity().clone();
    }
    pub fn interact(&mut self) {
        if let Some(p) = &mut self.view.pip {
            if p.state != PipState::Despawning {
                p.state = PipState::Engaged;
                self.view.menu = true;
                self.view.interaction = InteractionMode::Encounter;
            }
        }
    }
    pub fn close(&mut self) {
        self.view.menu = false;
        if let Some(p) = &mut self.view.pip {
            if p.state == PipState::Engaged {
                p.state = PipState::Roaming;
            }
        }
    }
    pub fn set_movement_windows(&mut self, windows: Option<Vec<Area>>) {
        self.companion.set_movement_windows(windows);
    }
    pub fn tick(&mut self, now: f64, dt: f64, cursor: (f64, f64), down: bool) {
        self.place_server_monster(now);
        // Hide an expired lease, but keep authority/budget until server reconciliation.
        if self.server_encounter.as_ref().is_some_and(|e| now >= e.1) {
            if let Some(p) = &mut self.view.pip {
                if p.state != PipState::Despawning {
                    p.state = PipState::Despawning;
                    self.pip_deadline = now + 0.5;
                }
            }
        }
        let dt = dt.clamp(0.0, 0.1);
        let was_dragging = self.companion.entity().state == CompanionState::Dragging;
        self.companion.tick(now, dt, self.area, cursor, down);
        self.view.moa = self.companion.entity().clone();
        let terminal = self
            .view
            .game
            .battle
            .as_ref()
            .is_some_and(|b| b.encounter_status != "ACTIVE");
        let locked =
            self.view.menu
                || down
                || was_dragging
                || self.view.game.busy
                || self.view.items.busy
                || self.view.evolution.busy
                || self
                    .view
                    .game
                    .battle
                    .as_ref()
                    .is_some_and(|b| b.status == crate::backend::battle::Status::Active)
                || terminal
                || self.view.pip.as_ref().is_some_and(|p| {
                    p.state == PipState::Engaged || p.state == PipState::Despawning
                });
        if locked {
            self.monster_movement.cancel();
            if let Some(b) = &mut self.monster_behavior {
                b.hold(terminal);
            }
        }
        let mut remove = false;
        let mut react = false;
        if let Some(p) = &mut self.view.pip {
            match p.state {
                PipState::Spawning => {
                    if self.view.monster.is_none() {
                        p.x -= 50.0 * dt;
                    }
                    if now >= self.pip_deadline {
                        p.state = PipState::Roaming;
                    }
                }
                PipState::Roaming => {
                    if self.view.monster.is_some() && locked {
                        // Interaction/battle ownership freezes ambient motion, not entity identity.
                    } else if let Some(identity) = &self.view.monster {
                        if let Some(behavior) = &mut self.monster_behavior {
                            let companion = self.view.identity.as_ref().and_then(|_| {
                                let q = &self.view.moa;
                                (q.x.is_finite() && q.y.is_finite()).then_some((q.x, q.y))
                            });
                            let distance = companion.map(|q| (q.0 - p.x).hypot(q.1 - p.y));
                            let env = crate::movement::ambient::Environment {
                                area: self.area,
                                size: p.size,
                                cursor,
                                windows: self
                                    .spawn_environment
                                    .as_ref()
                                    .and_then(|e| e.windows.as_deref()),
                            };
                            if behavior.stop_approach(distance)
                                && identity.movement_profile
                                    != crate::movement::MovementProfile::Jump
                            {
                                self.monster_movement.cancel();
                            }
                            if let Some(decision) = behavior.poll(
                                now,
                                distance,
                                identity.movement_profile,
                                self.monster_movement.profile().is_some(),
                            ) {
                                self.monster_movement.start_ambient(
                                    identity.movement_profile,
                                    decision,
                                    (p.x, p.y),
                                    companion,
                                    env,
                                );
                            }
                            let position = self.monster_movement.tick_ambient(
                                identity.movement_profile,
                                (p.x, p.y),
                                dt,
                                behavior.current.speed,
                                env,
                            );
                            p.x = position.0;
                            p.y = position.1;
                        }
                    } else {
                        p.x += p.facing as f64 * 24.0 * dt;
                    }
                    let (x, y) = self.area.clamp(p.x, p.y, p.size);
                    if x != p.x {
                        p.facing *= -1;
                    }
                    p.x = x;
                    p.y = y;
                    let distance = (p.x - self.view.moa.x).hypot(p.y - self.view.moa.y);
                    if distance < 130.0 && !was_dragging && self.view.monster.is_none() {
                        p.state = PipState::Engaged;
                        react = true;
                    }
                }
                PipState::Engaged => {
                    if !self.view.menu
                        && (p.x - self.view.moa.x).hypot(p.y - self.view.moa.y) > 160.0
                    {
                        p.state = PipState::Roaming;
                    }
                }
                PipState::Despawning => {
                    remove = now >= self.pip_deadline;
                }
            }
        }
        if react {
            self.companion
                .react(now, self.area, self.view.pip.as_ref().map(|p| p.x));
            self.view.moa = self.companion.entity().clone();
        }
        if remove {
            self.spawn_runtime.hidden();
            self.view.pip = None;
            self.monster_behavior = None;
            self.monster_movement.cancel();
        }
        if let Some(p) = &mut self.view.pip {
            let (x, y) = if self.view.monster.is_some() {
                self.area.clamp(p.x, p.y, p.size)
            } else {
                self.area.ground(p.x, p.size)
            };
            p.x = x;
            p.y = y;
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn world() -> World {
        World::new(
            Area {
                x: -800.0,
                y: 60.0,
                w: 800.0,
                h: 600.0,
            },
            0.0,
            42,
        )
    }
    #[test]
    fn drag_clamps_and_recovers() {
        let mut w = world();
        w.drag(0.0, (w.view.moa.x, w.view.moa.y));
        w.tick(1.0, 0.03, (9000.0, -9000.0), true);
        assert_eq!(w.view.moa.x, -56.0);
        assert_eq!(w.view.moa.y, 68.0);
        w.tick(2.0, 0.03, (9000.0, -9000.0), false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn click_reaction() {
        let mut w = world();
        let p = (w.view.moa.x, w.view.moa.y);
        w.drag(0.0, p);
        w.tick(0.1, 0.03, p, false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        w.tick(2.0, 0.03, p, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn pip_lifecycle() {
        let mut w = world();
        w.spawn(0.0);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Spawning);
        w.tick(1.0, 0.03, (0.0, 0.0), false);
        w.view.pip.as_mut().unwrap().x = w.view.moa.x + 110.0;
        w.tick(1.1, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        w.interact();
        assert!(w.view.menu);
        w.close();
        assert!(!w.view.menu);
        w.despawn(2.0);
        w.tick(3.0, 0.03, (0.0, 0.0), false);
        assert!(w.view.pip.is_none());
    }
    #[test]
    fn pip_waits_for_drag_release_then_reaction_expires() {
        let mut w = world();
        w.spawn(0.0);
        w.tick(1.0, 0.03, (0.0, 0.0), false);
        let start = (w.view.moa.x, w.view.moa.y);
        w.view.pip.as_mut().unwrap().x = start.0 + 80.0;
        w.drag(1.0, start);
        let end = (start.0 + 50.0, start.1);
        w.tick(2.0, 0.03, end, true);
        assert_eq!(w.view.moa.state, CompanionState::Dragging);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Roaming);
        w.tick(3.0, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
        w.tick(3.1, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Engaged);
        w.tick(4.4, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn ground_alignment_after_drag_and_visible_frame_change() {
        let mut w = world();
        w.spawn(0.0);
        w.view.pip.as_mut().unwrap().size = Size {
            width: 120.0,
            height: 180.0,
        };
        let start = (w.view.moa.x, w.view.moa.y);
        w.drag(0.0, start);
        w.tick(0.1, 0.03, (start.0, 10000.0), true);
        assert_eq!(
            w.view.moa.y + w.view.moa.size.height,
            w.area.y + w.area.h - crate::geometry::LAYOUT.side_margin
        );
        w.tick(0.2, 0.03, (start.0, 10000.0), false);
        assert_eq!(w.view.moa.y, w.view.pip.as_ref().unwrap().y);
        w.area = Area {
            x: -1200.0,
            y: -600.0,
            w: 1000.0,
            h: 500.0,
        };
        w.tick(0.3, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.y, w.area.ground_y());
        assert_eq!(w.view.pip.as_ref().unwrap().y, w.area.ground_y());
        for (x, y, size) in [(w.view.moa.x, w.view.moa.y, w.view.moa.size), {
            let p = w.view.pip.as_ref().unwrap();
            (p.x, p.y, p.size)
        }] {
            let b = size.bounds(x, y);
            assert!(b.x >= w.area.x && b.x + b.w <= w.area.x + w.area.w);
            assert!(b.y >= w.area.y && b.y + b.h <= w.area.y + w.area.h);
        }
    }
    #[test]
    fn area_change_and_sleep() {
        let mut w = world();
        w.area = Area {
            x: 0.0,
            y: 100.0,
            w: 300.0,
            h: 300.0,
        };
        w.tick(500.0, 500.0, (0.0, 0.0), false);
        assert!(w.view.moa.x >= 0.0);
        assert!(w.view.moa.y >= 100.0);
    }
}

#[cfg(test)]
mod monster_tests;
