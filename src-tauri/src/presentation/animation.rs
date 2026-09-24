// Read-only presentation telemetry from actual movement, never movement authority.
use serde::Serialize;
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Motion {
    pub moa: f64,
    pub pip: f64,
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
