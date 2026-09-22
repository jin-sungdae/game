//! Ambient decisions only: no position mutation, OS calls, backend commands or Companion ownership.
use crate::movement::MovementProfile;
use serde::Deserialize;
#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Profile {
    Curious,
    Timid,
    Playful,
    Aggressive,
    Sleepy,
    Trickster,
    Passive,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Intent {
    Idle,
    ApproachCompanion,
    AvoidCompanion,
    Wander,
    Pause,
    EdgeShift,
    ShortBurst,
}
pub const MIN_INTERVAL: f64 = 2.0;
pub const MAX_INTERVAL: f64 = 4.0;
pub const APPROACH_RADIUS: f64 = 280.0;
pub const STOP_RADIUS: f64 = 180.0;
pub const AVOID_RADIUS: f64 = 220.0;
pub const SAFE_RADIUS: f64 = 320.0;
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Decision {
    pub intent: Intent,
    pub direction: f64,
    pub distance: f64,
    pub speed: f64,
}
impl Decision {
    fn pause() -> Self {
        Self {
            intent: Intent::Pause,
            direction: 1.0,
            distance: 0.0,
            speed: 0.0,
        }
    }
}
pub trait Random {
    fn unit(&mut self) -> f64;
}
/// Production stream is seeded from the existing World seed and stable encounter identity.
/// Tests can inject a scripted adapter; no thread_rng/global random state.
pub struct Seeded(u64);
impl Seeded {
    pub fn new(seed: u64) -> Self {
        Self(seed)
    }
}
impl Random for Seeded {
    fn unit(&mut self) -> f64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1);
        (self.0 >> 11) as f64 / ((1_u64 << 53) as f64)
    }
}
pub fn profile(code: &str) -> Option<Profile> {
    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    struct Row {
        monster_code: String,
        behavior_profile: Profile,
    }
    let rows: Vec<Row> =
        serde_json::from_str(include_str!("../../src/entities/monster-dex.json")).ok()?;
    rows.into_iter()
        .find(|r| r.monster_code == code)
        .map(|r| r.behavior_profile)
}
pub struct Controller<R = Seeded> {
    pub profile: Profile,
    pub next_decision_at: f64,
    pub current: Decision,
    pub decisions: u64,
    random: R,
    suspended: bool,
    terminal: bool,
    approaching: bool,
    avoiding: bool,
}
impl<R: Random> Controller<R> {
    pub fn new(profile: Profile, random: R, now: f64) -> Self {
        Self {
            profile,
            random,
            next_decision_at: now,
            current: Decision::pause(),
            decisions: 0,
            suspended: false,
            terminal: false,
            approaching: false,
            avoiding: false,
        }
    }
    pub fn hold(&mut self, terminal: bool) {
        self.suspended = true;
        self.terminal |= terminal;
        self.current = Decision::pause();
    }
    /// No RNG or decision before due; no catch-up even after a large monotonic jump.
    pub fn poll(
        &mut self,
        now: f64,
        distance: Option<f64>,
        movement: MovementProfile,
        moving: bool,
    ) -> Option<Decision> {
        if self.terminal || !now.is_finite() {
            return None;
        }
        if self.suspended {
            self.suspended = false;
            self.next_decision_at = now + MIN_INTERVAL;
            return None;
        }
        if now < self.next_decision_at || moving {
            return None;
        }
        let r = self.random.unit().clamp(0.0, 1.0);
        let direction = if self.random.unit() < 0.5 { -1.0 } else { 1.0 };
        self.next_decision_at =
            now + MIN_INTERVAL + (MAX_INTERVAL - MIN_INTERVAL) * self.random.unit().clamp(0.0, 1.0);
        let distance = distance.filter(|d| d.is_finite() && *d >= 0.0);
        let intent = if movement == MovementProfile::Static
            || (self.profile == Profile::Sleepy && (self.decisions == 0 || r < 0.8))
        {
            Intent::Pause
        } else {
            match self.profile {
                Profile::Curious => {
                    if let Some(d) = distance {
                        if d <= STOP_RADIUS {
                            self.approaching = false;
                            Intent::Pause
                        } else if self.approaching || (d >= APPROACH_RADIUS && r < 0.8) {
                            self.approaching = true;
                            Intent::ApproachCompanion
                        } else {
                            Intent::Wander
                        }
                    } else {
                        Intent::Wander
                    }
                }
                Profile::Timid => {
                    if let Some(d) = distance {
                        if d < AVOID_RADIUS {
                            self.avoiding = true;
                        }
                        if d > SAFE_RADIUS {
                            self.avoiding = false;
                        }
                        if self.avoiding {
                            Intent::AvoidCompanion
                        } else if r < 0.6 {
                            Intent::Pause
                        } else {
                            Intent::Wander
                        }
                    } else {
                        Intent::Idle
                    }
                }
                Profile::Playful => {
                    if r < 0.2 {
                        Intent::ShortBurst
                    } else if r < 0.4 && distance.is_some_and(|d| d > APPROACH_RADIUS) {
                        Intent::ApproachCompanion
                    } else if r < 0.8 {
                        Intent::Wander
                    } else {
                        Intent::Pause
                    }
                }
                Profile::Aggressive => {
                    if distance.is_some_and(|d| d > STOP_RADIUS) {
                        Intent::ApproachCompanion
                    } else {
                        Intent::Pause
                    }
                }
                Profile::Sleepy => Intent::Wander,
                Profile::Trickster => {
                    if r < 0.6 {
                        Intent::Pause
                    } else if movement == MovementProfile::Edge {
                        Intent::EdgeShift
                    } else {
                        Intent::Wander
                    }
                }
                Profile::Passive => {
                    if r < 0.65 {
                        Intent::Idle
                    } else {
                        Intent::Wander
                    }
                }
            }
        };
        let (step, speed) = match (self.profile, intent) {
            (_, Intent::Idle | Intent::Pause) => (0.0, 0.0),
            (Profile::Sleepy, _) => (16.0, 8.0),
            (Profile::Passive, _) => (24.0, 10.0),
            (_, Intent::ShortBurst) => (48.0, 24.0),
            _ => (40.0, 14.0),
        };
        self.current = Decision {
            intent,
            direction,
            distance: step,
            speed,
        };
        self.decisions += 1;
        Some(self.current)
    }
    pub fn stop_approach(&mut self, distance: Option<f64>) -> bool {
        if self.current.intent == Intent::ApproachCompanion
            && distance.is_none_or(|d| d <= STOP_RADIUS)
        {
            self.approaching = false;
            self.current = Decision::pause();
            return true;
        }
        false
    }
}
#[cfg(test)]
mod tests;
