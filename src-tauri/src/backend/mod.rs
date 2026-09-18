//! Local HTTP client, DTO validation and bounded worker. No AppKit/React calls.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, SyncSender},
        Arc,
    },
    time::Duration,
};
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Player {
    pub player_id: u64,
    pub name: String,
    pub gold: u64,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Companion {
    pub player_companion_id: u64,
    pub species: String,
    pub evolution_stage: u32,
    pub evolution_name: String,
    pub level: u32,
    pub exp: u64,
    pub bond: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Bootstrap {
    pub player: Player,
    pub active_companion: Companion,
}
impl Bootstrap {
    fn valid(&self) -> bool {
        self.player.player_id > 0
            && !self.player.name.is_empty()
            && self.active_companion.player_companion_id > 0
            && (1..=5).contains(&self.active_companion.evolution_stage)
            && self.active_companion.level > 0
            && !self.active_companion.species.is_empty()
            && !self.active_companion.evolution_name.is_empty()
    }
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Monster {
    pub code: String,
    pub name: String,
    pub level: u32,
    pub rarity: String,
    pub movement_profile: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Encounter {
    pub encounter_id: uuid::Uuid,
    pub monster: Monster,
    pub spawned_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
}
impl Encounter {
    pub fn supports_pip(&self) -> bool {
        self.monster.code == "PIP"
            && self.monster.movement_profile == "GROUND"
            && self.monster.level > 0
            && self.expires_at > self.spawned_at
            && !self.encounter_id.is_nil()
    }
    pub fn remaining_at(&self, now: DateTime<Utc>) -> f64 {
        (self.expires_at - now).num_milliseconds().max(0) as f64 / 1000.0
    }
}
pub struct Api {
    base: String,
    client: reqwest::blocking::Client,
}
impl Api {
    pub fn new(base: &str) -> Result<Self, &'static str> {
        let url = reqwest::Url::parse(base).map_err(|_| "invalid LUMA_GAME_SERVER_URL")?;
        if url.scheme() != "http"
            || !matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "[::1]"))
            || !url.username().is_empty()
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
            || url.path() != "/"
        {
            return Err("LUMA_GAME_SERVER_URL must be a loopback HTTP origin");
        }
        let client = reqwest::blocking::Client::builder()
            .no_proxy()
            .redirect(reqwest::redirect::Policy::none())
            .connect_timeout(Duration::from_secs(1))
            .timeout(Duration::from_secs(3))
            .build()
            .map_err(|_| "HTTP client initialization failed")?;
        Ok(Self {
            base: base.trim_end_matches('/').to_owned(),
            client,
        })
    }
    fn request<T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        post: bool,
    ) -> Result<Option<T>, &'static str> {
        let url = format!("{}{path}", self.base);
        let response = if post {
            self.client.post(url)
        } else {
            self.client.get(url)
        }
        .send()
        .map_err(|_| "server unavailable")?;
        if response.status() == reqwest::StatusCode::NO_CONTENT {
            return Ok(None);
        }
        if response.status() != reqwest::StatusCode::OK {
            return Err("server returned non-success status");
        }
        // Bound local-server response allocation, and reject malformed JSON without mutating the world.
        use std::io::Read;
        let mut bytes = Vec::new();
        response
            .take(65537)
            .read_to_end(&mut bytes)
            .map_err(|_| "response read failed")?;
        if bytes.len() > 65536 {
            return Err("response exceeds limit");
        }
        serde_json::from_slice(&bytes)
            .map(Some)
            .map_err(|_| "invalid server response")
    }
    pub fn bootstrap(&self) -> Result<Bootstrap, &'static str> {
        let b: Bootstrap = self
            .request("/api/v1/game/bootstrap", false)?
            .ok_or("missing bootstrap")?;
        if !b.valid() {
            return Err("invalid bootstrap");
        }
        Ok(b)
    }
    pub fn encounter(&self, create: bool) -> Result<Option<Encounter>, &'static str> {
        let e: Option<Encounter> = self.request(
            if create {
                "/api/v1/encounters"
            } else {
                "/api/v1/encounters/active"
            },
            create,
        )?;
        if e.as_ref().is_some_and(|e| {
            e.expires_at <= e.spawned_at || e.monster.level == 0 || e.encounter_id.is_nil()
        }) {
            return Err("invalid encounter");
        }
        Ok(e)
    }
}
pub enum Event {
    Bootstrap(Bootstrap),
    Encounter(Option<Encounter>),
}
pub struct Backend {
    requests: SyncSender<()>,
    events: Receiver<Event>,
}
impl Backend {
    pub fn start(stopped: Arc<AtomicBool>) -> Self {
        let (requests, rx) = mpsc::sync_channel(1);
        let (events, receiver) = mpsc::sync_channel(8);
        std::thread::spawn(move || {
            let base = std::env::var("LUMA_GAME_SERVER_URL")
                .unwrap_or_else(|_| "http://127.0.0.1:8081".into());
            let api = match Api::new(&base) {
                Ok(api) => api,
                Err(e) => {
                    eprintln!("[LUMA BACKEND] {e}; local Companion continues");
                    return;
                }
            };
            let mut bootstrapped = false;
            let mut create = false;
            let mut last_error = None;
            while !stopped.load(Ordering::Relaxed) {
                let result = (|| {
                    if !bootstrapped {
                        let b = api.bootstrap()?;
                        let _ = events.try_send(Event::Bootstrap(b));
                        bootstrapped = true;
                    }
                    let encounter = api.encounter(create)?;
                    if encounter.as_ref().is_some_and(|e| !e.supports_pip()) {
                        let _ = events.try_send(Event::Encounter(None));
                        return Err("unsupported monster/profile; presentation skipped");
                    }
                    let _ = events.try_send(Event::Encounter(encounter));
                    Ok::<(), &'static str>(())
                })();
                match result {
                    Err(error) if last_error != Some(error) => {
                        eprintln!("[LUMA BACKEND] {error}; local Companion continues");
                        last_error = Some(error);
                    }
                    Ok(()) if last_error.take().is_some() => {
                        eprintln!("[LUMA BACKEND] connection restored");
                    }
                    _ => {}
                }
                match rx.recv_timeout(Duration::from_secs(5)) {
                    Ok(()) => create = true,
                    Err(mpsc::RecvTimeoutError::Timeout) => create = false,
                    Err(mpsc::RecvTimeoutError::Disconnected) => break,
                }
            }
        });
        Self {
            requests,
            events: receiver,
        }
    }
    pub fn request_encounter(&self) {
        if let Err(e) = self.requests.try_send(()) {
            eprintln!("[LUMA BACKEND] request not queued: {e}");
        }
    }
    pub fn event(&self) -> Option<Event> {
        self.events.try_recv().ok()
    }
}
#[cfg(test)]
mod tests;
