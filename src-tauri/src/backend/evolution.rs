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
    pub(super) fn valid(&self) -> bool {
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
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Request {
    pub command_id: uuid::Uuid,
    pub expected_companion_id: u64,
    pub expected_stage: u32,
    pub expected_selection_revision: u64,
}
impl Request {
    fn from_bootstrap(value: &Bootstrap) -> Option<Self> {
        let revision = value.player.active_selection_revision?;
        if !value.valid()
            || revision > i64::MAX as u64
            || !matches!(
                value.active_companion.species.as_str(),
                "MOA" | "RUU" | "NOX"
            )
            || !(1..=4).contains(&value.active_companion.evolution_stage)
        {
            return None;
        }
        Some(Self {
            command_id: uuid::Uuid::new_v4(),
            expected_companion_id: value.active_companion.player_companion_id,
            expected_stage: value.active_companion.evolution_stage,
            expected_selection_revision: revision,
        })
    }
}
impl Api {
    pub fn evolve_command(&self, request: &Request) -> std::result::Result<Result, &'static str> {
        if request.command_id.is_nil()
            || request.expected_companion_id == 0
            || !(1..=4).contains(&request.expected_stage)
            || request.expected_selection_revision > i64::MAX as u64
        {
            return Err("invalid evolution command");
        }
        let body = serde_json::to_value(request).map_err(|_| "invalid evolution command")?;
        let value: Result = self
            .request_json("/api/v1/companions/active/evolve", Some(&body))?
            .ok_or("missing evolution result")?;
        let c = &value.bootstrap.active_companion;
        let expected = request.expected_stage + u32::from(value.result == Outcome::Evolved);
        if !value.bootstrap.valid()
            || !value.evolution.valid()
            || c.player_companion_id != request.expected_companion_id
            || c.evolution_stage != expected
            || !matches!(c.species.as_str(), "MOA" | "RUU" | "NOX")
            || value.bootstrap.player.active_selection_revision
                != Some(request.expected_selection_revision)
            || c.species != value.evolution.species
            || c.evolution_stage != value.evolution.current_stage
            || c.evolution_name != value.evolution.current_name
        {
            return Err("invalid evolution result");
        }
        Ok(value)
    }
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
            || !matches!(
                (c.evolution_stage, c.evolution_name.as_str()),
                (2, "MOKORI") | (3, "NEBLA")
            )
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
    #[serde(skip)]
    pending: Option<Request>,
}
impl Presentation {
    pub fn command(&mut self, bootstrap: Option<&Bootstrap>) -> Option<Request> {
        if self.busy || self.phase != Phase::Idle {
            return None;
        }
        // An ambiguous transport failure retries the same intent even after a status refresh.
        let request = match &self.pending {
            Some(request) => request.clone(),
            None => {
                if self
                    .eligibility
                    .as_ref()
                    .is_none_or(|s| s.status != Status::Available)
                {
                    return None;
                }
                Request::from_bootstrap(bootstrap?)?
            }
        };
        self.pending = Some(request.clone());
        self.busy = true;
        self.error = None;
        self.success = None;
        Some(request)
    }
    pub fn acknowledge_command(
        &mut self,
        request: &Request,
        result: &Result,
        current: &Bootstrap,
        previous: Option<Companion>,
        now: f64,
    ) -> bool {
        if self.pending.as_ref() != Some(request) {
            return false;
        }
        self.pending = None;
        self.busy = false;
        self.error = None;
        if current.active_companion.player_companion_id
            == result.bootstrap.active_companion.player_companion_id
            && current.active_companion.evolution_stage
                == result.bootstrap.active_companion.evolution_stage
            && current.player.active_selection_revision
                == result.bootstrap.player.active_selection_revision
        {
            self.acknowledge(result, previous, now);
        } else {
            self.phase = Phase::Idle;
            self.previous = None;
            self.success = None;
        }
        true
    }
    pub fn request_legacy(&mut self, bootstrap: Option<&Bootstrap>) -> bool {
        // Compatibility is capability-based, never an error fallback from a structured command.
        bootstrap.is_some_and(|b| {
            b.player.active_selection_revision.is_none()
                && b.active_companion.species == "MOA"
                && (1..=2).contains(&b.active_companion.evolution_stage)
        }) && self.pending.is_none()
            && self.request()
    }
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
        if matches!(
            error.as_str(),
            "COMMAND_ID_REUSED"
                | "STALE_SELECTION"
                | "STALE_STAGE"
                | "COMPANION_MISMATCH"
                | "EVOLUTION_COMMAND_REQUIRED"
                | "Evolution not eligible; refresh status"
                | "Maximum evolution stage"
        ) {
            self.pending = None;
        }
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
