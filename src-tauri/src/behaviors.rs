use crate::companion::{
    config::{MOA_BEHAVIOR, MOA_PERSONALITY},
    CompanionController,
};
use crate::entities::*;
use serde::Serialize;
#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub moa: Entity<CompanionState>,
    pub pip: Option<Entity<PipState>>,
    pub menu: bool,
}
pub struct World {
    pub view: Snapshot,
    pub area: Area,
    companion: CompanionController,
    pip_deadline: f64,
}
impl World {
    pub fn new(area: Area, now: f64, seed: u64) -> Self {
        let companion = CompanionController::new(area, now, seed, MOA_PERSONALITY, MOA_BEHAVIOR);
        Self {
            view: Snapshot {
                moa: companion.entity().clone(),
                pip: None,
                menu: false,
            },
            area,
            companion,
            pip_deadline: 0.0,
        }
    }
    pub fn spawn(&mut self, now: f64) {
        if self.view.pip.is_some() {
            return;
        }
        let (x, y) = self
            .area
            .clamp(self.area.x + self.area.w - SIZE, self.area.y + 12.0);
        self.view.pip = Some(Entity {
            x,
            y,
            state: PipState::Spawning,
            facing: -1,
        });
        self.pip_deadline = now + 0.6;
    }
    pub fn despawn(&mut self, now: f64) {
        if let Some(p) = &mut self.view.pip {
            p.state = PipState::Despawning;
            self.pip_deadline = now + 0.5;
        }
        self.view.menu = false;
    }
    pub fn drag(&mut self, now: f64, cursor: (f64, f64)) {
        self.companion.begin_drag(now, self.area, cursor);
        self.view.moa = self.companion.entity().clone();
    }
    pub fn interact(&mut self) {
        if let Some(p) = &mut self.view.pip {
            if p.state != PipState::Despawning {
                p.state = PipState::Engaged;
                self.view.menu = true;
            }
        }
    }
    pub fn close(&mut self) {
        self.view.menu = false;
        if let Some(p) = &mut self.view.pip {
            if p.state == PipState::Engaged {
                p.state = PipState::Roaming;
            }
        }
    }
    pub fn tick(&mut self, now: f64, dt: f64, cursor: (f64, f64), down: bool) {
        let dt = dt.clamp(0.0, 0.1);
        let was_dragging = self.companion.entity().state == CompanionState::Dragging;
        self.companion.tick(now, dt, self.area, cursor, down);
        self.view.moa = self.companion.entity().clone();
        let mut remove = false;
        let mut react = false;
        if let Some(p) = &mut self.view.pip {
            match p.state {
                PipState::Spawning => {
                    p.x -= 50.0 * dt;
                    if now >= self.pip_deadline {
                        p.state = PipState::Roaming;
                    }
                }
                PipState::Roaming => {
                    p.x += p.facing as f64 * 24.0 * dt;
                    let (x, y) = self.area.clamp(p.x, p.y);
                    if x != p.x {
                        p.facing *= -1;
                    }
                    p.x = x;
                    p.y = y;
                    let distance = (p.x - self.view.moa.x).hypot(p.y - self.view.moa.y);
                    if distance < 130.0 && !was_dragging {
                        p.state = PipState::Engaged;
                        react = true;
                    }
                }
                PipState::Engaged => {
                    if !self.view.menu
                        && (p.x - self.view.moa.x).hypot(p.y - self.view.moa.y) > 160.0
                    {
                        p.state = PipState::Roaming;
                    }
                }
                PipState::Despawning => {
                    remove = now >= self.pip_deadline;
                }
            }
        }
        if react {
            self.companion.react(
                now,
                self.area,
                self.view.pip.as_ref().map(|p| p.x + SIZE / 2.0),
            );
            self.view.moa = self.companion.entity().clone();
        }
        if remove {
            self.view.pip = None;
        }
        if let Some(p) = &mut self.view.pip {
            let (x, y) = self.area.clamp(p.x, p.y);
            p.x = x;
            p.y = y;
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn world() -> World {
        World::new(
            Area {
                x: -800.0,
                y: 60.0,
                w: 800.0,
                h: 600.0,
            },
            0.0,
            42,
        )
    }
    #[test]
    fn drag_clamps_and_recovers() {
        let mut w = world();
        w.drag(0.0, (w.view.moa.x, w.view.moa.y));
        w.tick(1.0, 0.03, (9000.0, -9000.0), true);
        assert_eq!(w.view.moa.x, -96.0);
        assert_eq!(w.view.moa.y, 60.0);
        w.tick(2.0, 0.03, (9000.0, -9000.0), false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn click_reaction() {
        let mut w = world();
        let p = (w.view.moa.x, w.view.moa.y);
        w.drag(0.0, p);
        w.tick(0.1, 0.03, p, false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        w.tick(2.0, 0.03, p, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn pip_lifecycle() {
        let mut w = world();
        w.spawn(0.0);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Spawning);
        w.tick(1.0, 0.03, (0.0, 0.0), false);
        w.view.pip.as_mut().unwrap().x = w.view.moa.x + 110.0;
        w.tick(1.1, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        w.interact();
        assert!(w.view.menu);
        w.close();
        assert!(!w.view.menu);
        w.despawn(2.0);
        w.tick(3.0, 0.03, (0.0, 0.0), false);
        assert!(w.view.pip.is_none());
    }
    #[test]
    fn pip_waits_for_drag_release_then_reaction_expires() {
        let mut w = world();
        w.spawn(0.0);
        w.tick(1.0, 0.03, (0.0, 0.0), false);
        let start = (w.view.moa.x, w.view.moa.y);
        w.view.pip.as_mut().unwrap().x = start.0 + 80.0;
        w.drag(1.0, start);
        let end = (start.0 + 50.0, start.1);
        w.tick(2.0, 0.03, end, true);
        assert_eq!(w.view.moa.state, CompanionState::Dragging);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Roaming);
        w.tick(3.0, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
        w.tick(3.1, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Reacting);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Engaged);
        w.tick(4.4, 0.03, end, false);
        assert_eq!(w.view.moa.state, CompanionState::Idle);
    }
    #[test]
    fn area_change_and_sleep() {
        let mut w = world();
        w.area = Area {
            x: 0.0,
            y: 100.0,
            w: 300.0,
            h: 300.0,
        };
        w.tick(500.0, 500.0, (0.0, 0.0), false);
        assert!(w.view.moa.x >= 0.0);
        assert!(w.view.moa.y >= 100.0);
    }
}
