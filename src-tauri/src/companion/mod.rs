use crate::movement::{
    self, MovementConfig, MovementController, MovementIntent, MovementProfile, MOA_MOVEMENT,
};
pub mod config;
mod selection;
mod transitions;
use crate::entities::{Area, CompanionState, Entity, MOA_SIZE};
use config::{BehaviorConfig, CompanionPersonality};
use transitions::Event;

#[derive(Clone, Copy)]
struct Excursion {
    start: (f64, f64),
    target: (f64, f64),
    height: f64,
}
struct DragGesture {
    offset: (f64, f64),
    start: (f64, f64),
    max_distance: f64,
}
/// Owns Companion simulation. No Tauri/React/AppKit dependencies or wall-clock reads.
pub struct CompanionController {
    entity: Entity<CompanionState>,
    personality: CompanionPersonality,
    config: BehaviorConfig,
    entered_at: f64,
    duration: f64,
    quiet_since: f64,
    cursor_ready_at: f64,
    target: f64,
    movement: MovementController,
    movement_config: MovementConfig,
    movement_ready_at: f64,
    windows: Option<Vec<Area>>,
    excursion: Option<Excursion>,
    rng: u64,
    movement_rng: u64,
    drag: Option<DragGesture>,
}
impl CompanionController {
    pub fn new(
        area: Area,
        now: f64,
        seed: u64,
        personality: CompanionPersonality,
        config: BehaviorConfig,
    ) -> Self {
        let (x, y) = area.ground(area.x + area.w - 280.0 + MOA_SIZE.width / 2.0, MOA_SIZE);
        let mut s = Self {
            entity: Entity {
                x,
                y,
                size: MOA_SIZE,
                state: CompanionState::Idle,
                facing: -1,
            },
            personality,
            config,
            entered_at: now,
            duration: 0.0,
            quiet_since: now,
            cursor_ready_at: now + config.cursor_cooldown,
            target: x,
            movement: MovementController::default(),
            movement_config: MOA_MOVEMENT,
            movement_ready_at: now + MOA_MOVEMENT.cooldown,
            windows: None,
            excursion: None,
            rng: seed.max(1),
            // Separate deterministic stream; movement choices do not consume behavior randomness.
            movement_rng: (seed ^ 0x6c756d615f6d6f76).max(1),
            drag: None,
        };
        s.duration = config.idle.sample(s.random());
        s
    }
    pub fn entity(&self) -> &Entity<CompanionState> {
        &self.entity
    }
    pub fn set_movement_windows(&mut self, windows: Option<Vec<Area>>) {
        self.windows = windows;
    }
    fn random(&mut self) -> f64 {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 7;
        self.rng ^= self.rng << 17;
        (self.rng >> 11) as f64 / ((1u64 << 53) as f64)
    }
    fn movement_random(&mut self) -> f64 {
        self.movement_rng ^= self.movement_rng << 13;
        self.movement_rng ^= self.movement_rng >> 7;
        self.movement_rng ^= self.movement_rng << 17;
        (self.movement_rng >> 11) as f64 / ((1u64 << 53) as f64)
    }
    fn apply(&mut self, event: Event, now: f64, area: Area, cursor: (f64, f64)) {
        let Some(state) = transitions::next(self.entity.state, event) else {
            return;
        };
        let previous = self.entity.state;
        self.movement.cancel();
        self.excursion = None;
        if state != CompanionState::Dragging {
            (self.entity.x, self.entity.y) = area.ground(self.entity.x, self.entity.size);
        }
        self.entity.state = state;
        self.entered_at = now;
        self.duration = match state {
            CompanionState::Idle => self.config.idle.sample(self.random()),
            CompanionState::Walking => {
                let offset = (self.random() * 2.0 - 1.0) * self.config.walk_radius;
                self.target = area.ground(self.entity.x + offset, self.entity.size).0;
                let config = self.movement_config;
                let mut intent = MovementIntent {
                    profile: config.default,
                    target: area.ground(self.target, self.entity.size),
                    duration: self.config.walk_duration,
                    height: 0.0,
                };
                if now >= self.movement_ready_at {
                    let profile = config.choose(self.movement_random());
                    if matches!(profile, MovementProfile::Jump | MovementProfile::Free2d) {
                        let target = movement::bounded_target(
                            (self.entity.x, self.entity.y),
                            self.movement_random(),
                            area,
                            self.entity.size,
                            config,
                        );
                        let target = if profile == MovementProfile::Jump {
                            area.ground(target.0, self.entity.size)
                        } else {
                            target
                        };
                        let height = if profile == MovementProfile::Jump {
                            config.height
                        } else {
                            0.0
                        };
                        if movement::unobstructed(
                            (self.entity.x, self.entity.y),
                            target,
                            height,
                            self.entity.size,
                            cursor,
                            self.windows.as_deref(),
                            config.cursor_clearance,
                        ) {
                            intent = MovementIntent {
                                profile,
                                target,
                                duration: config.duration,
                                height,
                            };
                            self.excursion = Some(Excursion {
                                start: (self.entity.x, self.entity.y),
                                target,
                                height,
                            });
                            self.movement_ready_at = now + config.cooldown;
                            self.target = target.0;
                        }
                    }
                }
                self.movement.start(
                    intent,
                    (self.entity.x, self.entity.y),
                    area,
                    self.entity.size,
                );
                self.entity.facing = if self.target >= self.entity.x { 1 } else { -1 };
                self.quiet_since = now;
                self.config.walk_duration
            }
            CompanionState::Sitting => self.config.sitting.sample(self.random()),
            CompanionState::Looking => {
                self.face(cursor.0);
                self.cursor_ready_at = now + self.config.cursor_cooldown;
                self.config.looking.sample(self.random())
            }
            CompanionState::Sleeping => self.config.sleeping.sample(self.random()),
            CompanionState::Dragging => f64::INFINITY,
            CompanionState::Reacting => self.config.reaction_duration,
        };
        if matches!(state, CompanionState::Dragging | CompanionState::Reacting)
            || (state == CompanionState::Idle
                && matches!(
                    previous,
                    CompanionState::Walking
                        | CompanionState::Dragging
                        | CompanionState::Reacting
                        | CompanionState::Sleeping
                ))
        {
            self.quiet_since = now;
            self.cursor_ready_at = now + self.config.cursor_cooldown;
        }
    }
    fn face(&mut self, x: f64) {
        let delta = x - self.entity.x;
        if delta != 0.0 {
            self.entity.facing = if delta > 0.0 { 1 } else { -1 };
        }
    }
    pub fn react(&mut self, now: f64, area: Area, source_x: Option<f64>) {
        if self.entity.state == CompanionState::Dragging {
            return;
        }
        self.apply(Event::Reaction, now, area, (0.0, 0.0));
        if let Some(x) = source_x {
            self.face(x);
        }
    }
    pub fn begin_drag(&mut self, now: f64, area: Area, cursor: (f64, f64)) {
        if self.entity.state == CompanionState::Dragging {
            return;
        }
        self.drag = Some(DragGesture {
            offset: (cursor.0 - self.entity.x, cursor.1 - self.entity.y),
            start: cursor,
            max_distance: 0.0,
        });
        self.apply(Event::DragStarted, now, area, cursor);
    }
    pub fn tick(&mut self, now: f64, dt: f64, area: Area, cursor: (f64, f64), down: bool) {
        let dt = dt.clamp(0.0, 0.1); // Existing sleep/busy-main-thread protection.
        (self.entity.x, self.entity.y) = area.clamp(self.entity.x, self.entity.y, self.entity.size);
        if let Some(gesture) = &mut self.drag {
            (self.entity.x, self.entity.y) = area.clamp(
                cursor.0 - gesture.offset.0,
                cursor.1 - gesture.offset.1,
                self.entity.size,
            );
            gesture.max_distance = gesture
                .max_distance
                .max((cursor.0 - gesture.start.0).hypot(cursor.1 - gesture.start.1));
            if !down {
                let clicked = gesture.max_distance < self.config.click_distance;
                self.drag = None;
                (self.entity.x, self.entity.y) = area.ground(self.entity.x, self.entity.size);
                self.apply(Event::DragReleased, now, area, cursor);
                // Preserve the spike's native mouse gesture classification: click is a separate reaction.
                if clicked {
                    self.react(now, area, None);
                }
            }
            return; // No automatic decision or cursor awareness during/releasing a drag.
        }
        let nearby = (cursor.0 - self.entity.x)
            .hypot(cursor.1 - self.entity.y - self.entity.size.height / 2.0)
            <= self.config.cursor_radius;
        if now - self.entered_at >= self.duration {
            if self.entity.state == CompanionState::Idle {
                let weights = selection::weights(
                    self.personality,
                    self.config.weights,
                    now - self.quiet_since >= self.config.sleep_after_quiet,
                    nearby,
                );
                if let Some(behavior) = selection::choose(weights, self.random()) {
                    self.apply(Event::Decision(behavior), now, area, cursor);
                } else {
                    self.entered_at = now;
                    self.duration = self.config.idle.sample(self.random());
                }
            } else {
                self.apply(Event::Finished, now, area, cursor);
            }
            return; // At most one autonomous transition per tick.
        }
        match self.entity.state {
            CompanionState::Walking => {
                self.target = area.ground(self.target, self.entity.size).0;
                if let Some(Excursion {
                    start,
                    target,
                    height,
                }) = self.excursion
                {
                    if !movement::unobstructed(
                        start,
                        target,
                        height,
                        self.entity.size,
                        cursor,
                        self.windows.as_deref(),
                        self.movement_config.cursor_clearance,
                    ) {
                        self.apply(Event::Finished, now, area, cursor);
                        return;
                    }
                }
                if self.movement.profile() == Some(MovementProfile::Ground) {
                    self.movement
                        .retarget_ground(self.target, area, self.entity.size);
                }
                let (position, complete) = self.movement.tick(
                    (self.entity.x, self.entity.y),
                    dt,
                    area,
                    self.entity.size,
                    self.config.walk_speed,
                );
                (self.entity.x, self.entity.y) = position;
                if complete {
                    self.apply(Event::Finished, now, area, cursor);
                }
            }
            CompanionState::Looking => self.face(cursor.0),
            CompanionState::Idle | CompanionState::Sitting
                if nearby && now >= self.cursor_ready_at =>
            {
                self.apply(Event::CursorNearby, now, area, cursor);
            }
            _ => {} // SITTING/SLEEPING/REACTING never move.
        }
        (self.entity.x, self.entity.y) = if self.entity.state == CompanionState::Walking {
            area.clamp(self.entity.x, self.entity.y, self.entity.size)
        } else {
            area.ground(self.entity.x, self.entity.size)
        };
    }
}
#[cfg(test)]
mod tests;
