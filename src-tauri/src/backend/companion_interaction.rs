//! Explicit interaction intent and acknowledged-only relationship presentation.
use super::{evolution, Api, Bootstrap};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Outcome {
    Awarded,
    Cooldown,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Result {
    pub outcome: Outcome,
    pub bond_delta: u32,
    pub server_time: DateTime<Utc>,
    pub next_available_at: DateTime<Utc>,
    pub bootstrap: Bootstrap,
    pub evolution: evolution::Eligibility,
}
impl Result {
    fn valid(&self) -> bool {
        let c = &self.bootstrap.active_companion;
        self.bootstrap.valid()
            && self.evolution.valid()
            && self.evolution.species == c.species
            && self.evolution.current_stage == c.evolution_stage
            && self.evolution.current_name == c.evolution_name
            && self.next_available_at > self.server_time
            && match self.outcome {
                Outcome::Awarded => self.bond_delta == 1 && c.bond >= self.bond_delta,
                Outcome::Cooldown => self.bond_delta == 0,
            }
    }
}
impl Api {
    pub fn interact_companion(&self) -> std::result::Result<Result, &'static str> {
        let result: Result = self
            .request("/api/v1/companions/active/interact", true)?
            .ok_or("missing companion interaction")?;
        if !result.valid() {
            return Err("invalid companion interaction");
        }
        Ok(result)
    }
}
#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Presentation {
    pub busy: bool,
    pub feedback: Option<String>,
    pub next_available_at: Option<DateTime<Utc>>,
    #[serde(skip)]
    clear_at: f64,
}
impl Presentation {
    pub fn request(&mut self) -> bool {
        if self.busy {
            return false;
        }
        self.busy = true;
        true
    }
    pub fn acknowledge(&mut self, result: &Result, now: f64) {
        self.busy = false;
        self.next_available_at = Some(result.next_available_at);
        self.feedback =
            (result.outcome == Outcome::Awarded).then(|| format!("Bond +{}", result.bond_delta));
        self.clear_at = now + 3.0;
    }
    pub fn fail(&mut self) {
        self.busy = false;
        self.feedback = None; // Ambient input never opens an error popup or replays a mutation.
    }
    pub fn tick(&mut self, now: f64) -> bool {
        if self.feedback.is_some() && now >= self.clear_at {
            self.feedback = None;
            return true;
        }
        false
    }
}
#[cfg(test)]
mod tests;
