//! Server-owned eligibility and acknowledged-only local presentation.
use super::{Api, Bootstrap, Companion};
use serde::{Deserialize, Serialize};
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Status {
    Locked,
    Available,
    MaxStage,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Requirement {
    pub required: u32,
    pub current: u32,
    pub met: bool,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Requirements {
    pub level: Requirement,
    pub bond: Requirement,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Eligibility {
    pub status: Status,
    pub species: String,
    pub current_stage: u32,
    pub current_name: String,
    pub next_stage: Option<u32>,
    pub next_name: Option<String>,
    pub requirements: Option<Requirements>,
}
impl Eligibility {
    fn valid(&self) -> bool {
        !self.species.is_empty()
            && !self.current_name.is_empty()
            && (1..=5).contains(&self.current_stage)
            && match (self.next_stage, &self.next_name, &self.requirements) {
                (Some(stage), Some(name), Some(_)) => {
                    stage == self.current_stage + 1 && stage <= 5 && !name.is_empty()
                }
                (None, None, None) => self.status != Status::Available,
                _ => false,
            }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Outcome {
    Evolved,
    AlreadyEvolved,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Result {
    pub result: Outcome,
    pub evolution: Eligibility,
    pub bootstrap: Bootstrap,
}
impl Api {
    pub fn evolution(&self) -> std::result::Result<Eligibility, &'static str> {
        let value: Eligibility = self
            .request("/api/v1/companions/active/evolution", false)?
            .ok_or("missing evolution")?;
        if !value.valid() {
            return Err("invalid evolution");
        }
        Ok(value)
    }
    pub fn evolve(&self) -> std::result::Result<Result, &'static str> {
        let value: Result = self
            .request("/api/v1/companions/active/evolve", true)?
            .ok_or("missing evolution result")?;
        let c = &value.bootstrap.active_companion;
        if !value.bootstrap.valid()
            || !value.evolution.valid()
            || c.species != "MOA"
            || c.evolution_stage != 2
            || c.species != value.evolution.species
            || c.evolution_stage != value.evolution.current_stage
            || c.evolution_name != value.evolution.current_name
        {
            return Err("invalid evolution result");
        }
        Ok(value)
    }
}
#[derive(Clone, Debug, Default, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Phase {
    #[default]
    Idle,
    Glow,
    Reveal,
}
#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Presentation {
    pub eligibility: Option<Eligibility>,
    pub busy: bool,
    pub error: Option<String>,
    pub phase: Phase,
    pub previous: Option<Companion>,
    pub success: Option<String>,
    #[serde(skip)]
    started: f64,
}
impl Presentation {
    pub fn request(&mut self) -> bool {
        if self.busy
            || self.phase != Phase::Idle
            || self
                .eligibility
                .as_ref()
                .is_none_or(|s| s.status != Status::Available)
        {
            return false;
        }
        self.busy = true;
        self.error = None;
        self.success = None;
        true
    }
    pub fn acknowledge(&mut self, result: &Result, previous: Option<Companion>, now: f64) {
        self.eligibility = Some(result.evolution.clone());
        self.busy = false;
        self.error = None;
        self.success = Some(result.bootstrap.active_companion.evolution_name.clone());
        // Retry confirmation restores identity but never replays the transition.
        if result.result == Outcome::Evolved {
            self.previous = previous;
            self.started = now;
            self.phase = Phase::Glow;
        }
    }
    pub fn fail(&mut self, error: String) {
        self.busy = false;
        self.error = Some(error);
    }
    pub fn tick(&mut self, now: f64) -> bool {
        let next = if self.phase == Phase::Idle || now - self.started >= 1.6 {
            Phase::Idle
        } else if now - self.started >= 0.8 {
            Phase::Reveal
        } else {
            Phase::Glow
        };
        if next == self.phase {
            return false;
        }
        self.phase = next;
        if self.phase != Phase::Glow {
            self.previous = None;
        }
        true
    }
}
#[cfg(test)]
mod tests;
