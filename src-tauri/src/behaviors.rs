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
            .ground(self.area.x + self.area.w - PIP_SIZE.width / 2.0, PIP_SIZE);
        self.view.pip = Some(Entity {
            x,
            y,
            size: PIP_SIZE,
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
                    let (x, y) = self.area.ground(p.x, p.size);
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
            self.companion
                .react(now, self.area, self.view.pip.as_ref().map(|p| p.x));
            self.view.moa = self.companion.entity().clone();
        }
        if remove {
            self.view.pip = None;
        }
        if let Some(p) = &mut self.view.pip {
            let (x, y) = self.area.ground(p.x, p.size);
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
        assert_eq!(w.view.moa.x, -56.0);
        assert_eq!(w.view.moa.y, 68.0);
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
    fn ground_alignment_after_drag_and_visible_frame_change() {
        let mut w = world();
        w.spawn(0.0);
        w.view.pip.as_mut().unwrap().size = Size {
            width: 120.0,
            height: 180.0,
        };
        let start = (w.view.moa.x, w.view.moa.y);
        w.drag(0.0, start);
        w.tick(0.1, 0.03, (start.0, 10000.0), true);
        assert_eq!(
            w.view.moa.y + w.view.moa.size.height,
            w.area.y + w.area.h - crate::geometry::LAYOUT.side_margin
        );
        w.tick(0.2, 0.03, (start.0, 10000.0), false);
        assert_eq!(w.view.moa.y, w.view.pip.as_ref().unwrap().y);
        w.area = Area {
            x: -1200.0,
            y: -600.0,
            w: 1000.0,
            h: 500.0,
        };
        w.tick(0.3, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.y, w.area.ground_y());
        assert_eq!(w.view.pip.as_ref().unwrap().y, w.area.ground_y());
        for (x, y, size) in [(w.view.moa.x, w.view.moa.y, w.view.moa.size), {
            let p = w.view.pip.as_ref().unwrap();
            (p.x, p.y, p.size)
        }] {
            let b = size.bounds(x, y);
            assert!(b.x >= w.area.x && b.x + b.w <= w.area.x + w.area.w);
            assert!(b.y >= w.area.y && b.y + b.h <= w.area.y + w.area.h);
        }
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
