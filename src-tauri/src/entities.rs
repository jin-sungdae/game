pub use crate::geometry::{Area, Size, MOA_SIZE, PIP_SIZE};
use serde::Serialize;
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
    // Native panel/geometry concern; React fills the host's bounds.
    #[serde(skip_serializing)]
    pub size: Size,
    pub state: S,
    pub facing: i8,
}
