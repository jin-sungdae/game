pub mod config;
mod selection;
mod transitions;
use crate::entities::{Area, CompanionState, Entity, MOA_SIZE};
use config::{BehaviorConfig, CompanionPersonality};
use transitions::Event;

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
    rng: u64,
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
            rng: seed.max(1),
            drag: None,
        };
        s.duration = config.idle.sample(s.random());
        s
    }
    pub fn entity(&self) -> &Entity<CompanionState> {
        &self.entity
    }
    fn random(&mut self) -> f64 {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 7;
        self.rng ^= self.rng << 17;
        (self.rng >> 11) as f64 / ((1u64 << 53) as f64)
    }
    fn apply(&mut self, event: Event, now: f64, area: Area, cursor: (f64, f64)) {
        let Some(state) = transitions::next(self.entity.state, event) else {
            return;
        };
        let previous = self.entity.state;
        self.entity.state = state;
        self.entered_at = now;
        self.duration = match state {
            CompanionState::Idle => self.config.idle.sample(self.random()),
            CompanionState::Walking => {
                let offset = (self.random() * 2.0 - 1.0) * self.config.walk_radius;
                self.target = area.ground(self.entity.x + offset, self.entity.size).0;
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
        (self.entity.x, self.entity.y) = area.ground(self.entity.x, self.entity.size);
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
                let d = self.target - self.entity.x;
                self.entity.x += d.signum() * d.abs().min(self.config.walk_speed * dt);
                if d.abs() <= self.config.walk_speed * dt {
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
        (self.entity.x, self.entity.y) = area.ground(self.entity.x, self.entity.size);
    }
}
#[cfg(test)]
mod tests;
