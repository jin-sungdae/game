//! Read-only phases of the accepted parabolic JUMP trajectory. No animation clock.
use serde::Serialize;
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Sample {
    pub phase: &'static str,
    pub progress: f64,
    pub grounded: bool,
    pub vy: f64,
    pub vx: f64,
    pub x: f64,
    pub y: f64,
    pub timestamp: f64,
    pub facing: i8,
}
pub fn sample(p: f64, height: f64, duration: f64, position: (f64, f64), ground: f64) -> Sample {
    let grounded = p >= 1.0 && (position.1 - ground).abs() <= 0.001;
    // Progress is monotonic within one movement. A 10%-wide apex band prevents
    // sign jitter and is independent of entity speed, framerate or asset timing.
    let phase = if grounded {
        "LAND"
    } else if p <= 0.05 {
        "LAUNCH"
    } else if p < 0.45 {
        "ASCEND"
    } else if p <= 0.55 {
        "APEX"
    } else {
        "DESCEND"
    };
    Sample {
        phase,
        progress: p,
        grounded,
        vy: if grounded {
            0.0
        } else {
            4.0 * height * (1.0 - 2.0 * p) / duration
        },
        vx: 0.0,
        x: position.0,
        y: position.1,
        timestamp: 0.0,
        facing: 1,
    }
}
