//! Species habits layered on the existing personality decision and movement intents.
//! No timers, coordinates mutation, backend actions, or alternate movement engine.
use super::*;
use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Habit {
    Scout,
    SurveyHop,
    Doze,
    ScanFlight,
    DoubleHop,
    Settle,
    LeanDrift,
    InspectStep,
    Peek,
    Recoil,
    EdgeFeint,
    Burst,
    SideObserve,
    Explore,
    EdgeCaution,
}
#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub code: &'static str,
    pub habit: Habit,
    pub step: f64,
    pub speed: f64,
    pub rest: f64,
    pub preparation: f64,
    pub repeat_cooldown: f64,
    pub cursor_radius: f64,
}
// These are local movement/attention parameters, never spawn or battle balance.
pub const CONFIGS: [Config; 15] = [
    Config {
        code: "PIP",
        habit: Habit::Scout,
        step: 28.,
        speed: 24.,
        rest: 2.,
        preparation: 0.15,
        repeat_cooldown: 5.,
        cursor_radius: 220.,
    },
    Config {
        code: "MELLO",
        habit: Habit::SurveyHop,
        step: 40.,
        speed: 20.,
        rest: 3.,
        preparation: 0.55,
        repeat_cooldown: 6.,
        cursor_radius: 230.,
    },
    Config {
        code: "MOSSY",
        habit: Habit::Doze,
        step: 16.,
        speed: 8.,
        rest: 9.,
        preparation: 0.8,
        repeat_cooldown: 12.,
        cursor_radius: 190.,
    },
    Config {
        code: "CHIRP",
        habit: Habit::ScanFlight,
        step: 56.,
        speed: 24.,
        rest: 2.5,
        preparation: 0.3,
        repeat_cooldown: 6.,
        cursor_radius: 240.,
    },
    Config {
        code: "BUBU",
        habit: Habit::DoubleHop,
        step: 30.,
        speed: 24.,
        rest: 2.,
        preparation: 0.2,
        repeat_cooldown: 7.,
        cursor_radius: 210.,
    },
    Config {
        code: "PEBB",
        habit: Habit::Settle,
        step: 20.,
        speed: 10.,
        rest: 7.,
        preparation: 0.9,
        repeat_cooldown: 10.,
        cursor_radius: 180.,
    },
    Config {
        code: "PUFF",
        habit: Habit::LeanDrift,
        step: 36.,
        speed: 14.,
        rest: 4.,
        preparation: 0.45,
        repeat_cooldown: 7.,
        cursor_radius: 230.,
    },
    Config {
        code: "TIKKI",
        habit: Habit::InspectStep,
        step: 24.,
        speed: 16.,
        rest: 3.,
        preparation: 0.65,
        repeat_cooldown: 5.,
        cursor_radius: 230.,
    },
    Config {
        code: "MIMI",
        habit: Habit::Peek,
        step: 0.,
        speed: 0.,
        rest: 5.,
        preparation: 0.,
        repeat_cooldown: 9.,
        cursor_radius: 230.,
    },
    Config {
        code: "WISP",
        habit: Habit::Recoil,
        step: 36.,
        speed: 18.,
        rest: 5.,
        preparation: 0.2,
        repeat_cooldown: 7.,
        cursor_radius: 270.,
    },
    Config {
        code: "SHADE",
        habit: Habit::EdgeFeint,
        step: 32.,
        speed: 16.,
        rest: 4.,
        preparation: 0.45,
        repeat_cooldown: 8.,
        cursor_radius: 220.,
    },
    Config {
        code: "EMBER",
        habit: Habit::Burst,
        step: 48.,
        speed: 24.,
        rest: 2.5,
        preparation: 0.3,
        repeat_cooldown: 7.,
        cursor_radius: 220.,
    },
    Config {
        code: "LUNET",
        habit: Habit::SideObserve,
        step: 28.,
        speed: 12.,
        rest: 5.,
        preparation: 0.6,
        repeat_cooldown: 9.,
        cursor_radius: 280.,
    },
    Config {
        code: "NOVA",
        habit: Habit::Explore,
        step: 54.,
        speed: 18.,
        rest: 3.,
        preparation: 0.4,
        repeat_cooldown: 7.,
        cursor_radius: 250.,
    },
    Config {
        code: "NOCT",
        habit: Habit::EdgeCaution,
        step: 18.,
        speed: 10.,
        rest: 6.,
        preparation: 0.9,
        repeat_cooldown: 10.,
        cursor_radius: 270.,
    },
];
#[derive(Clone, Copy)]
pub struct Context {
    pub position: (f64, f64),
    pub cursor: (f64, f64),
    pub companion_distance: Option<f64>,
    pub movement: MovementProfile,
    pub moving: bool,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CueKind {
    Observe,
    Rest,
    React,
    Turn,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Cue {
    pub kind: CueKind,
    pub serial: u64,
}
#[derive(Default)]
pub(super) struct Living {
    config: Option<Config>,
    pending: Option<(f64, Decision)>,
    recent: Option<Intent>,
    repeated: u8,
    signature_ready: f64,
    cursor_ready: f64,
    interaction: bool,
    followup: Option<Decision>,
    last_direction: Option<f64>,
    cue: Option<Cue>,
    cue_until: f64,
    serial: u64,
}
impl Living {
    pub(super) fn suspend(&mut self) {
        self.pending = None;
        self.followup = None;
        self.cue = None;
    }
    fn cue(&mut self, kind: CueKind, now: f64, duration: f64) {
        self.serial = self.serial.wrapping_add(1);
        self.cue = Some(Cue {
            kind,
            serial: self.serial,
        });
        self.cue_until = now + duration;
    }
}
impl<R: Random> Controller<R> {
    pub fn for_species(code: &str, random: R, now: f64) -> Option<Self> {
        let config = CONFIGS.iter().find(|c| c.code == code).copied()?;
        let mut controller = Self::new(profile(code)?, random, now);
        controller.living.config = Some(config);
        Some(controller)
    }
    pub fn interaction(&mut self) {
        self.living.interaction = true;
    }
    pub fn cue(&self, now: f64) -> Option<Cue> {
        if now.is_finite() && now < self.living.cue_until {
            self.living.cue
        } else {
            None
        }
    }
    /// One decision per due interval. Motion completes before a new decision; jumps always land.
    pub fn poll_species(&mut self, now: f64, context: Context) -> Option<Decision> {
        let c = self.living.config?;
        if self.terminal
            || !now.is_finite()
            || !context.position.0.is_finite()
            || !context.position.1.is_finite()
        {
            return None;
        }
        if self.suspended {
            self.suspended = false;
            self.next_decision_at = now + MIN_INTERVAL;
            return None;
        }
        if context.moving {
            return None;
        }
        if let Some((ready, decision)) = self.living.pending {
            if now < ready {
                return None;
            }
            self.living.pending = None;
            self.current = decision;
            self.living.last_direction = Some(decision.direction);
            self.next_decision_at = now + c.rest;
            return Some(decision);
        }
        if now < self.next_decision_at {
            return None;
        }
        let cursor_distance =
            (context.cursor.0 - context.position.0).hypot(context.cursor.1 - context.position.1);
        let cursor_near = cursor_distance.is_finite() && cursor_distance < c.cursor_radius;
        let interaction = std::mem::take(&mut self.living.interaction);
        let mut decision = self.poll(now, context.companion_distance, context.movement, false)?;
        let mut cue = None;
        let mut signature = false;
        if interaction || (cursor_near && now >= self.living.cursor_ready) {
            self.living.cursor_ready = now + c.repeat_cooldown;
            decision.intent = match c.habit {
                Habit::Recoil | Habit::EdgeCaution => Intent::AvoidCursor,
                Habit::SideObserve => Intent::SideStepCursor,
                Habit::Doze | Habit::Settle => Intent::Rest,
                _ => Intent::Observe,
            };
            cue = Some(if interaction {
                CueKind::React
            } else {
                CueKind::Observe
            });
            self.living.followup = None;
        } else if let Some(hop) = self.living.followup.take() {
            // Exactly one follow-up, only after the first hop has landed; never an endless chain.
            decision = hop;
        } else if now >= self.living.signature_ready && self.random.unit() < 0.4 {
            signature = true;
            decision.intent = match c.habit {
                Habit::Scout => Intent::ShortBurst,
                Habit::SurveyHop | Habit::InspectStep | Habit::ScanFlight => Intent::Observe,
                Habit::Doze | Habit::Settle => Intent::Rest,
                Habit::LeanDrift | Habit::Explore => Intent::Wander,
                Habit::DoubleHop => Intent::ShortBurst,
                Habit::Peek => Intent::Observe,
                Habit::Recoil | Habit::SideObserve | Habit::EdgeCaution => Intent::Pause,
                Habit::EdgeFeint => Intent::EdgeShift,
                Habit::Burst => {
                    if context.companion_distance.is_some_and(|d| d > STOP_RADIUS) {
                        Intent::ApproachCompanion
                    } else {
                        Intent::Observe
                    }
                }
            };
            self.living.signature_ready = now + c.repeat_cooldown;
        }
        // Timid companion avoidance remains stronger than idle variations.
        if !cursor_near
            && !interaction
            && self.profile == Profile::Timid
            && context.companion_distance.is_some_and(|d| d < AVOID_RADIUS)
        {
            decision.intent = Intent::AvoidCompanion;
        }
        if context.movement == MovementProfile::Static {
            decision.intent = if interaction || signature || cue.is_some() {
                Intent::Observe
            } else {
                Intent::Rest
            };
        }
        if self.living.recent == Some(decision.intent) {
            self.living.repeated = self.living.repeated.saturating_add(1);
        } else {
            self.living.repeated = 1;
        }
        if self.living.repeated > 2
            && !matches!(
                decision.intent,
                Intent::AvoidCompanion | Intent::AvoidCursor | Intent::SideStepCursor
            )
        {
            decision.intent =
                if matches!(decision.intent, Intent::Rest | Intent::Pause | Intent::Idle) {
                    Intent::Observe
                } else {
                    Intent::Rest
                };
            self.living.repeated = 1;
        }
        self.living.recent = Some(decision.intent);
        decision.distance = c.step;
        decision.speed = c.speed;
        if matches!(
            decision.intent,
            Intent::Observe | Intent::Rest | Intent::Pause | Intent::Idle
        ) {
            decision.distance = 0.;
            decision.speed = 0.;
            self.next_decision_at = now + c.rest;
            if cue.is_none() {
                cue = Some(if decision.intent == Intent::Observe {
                    CueKind::Observe
                } else {
                    CueKind::Rest
                });
            }
        } else {
            if let Some(distance) = context.companion_distance {
                if decision.intent == Intent::ApproachCompanion {
                    decision.distance = decision.distance.min((distance - STOP_RADIUS).max(0.));
                }
            }
            if c.habit == Habit::DoubleHop && signature && decision.intent == Intent::ShortBurst {
                self.living.followup = Some(decision);
            }
            // Inspect/turn before motion; keep the same controller/trajectory and revalidate safety at execution.
            let reversing = self
                .living
                .last_direction
                .is_some_and(|d| d != decision.direction);
            if c.preparation > 0. {
                let delay = c.preparation * if reversing { 2. } else { 1. };
                self.living.pending = Some((now + delay, decision));
                self.living.cue(
                    if reversing {
                        CueKind::Turn
                    } else {
                        CueKind::Observe
                    },
                    now,
                    delay,
                );
                self.current = Decision::pause();
                return Some(self.current);
            }
        }
        if let Some(kind) = cue {
            self.living.cue(kind, now, c.rest.min(1.5));
        }
        self.current = decision;
        Some(decision)
    }
}
#[cfg(test)]
mod tests;
