//! Semantic-intent adapter and cached safety checks around the existing movement engine.
use super::*;
use crate::monster_behavior::{Decision, Intent};
#[derive(Clone, Copy)]
pub struct Environment<'a> {
    pub area: Area,
    pub size: Size,
    pub cursor: (f64, f64),
    pub windows: Option<&'a [Area]>,
}
fn region(profile: MovementProfile, area: Area, size: Size) -> Area {
    if profile == MovementProfile::Flying {
        let floor = (area.y + area.h - size.height - 8.0 - 160.0).max(area.y);
        Area {
            y: floor,
            h: area.y + area.h - floor,
            ..area
        }
    } else {
        area
    }
}
impl MovementController {
    pub fn start_ambient(
        &mut self,
        profile: MovementProfile,
        d: Decision,
        position: (f64, f64),
        companion: Option<(f64, f64)>,
        env: Environment<'_>,
    ) {
        if profile == MovementProfile::Static || matches!(d.intent, Intent::Idle | Intent::Pause) {
            self.cancel();
            return;
        }
        let area = region(profile, env.area, env.size);
        if !area.fits(env.size) {
            self.cancel();
            return;
        }
        let mut vector = (d.direction, 0.5);
        if matches!(d.intent, Intent::ApproachCompanion | Intent::AvoidCompanion) {
            let Some(target) = companion else {
                self.cancel();
                return;
            };
            let (x, y) = (target.0 - position.0, target.1 - position.1);
            let norm = x.hypot(y).max(1.0);
            let sign = if d.intent == Intent::AvoidCompanion {
                -1.0
            } else {
                1.0
            };
            vector = (x / norm * sign, y / norm * sign);
        }
        if profile == MovementProfile::Edge {
            // Same safe side always; approaching/avoiding projects onto the vertical edge.
            vector = (
                0.0,
                if vector.1.abs() < 0.1 {
                    d.direction
                } else {
                    vector.1.signum()
                },
            );
            if matches!(
                d.intent,
                Intent::Wander | Intent::EdgeShift | Intent::ShortBurst
            ) {
                vector.1 = d.direction;
            }
        }
        let mut target = area.clamp(
            position.0 + vector.0 * d.distance,
            position.1 + vector.1 * d.distance,
            env.size,
        );
        if matches!(profile, MovementProfile::Ground | MovementProfile::Jump) {
            target = area.ground(target.0, env.size);
        }
        if profile == MovementProfile::Floating {
            target.1 = position.1;
        }
        // A blocked boundary reverses wandering, never a pursuit/avoidance direction.
        if (target.0 - position.0).hypot(target.1 - position.1) < 1.0
            && matches!(
                d.intent,
                Intent::Wander | Intent::EdgeShift | Intent::ShortBurst
            )
        {
            target = area.clamp(
                position.0 - vector.0 * d.distance,
                position.1 - vector.1 * d.distance,
                env.size,
            );
        }
        let height = if matches!(profile, MovementProfile::Jump | MovementProfile::Floating) {
            16.0
        } else {
            0.0
        };
        let clear = unobstructed(
            position,
            target,
            height,
            env.size,
            env.cursor,
            env.windows,
            100.0,
        ) && (profile != MovementProfile::Free2d
            || unobstructed(
                target,
                area.ground(target.0, env.size),
                0.0,
                env.size,
                env.cursor,
                env.windows,
                100.0,
            ));
        if clear {
            self.start(
                MovementIntent {
                    profile,
                    target,
                    height,
                    duration: d.distance / d.speed.max(1.0),
                },
                position,
                area,
                env.size,
            );
        } else {
            self.cancel();
        }
    }
    pub fn tick_ambient(
        &mut self,
        profile: MovementProfile,
        position: (f64, f64),
        dt: f64,
        speed: f64,
        env: Environment<'_>,
    ) -> (f64, f64) {
        let area = region(profile, env.area, env.size);
        let next = self.tick(position, dt, area, env.size, speed).0;
        if unobstructed(
            position,
            next,
            0.0,
            env.size,
            env.cursor,
            env.windows,
            100.0,
        ) {
            next
        } else {
            self.cancel();
            env.area.clamp(position.0, position.1, env.size)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn all_profiles_obey_windows_cursor_and_constraints() {
        let area = Area {
            x: -2000.,
            y: -1000.,
            w: 1400.,
            h: 900.,
        };
        let size = crate::geometry::PIP_SIZE;
        for profile in [
            MovementProfile::Ground,
            MovementProfile::Jump,
            MovementProfile::Floating,
            MovementProfile::Flying,
            MovementProfile::Free2d,
            MovementProfile::Edge,
            MovementProfile::Static,
        ] {
            let position = match profile {
                MovementProfile::Ground | MovementProfile::Jump => area.ground(-1500., size),
                MovementProfile::Flying => area.clamp(-1500., f64::MAX, size),
                MovementProfile::Edge => area.clamp(f64::MIN, -500., size),
                _ => (-1500., -600.),
            };
            let decision = Decision {
                intent: Intent::ApproachCompanion,
                direction: 1.,
                distance: 40.,
                speed: 14.,
            };
            let windows = [area];
            for (cursor, windows) in [
                ((-9999., -9999.), None),
                ((-9999., -9999.), Some(windows.as_slice())),
                (position, Some([].as_slice())),
            ] {
                let env = Environment {
                    area,
                    size,
                    cursor,
                    windows,
                };
                let mut c = MovementController::default();
                c.start_ambient(profile, decision, position, Some((-1000., -900.)), env);
                assert!(c.profile().is_none());
                assert_eq!(c.tick_ambient(profile, position, 0.1, 14., env), position);
            }
            let env = Environment {
                area,
                size,
                cursor: (-9999., -9999.),
                windows: Some(&[]),
            };
            let mut c = MovementController::default();
            c.start_ambient(profile, decision, position, Some((-1000., -900.)), env);
            let mut p = position;
            for _ in 0..100 {
                p = c.tick_ambient(profile, p, 0.1, 14., env);
                let b = size.bounds(p.0, p.1);
                assert!(
                    b.x >= area.x + 8.
                        && b.x + b.w <= area.x + area.w - 8.
                        && b.y >= area.ground_y()
                        && b.y + b.h <= area.y + area.h - 8.
                );
                if profile == MovementProfile::Flying {
                    assert!(p.1 >= area.y + area.h - size.height - 160.);
                }
                if profile == MovementProfile::Edge {
                    assert_eq!(p.0, position.0);
                }
                if profile == MovementProfile::Static {
                    assert_eq!(p, position);
                }
            }
            // New cursor/window occupancy cancels an already-running excursion.
            c.start_ambient(profile, decision, p, Some((-1000., -900.)), env);
            assert_eq!(
                c.tick_ambient(profile, p, 0.1, 14., Environment { cursor: p, ..env }),
                p
            );
        }
    }
}
