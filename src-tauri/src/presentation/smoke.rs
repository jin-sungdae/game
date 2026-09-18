//! Opt-in debug validation driver, absent from release builds. Uses the same bounded commands as UI.
use crate::{
    backend::{battle::Status, Backend},
    behaviors::World,
};
#[derive(Default)]
pub struct Driver {
    step: u8,
    finished_at: Option<f64>,
}
impl Driver {
    pub fn tick(&mut self, w: &mut World, backend: &Backend, now: f64) -> bool {
        if now > 90.0 {
            eprintln!("[LUMA VISUAL SMOKE] FAIL timeout");
            return true;
        }
        if w.view.game.busy || w.view.visual.phase != super::Phase::Idle {
            return false;
        }
        if let Some(error) = &w.view.game.error {
            eprintln!("[LUMA VISUAL SMOKE] FAIL {error}");
            return true;
        }
        let action = match self.step {
            0 => {
                self.step = 1;
                Some("encounter")
            }
            1 if w.view.pip.is_some() => {
                w.interact();
                self.step = 2;
                Some("battle")
            }
            2 => match w.view.game.battle.as_ref().map(|b| &b.status) {
                Some(Status::Active) => Some("attack"),
                Some(Status::Victory) => {
                    self.step = 3;
                    Some("capture")
                }
                _ => None,
            },
            3 if w
                .view
                .game
                .battle
                .as_ref()
                .is_some_and(|b| b.encounter_status != "ACTIVE") =>
            {
                self.step = 4;
                Some("collection")
            }
            4 => {
                eprintln!(
                    "[LUMA VISUAL SMOKE] PASS complete collection={}",
                    w.view.game.collection.len()
                );
                self.step = 5;
                self.finished_at = Some(now);
                None
            }
            _ => None,
        };
        if let Some(action) = action {
            if let Some(command) = w.view.game.command(action) {
                w.presentation.request(action, now);
                eprintln!("[LUMA VISUAL SMOKE] command={action}");
                if !backend.request(command) {
                    w.view.game.finish(Some("Queue unavailable".into()));
                }
            }
        }
        self.finished_at.is_some_and(|t| now - t > 30.0)
    }
}
