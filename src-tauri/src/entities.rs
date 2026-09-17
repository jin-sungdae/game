use serde::Serialize;
pub const SIZE: f64 = 96.0;
pub const HEIGHT: f64 = 104.0;
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CompanionState {
    Idle,
    Walking,
    Sitting,
    Looking,
    Sleeping,
    Dragging,
    Reacting,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PipState {
    Spawning,
    Roaming,
    Engaged,
    Despawning,
}
#[derive(Clone, Debug, Serialize)]
pub struct Entity<S> {
    pub x: f64,
    pub y: f64,
    pub state: S,
    pub facing: i8,
}
#[derive(Clone, Copy, Debug)]
pub struct Area {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}
impl Area {
    pub fn clamp(&self, x: f64, y: f64) -> (f64, f64) {
        (
            x.clamp(self.x, (self.x + self.w - SIZE).max(self.x)),
            y.clamp(self.y, (self.y + self.h.min(220.0) - HEIGHT).max(self.y)),
        )
    }
}
