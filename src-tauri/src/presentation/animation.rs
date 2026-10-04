// Read-only presentation telemetry from actual movement, never movement authority.
use serde::Serialize;
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Motion {
    pub moa: f64,
    pub pip: f64,
    pub jump: Option<crate::movement::jump::Sample>,
    pub flight: Option<Flight>,
    pub floating: Option<Flight>,
}
pub fn speed(before: (f64, f64), after: (f64, f64), dt: f64, previous: f64) -> f64 {
    if !dt.is_finite() || !(0.001..=0.25).contains(&dt) {
        return 0.0;
    }
    let raw = (after.0 - before.0).hypot(after.1 - before.1) / dt;
    if !raw.is_finite() || !(3.0..=256.0).contains(&raw) {
        return 0.0;
    }
    if (raw - previous).abs() < 4.0 {
        return previous;
    }
    (raw / 4.0).round() * 4.0
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn measured_motion_stationary_jitter_and_discontinuities() {
        assert_eq!(speed((0., 0.), (1.32, 0.), 0.033, 0.), 40.);
        assert_eq!(speed((0., 0.), (1.33, 0.), 0.033, 40.), 40.);
        assert_eq!(speed((5., 5.), (5., 5.), 0.033, 40.), 0.);
        assert_eq!(speed((0., 0.), (0.01, 0.), 0.033, 0.), 0.);
        assert_eq!(speed((0., 0.), (1000., 0.), 0.033, 40.), 0.);
        assert_eq!(speed((0., 0.), (1., 0.), 0., 0.), 0.);
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Flight {
    pub timestamp: f64,
    pub x: f64,
    pub y: f64,
    pub vx: f64,
    pub vy: f64,
    pub speed: f64,
    pub active: bool,
    pub facing: i8,
}
impl Flight {
    pub fn measured(
        before: (f64, f64),
        after: (f64, f64),
        dt: f64,
        now: f64,
        active: bool,
        facing: i8,
    ) -> Option<Self> {
        if !dt.is_finite() || !(0.001..=0.1).contains(&dt) || !now.is_finite() {
            return None;
        }
        let vx = (after.0 - before.0) / dt;
        let vy = (after.1 - before.1) / dt;
        let speed = vx.hypot(vy);
        if !speed.is_finite() || speed > 256.0 {
            return None;
        }
        Some(Self {
            timestamp: now,
            x: after.0,
            y: after.1,
            vx,
            vy,
            speed,
            active,
            facing,
        })
    }
}

#[cfg(test)]
mod flight_tests {
    use super::*;
    #[test]
    fn accepted_vector_telemetry_including_vertical_and_stop() {
        let m = Flight::measured((1., 2.), (1., 3.), 0.05, 1., true, -1).unwrap();
        assert_eq!((m.vx, m.vy, m.speed, m.facing), (0., 20., 20., -1));
        let stopped = Flight::measured((1., 3.), (1., 3.), 0.05, 2., false, -1).unwrap();
        assert_eq!(stopped.speed, 0.);
        for dt in [0., f64::NAN, 1.] {
            assert!(Flight::measured((0., 0.), (1., 1.), dt, 1., true, 1).is_none());
        }
        assert!(Flight::measured((0., 0.), (1000., 1000.), 0.05, 1., true, 1).is_none());
    }
}
