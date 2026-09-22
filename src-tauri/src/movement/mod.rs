//! Presentation-independent logical-point movement. No OS APIs, state transitions or clocks.
use crate::geometry::{Area, Size};
use serde::{Deserialize, Serialize};
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum MovementProfile {
    Ground,
    Jump,
    #[serde(rename = "FREE_2D")]
    Free2d,
    Floating,
    Flying,
    Edge,
    Static,
}
#[derive(Clone, Copy, Debug, Serialize)]
pub struct MovementConfig {
    pub default: MovementProfile,
    pub allowed: &'static [MovementProfile],
    pub weights: [u32; 3],
    pub cooldown: f64,
    pub radius: f64,
    pub height: f64,
    pub duration: f64,
    pub cursor_clearance: f64,
}
pub const WINDOW_POLL_SECONDS: f64 = 1.0;
pub const MOA_MOVEMENT: MovementConfig = MovementConfig {
    default: MovementProfile::Ground,
    allowed: &[
        MovementProfile::Ground,
        MovementProfile::Jump,
        MovementProfile::Free2d,
    ],
    weights: [90, 7, 3],
    cooldown: 180.0,
    radius: 60.0,
    height: 48.0,
    duration: 2.0,
    cursor_clearance: 100.0,
};
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct MovementIntent {
    pub profile: MovementProfile,
    pub target: (f64, f64),
    pub duration: f64,
    pub height: f64,
}
impl MovementConfig {
    pub fn choose(self, unit: f64) -> MovementProfile {
        let mut point = unit * self.weights.iter().map(|v| f64::from(*v)).sum::<f64>();
        for (weight, profile) in self.weights.into_iter().zip([
            MovementProfile::Ground,
            MovementProfile::Jump,
            MovementProfile::Free2d,
        ]) {
            if point < f64::from(weight) {
                return if self.allowed.contains(&profile) {
                    profile
                } else {
                    self.default
                };
            }
            point -= f64::from(weight);
        }
        self.default
    }
}
fn intersects(a: Area, b: Area) -> bool {
    a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}
/// Conservative full swept rectangle, not just target-point avoidance. Unknown window data denies excursions.
pub fn unobstructed(
    start: (f64, f64),
    target: (f64, f64),
    height: f64,
    size: Size,
    cursor: (f64, f64),
    windows: Option<&[Area]>,
    clearance: f64,
) -> bool {
    let Some(windows) = windows else { return false };
    let swept = Area {
        x: start.0.min(target.0) - size.width / 2.0,
        y: start.1.min(target.1),
        w: (target.0 - start.0).abs() + size.width,
        h: (target.1 - start.1).abs() + size.height + height,
    };
    let cursor = Area {
        x: cursor.0 - clearance,
        y: cursor.1 - clearance,
        w: clearance * 2.0,
        h: clearance * 2.0,
    };
    !intersects(swept, cursor) && !windows.iter().any(|w| intersects(swept, *w))
}
/// Target confined to a local bottom band; never choose from the full desktop.
pub fn bounded_target(
    start: (f64, f64),
    unit: f64,
    area: Area,
    size: Size,
    config: MovementConfig,
) -> (f64, f64) {
    area.clamp(
        start.0 + (unit * 2.0 - 1.0) * config.radius,
        area.ground_y() + config.height,
        size,
    )
}
#[derive(Clone, Copy, Debug)]
struct Motion {
    intent: MovementIntent,
    start: (f64, f64),
    elapsed: f64,
    area: Area,
}
#[derive(Default)]
pub struct MovementController {
    active: Option<Motion>,
}
impl MovementController {
    pub fn profile(&self) -> Option<MovementProfile> {
        self.active.map(|m| m.intent.profile)
    }
    pub fn cancel(&mut self) {
        self.active = None;
    }
    pub fn start(
        &mut self,
        mut intent: MovementIntent,
        position: (f64, f64),
        area: Area,
        size: Size,
    ) {
        intent.duration = intent.duration.max(0.001);
        intent.height = intent.height.max(0.0);
        let mut start = area.clamp(position.0, position.1, size);
        intent.target = area.clamp(intent.target.0, intent.target.1, size);
        match intent.profile {
            MovementProfile::Ground | MovementProfile::Jump => {
                start = area.ground(start.0, size);
            }
            MovementProfile::Edge => {
                // Follow the nearest safe side without teleporting to the bottom edge.
                let left = area.clamp(f64::MIN, start.1, size).0;
                let right = area.clamp(f64::MAX, start.1, size).0;
                start.0 = if (start.0 - left).abs() <= (start.0 - right).abs() {
                    left
                } else {
                    right
                };
                intent.target.0 = start.0;
            }
            _ => {}
        }
        if matches!(
            intent.profile,
            MovementProfile::Ground | MovementProfile::Jump
        ) {
            intent.target = area.ground(intent.target.0, size);
        }
        let ceiling = area.clamp(start.0, f64::MAX, size).1;
        intent.height = intent.height.min((ceiling - start.1).max(0.0));
        self.active = Some(Motion {
            intent,
            start,
            elapsed: 0.0,
            area,
        });
    }
    pub fn retarget_ground(&mut self, x: f64, area: Area, size: Size) {
        if let Some(m) = self
            .active
            .as_mut()
            .filter(|m| m.intent.profile == MovementProfile::Ground)
        {
            m.intent.target = area.ground(x, size);
        }
    }
    /// Returns (position, complete). Existing capped dt and constant-speed GROUND are retained.
    pub fn tick(
        &mut self,
        position: (f64, f64),
        dt: f64,
        area: Area,
        size: Size,
        ground_speed: f64,
    ) -> ((f64, f64), bool) {
        let Some(m) = self.active.as_mut() else {
            return (area.clamp(position.0, position.1, size), true);
        };
        if m.area != area || !area.fits(size) {
            self.cancel();
            return (area.ground(position.0, size), true);
        }
        m.elapsed += dt.clamp(0.0, 0.1);
        let p = (m.elapsed / m.intent.duration).clamp(0.0, 1.0);
        let lerp = |a: f64, b: f64, t: f64| a + (b - a) * t;
        let target = m.intent.target;
        let mut complete = p >= 1.0;
        let result = match m.intent.profile {
            MovementProfile::Ground => {
                let d = target.0 - position.0;
                let step = ground_speed * dt.clamp(0.0, 0.1);
                complete = d.abs() <= step;
                area.ground(position.0 + d.signum() * d.abs().min(step), size)
            }
            MovementProfile::Jump => (
                lerp(m.start.0, target.0, p),
                area.ground_y() + m.intent.height * 4.0 * p * (1.0 - p),
            ),
            MovementProfile::Free2d => {
                // Outbound then descend at destination; finite excursion always lands.
                if p <= 0.5 {
                    (
                        lerp(m.start.0, target.0, p * 2.0),
                        lerp(m.start.1, target.1, p * 2.0),
                    )
                } else {
                    (target.0, lerp(target.1, area.ground_y(), (p - 0.5) * 2.0))
                }
            }
            MovementProfile::Floating => (
                m.start.0,
                m.start.1 + m.intent.height * (std::f64::consts::PI * p).sin(),
            ),
            MovementProfile::Flying | MovementProfile::Edge => {
                (lerp(m.start.0, target.0, p), lerp(m.start.1, target.1, p))
            }
            MovementProfile::Static => m.start,
        };
        let result = area.clamp(result.0, result.1, size);
        if complete {
            self.cancel();
        }
        (result, complete)
    }
}
#[cfg(test)]
mod tests;
