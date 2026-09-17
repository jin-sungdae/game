use crate::entities::*;
use serde::Serialize;
#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub moa: Entity<MoaState>,
    pub pip: Option<Entity<PipState>>,
    pub menu: bool,
}
pub struct World {
    pub view: Snapshot,
    pub area: Area,
    next_walk: f64,
    walk_end: f64,
    reaction_end: f64,
    pip_deadline: f64,
    target: f64,
    rng: u64,
    drag: Option<(f64, f64, f64, f64)>,
}
impl World {
    pub fn new(area: Area, now: f64, seed: u64) -> Self {
        let (x, y) = area.clamp(area.x + area.w - 280.0, area.y + 12.0);
        let mut s = Self {
            view: Snapshot {
                moa: Entity {
                    x,
                    y,
                    state: MoaState::Idle,
                    facing: -1,
                },
                pip: None,
                menu: false,
            },
            area,
            next_walk: now,
            walk_end: 0.0,
            reaction_end: 0.0,
            pip_deadline: 0.0,
            target: x,
            rng: seed.max(1),
            drag: None,
        };
        s.schedule(now);
        s
    }
    fn random(&mut self) -> f64 {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 7;
        self.rng ^= self.rng << 17;
        (self.rng >> 11) as f64 / ((1u64 << 53) as f64)
    }
    fn schedule(&mut self, now: f64) {
        self.next_walk = now + 30.0 + self.random() * 30.0;
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
    pub fn react(&mut self, now: f64) {
        if self.view.moa.state != MoaState::Dragging {
            self.view.moa.state = MoaState::Reacting;
            self.reaction_end = now + 1.2;
        }
    }
    pub fn drag(&mut self, cursor: (f64, f64)) {
        let m = &mut self.view.moa;
        self.drag = Some((cursor.0 - m.x, cursor.1 - m.y, cursor.0, cursor.1));
        m.state = MoaState::Dragging;
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
        let dt = dt.clamp(0.0, 0.1); // No jump after sleep or a busy main thread.
        if let Some((ox, oy, sx, sy)) = self.drag {
            let (x, y) = self.area.clamp(cursor.0 - ox, cursor.1 - oy);
            self.view.moa.x = x;
            self.view.moa.y = y;
            if !down {
                self.drag = None;
                self.view.moa.state = MoaState::Idle;
                self.schedule(now);
                if (cursor.0 - sx).hypot(cursor.1 - sy) < 5.0 {
                    self.react(now);
                }
            }
        } else {
            match self.view.moa.state {
                MoaState::Idle if now >= self.next_walk => {
                    let offset = (self.random() - 0.5) * 360.0;
                    self.target = self.area.clamp(self.view.moa.x + offset, self.view.moa.y).0;
                    self.view.moa.facing = if self.target >= self.view.moa.x {
                        1
                    } else {
                        -1
                    };
                    self.view.moa.state = MoaState::Walking;
                    self.walk_end = now + 5.0;
                }
                MoaState::Walking => {
                    let d = self.target - self.view.moa.x;
                    self.view.moa.x += d.signum() * d.abs().min(40.0 * dt);
                    if d.abs() < 1.0 || now >= self.walk_end {
                        self.view.moa.state = MoaState::Idle;
                        self.schedule(now);
                    }
                }
                MoaState::Reacting if now >= self.reaction_end => {
                    self.view.moa.state = MoaState::Idle;
                    self.schedule(now);
                }
                _ => {}
            }
        }
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
                    if distance < 130.0 && self.view.moa.state != MoaState::Dragging {
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
            self.view.moa.facing = if self.view.pip.as_ref().unwrap().x >= self.view.moa.x {
                1
            } else {
                -1
            };
            self.react(now);
        }
        if remove {
            self.view.pip = None;
        }
        let (x, y) = self.area.clamp(self.view.moa.x, self.view.moa.y);
        self.view.moa.x = x;
        self.view.moa.y = y;
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
    fn walk_interval() {
        let mut w = world();
        for _ in 0..1000 {
            w.schedule(10.0);
            assert!((40.0..=70.0).contains(&w.next_walk));
        }
    }
    #[test]
    fn walk_cycle() {
        let mut w = world();
        w.tick(61.0, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.state, MoaState::Walking);
        w.tick(67.0, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.state, MoaState::Idle);
    }
    #[test]
    fn drag_clamps_and_recovers() {
        let mut w = world();
        w.drag((w.view.moa.x, w.view.moa.y));
        w.tick(1.0, 0.03, (9000.0, -9000.0), true);
        assert_eq!(w.view.moa.x, -96.0);
        assert_eq!(w.view.moa.y, 60.0);
        w.tick(2.0, 0.03, (9000.0, -9000.0), false);
        assert_eq!(w.view.moa.state, MoaState::Idle);
    }
    #[test]
    fn click_reaction() {
        let mut w = world();
        let p = (w.view.moa.x, w.view.moa.y);
        w.drag(p);
        w.tick(0.1, 0.03, p, false);
        assert_eq!(w.view.moa.state, MoaState::Reacting);
        w.tick(2.0, 0.03, p, false);
        assert_eq!(w.view.moa.state, MoaState::Idle);
    }
    #[test]
    fn pip_lifecycle() {
        let mut w = world();
        w.spawn(0.0);
        assert_eq!(w.view.pip.as_ref().unwrap().state, PipState::Spawning);
        w.tick(1.0, 0.03, (0.0, 0.0), false);
        w.view.pip.as_mut().unwrap().x = w.view.moa.x + 110.0;
        w.tick(1.1, 0.03, (0.0, 0.0), false);
        assert_eq!(w.view.moa.state, MoaState::Reacting);
        w.interact();
        assert!(w.view.menu);
        w.close();
        assert!(!w.view.menu);
        w.despawn(2.0);
        w.tick(3.0, 0.03, (0.0, 0.0), false);
        assert!(w.view.pip.is_none());
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
