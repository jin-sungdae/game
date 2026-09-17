use crate::entities::CompanionState;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Behavior {
    Walking,
    Sitting,
    Looking,
    Sleeping,
}
impl Behavior {
    pub fn state(self) -> CompanionState {
        match self {
            Self::Walking => CompanionState::Walking,
            Self::Sitting => CompanionState::Sitting,
            Self::Looking => CompanionState::Looking,
            Self::Sleeping => CompanionState::Sleeping,
        }
    }
}
#[derive(Clone, Copy, Debug)]
pub enum Event {
    Decision(Behavior),
    Finished,
    DragStarted,
    DragReleased,
    Reaction,
    CursorNearby,
}
/// The sole state-transition policy. Dragging cannot be interrupted by autonomous events.
pub fn next(state: CompanionState, event: Event) -> Option<CompanionState> {
    use CompanionState::*;
    match (state, event) {
        (_, Event::DragStarted) => Some(Dragging),
        (Dragging, Event::DragReleased) => Some(Idle),
        (Dragging, _) => None,
        (_, Event::Reaction) => Some(Reacting),
        (Idle, Event::Decision(behavior)) => Some(behavior.state()),
        (Idle | Sitting, Event::CursorNearby) => Some(Looking),
        (Walking | Sitting | Looking | Sleeping | Reacting, Event::Finished) => Some(Idle),
        _ => None,
    }
}
