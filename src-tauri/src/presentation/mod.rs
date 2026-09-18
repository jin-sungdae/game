#[cfg(debug_assertions)]
pub mod smoke;
// Transient visual timeline only. Never writes server HP, world position or entity state.
use crate::backend::{
    battle::{Battle, Capture, Reward},
    Bootstrap,
};
use serde::Serialize;
use std::collections::VecDeque;
#[derive(Clone, Copy, Debug, Default, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Phase {
    #[default]
    Idle,
    Requesting,
    PlayerAttack,
    MonsterHit,
    MonsterAttack,
    PlayerHit,
    Victory,
    Capturing,
    CaptureSuccess,
    CaptureFail,
    Reward,
    LevelUp,
    Error,
}
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Level {
    pub from: u32,
    pub to: u32,
}
#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Visual {
    pub phase: Phase,
    pub serial: u64,
    pub damage: Option<u32>,
    pub reward: Option<Reward>,
    pub level: Option<Level>,
}
#[derive(Clone)]
struct Cue {
    phase: Phase,
    duration: f64,
    damage: Option<u32>,
    reward: Option<Reward>,
    level: Option<Level>,
}
impl Cue {
    fn new(phase: Phase, duration: f64) -> Self {
        Self {
            phase,
            duration,
            damage: None,
            reward: None,
            level: None,
        }
    }
}
#[derive(Default)]
pub struct Controller {
    pub view: Visual,
    queue: VecDeque<Cue>,
    deadline: f64,
    battle_id: Option<uuid::Uuid>,
    last_turn: Option<u32>,
    reward_shown: bool,
    last_capture: Option<(uuid::Uuid, u32)>,
    level: Option<(u64, u32)>,
}
impl Controller {
    fn enqueue(&mut self, c: Cue) {
        if self.queue.len() == 24 {
            self.queue.pop_front();
        }
        self.queue.push_back(c);
    }
    fn start(&mut self, c: Cue, now: f64) {
        self.view = Visual {
            phase: c.phase,
            serial: self.view.serial.wrapping_add(1),
            damage: c.damage,
            reward: c.reward,
            level: c.level,
        };
        self.deadline = now + c.duration;
    }
    fn clear_request(&mut self) {
        if matches!(self.view.phase, Phase::Requesting | Phase::Capturing) {
            self.deadline = 0.0;
        }
    }
    pub fn request(&mut self, action: &str, now: f64) {
        // New explicit requests supersede stale transient visuals, not authoritative state.
        self.queue
            .retain(|c| matches!(c.phase, Phase::Reward | Phase::LevelUp));
        self.start(
            Cue::new(
                if action == "capture" {
                    Phase::Capturing
                } else {
                    Phase::Requesting
                },
                f64::MAX / 2.0,
            ),
            now,
        );
    }
    pub fn finish(&mut self, error: bool, now: f64) {
        if error {
            self.queue.clear();
            self.start(Cue::new(Phase::Error, 2.0), now);
        } else {
            self.clear_request();
        }
    }
    pub fn bootstrap(&mut self, b: &Bootstrap) {
        let c = &b.active_companion;
        if let Some((id, old)) = self.level {
            if id == c.player_companion_id && c.level > old {
                let mut cue = Cue::new(Phase::LevelUp, 2.0);
                cue.level = Some(Level {
                    from: old,
                    to: c.level,
                });
                self.enqueue(cue);
            }
        }
        self.level = Some((c.player_companion_id, c.level));
    }
    pub fn battle(&mut self, b: &Battle) {
        if self.battle_id != Some(b.battle_id) {
            self.battle_id = Some(b.battle_id);
            self.last_turn = None;
            self.reward_shown = false;
        }
        // Poll/restore snapshots carry no transient events and never replay reward toasts.
        if b.events.is_empty() || self.last_turn.is_some_and(|t| b.turn <= t) {
            return;
        }
        self.clear_request();
        self.last_turn = Some(b.turn);
        for e in &b.presentation_events {
            let (attack, hit) = match e.r#type.as_str() {
                "PLAYER_ATTACK" => (Phase::PlayerAttack, Phase::MonsterHit),
                "MONSTER_ATTACK" => (Phase::MonsterAttack, Phase::PlayerHit),
                _ => continue,
            };
            self.enqueue(Cue::new(attack, 0.14));
            let mut c = Cue::new(hit, 0.65);
            c.damage = Some(e.damage);
            self.enqueue(c);
        }
        if b.events.iter().any(|e| e == "VICTORY") {
            self.enqueue(Cue::new(Phase::Victory, 0.5));
        }
        if b.events.iter().any(|e| e == "REWARD") && !self.reward_shown {
            if let Some(r) = &b.reward {
                let mut c = Cue::new(Phase::Reward, 2.5);
                c.reward = Some(r.clone());
                self.enqueue(c);
                self.reward_shown = true;
            }
        }
    }
    pub fn capture(&mut self, c: &Capture, now: f64) {
        let key = (c.battle_id, c.battle.turn);
        if self.last_capture == Some(key) {
            return;
        }
        self.last_capture = Some(key);
        let pending: Vec<_> = self
            .queue
            .drain(..)
            .filter(|c| matches!(c.phase, Phase::Reward | Phase::LevelUp))
            .collect();
        self.start(
            Cue::new(
                if c.success {
                    Phase::CaptureSuccess
                } else {
                    Phase::CaptureFail
                },
                0.4,
            ),
            now,
        );
        self.battle(&c.battle);
        for cue in pending {
            self.enqueue(cue);
        }
    }
    pub fn tick(&mut self, now: f64) -> bool {
        if self.view.phase != Phase::Idle && now < self.deadline {
            return false;
        }
        if let Some(c) = self.queue.pop_front() {
            self.start(c, now);
            true
        } else if self.view.phase != Phase::Idle {
            self.start(Cue::new(Phase::Idle, 0.0), now);
            true
        } else {
            false
        }
    }
}
#[cfg(test)]
mod tests;
