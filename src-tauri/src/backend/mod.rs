pub mod battle;
use battle::{Battle, Capture, Collected, Command};
// Local HTTP client, DTO validation and bounded worker. No AppKit/React calls.
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
    #[serde(default)]
    pub battle_id: Option<uuid::Uuid>,
    #[serde(default)]
    pub expiration_suspended: bool,
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
        if self.expiration_suspended {
            return f64::MAX / 2.0;
        }
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
        let status = response.status();
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
        if status != reqwest::StatusCode::OK {
            let code = serde_json::from_slice::<serde_json::Value>(&bytes).ok();
            return Err(
                match code
                    .as_ref()
                    .and_then(|v| v.get("code"))
                    .and_then(|v| v.as_str())
                {
                    Some("ENCOUNTER_NOT_FOUND") => "Encounter not found",
                    Some("BATTLE_NOT_FOUND") => "Battle not found",
                    Some("ENCOUNTER_EXPIRED") => "Encounter expired",
                    Some("BATTLE_ALREADY_TERMINAL") => "Battle already terminal; refresh state",
                    Some("CAPTURE_ALREADY_RESOLVED") => "Capture already resolved; refresh state",
                    Some("INVALID_STATE") => "Invalid game state; refresh state",
                    Some("GAME_UNAVAILABLE") => "Game unavailable",
                    _ => "server returned non-success status",
                },
            );
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
    Battle(Battle),
    Capture(Capture),
    Collection(Vec<Collected>),
    Finished(Option<String>),
}
pub struct Backend {
    requests: SyncSender<Command>,
    events: Receiver<Event>,
    open: Arc<AtomicBool>,
}
impl Backend {
    pub fn start(stopped: Arc<AtomicBool>) -> Self {
        let (requests, rx) = mpsc::sync_channel(1);
        let (events, receiver) = mpsc::sync_channel(8);
        let open = Arc::new(AtomicBool::new(false));
        let visible = open.clone();
        std::thread::spawn(move || {
            let base = std::env::var("LUMA_GAME_SERVER_URL")
                .unwrap_or_else(|_| "http://127.0.0.1:8081".into());
            let api = match Api::new(&base) {
                Ok(a) => a,
                Err(e) => {
                    let _ = events.send(Event::Finished(Some(e.into())));
                    return;
                }
            };
            let mut bootstrapped = false;
            let mut command = None;
            let mut last_error = None;
            let mut last_battle = None;
            while !stopped.load(Ordering::Relaxed) {
                let explicit = command.is_some();
                let result = (|| {
                    if !bootstrapped {
                        events
                            .send(Event::Bootstrap(api.bootstrap()?))
                            .map_err(|_| "closed")?;
                        bootstrapped = true;
                    }
                    match command.take() {
                        Some(Command::StartBattle(id)) => {
                            events
                                .send(Event::Battle(api.battle(id, Some("start"))?))
                                .map_err(|_| "closed")?;
                        }
                        Some(Command::Attack(id)) => {
                            events
                                .send(Event::Battle(api.battle(id, Some("attack"))?))
                                .map_err(|_| "closed")?;
                        }
                        Some(Command::Capture(id)) => {
                            events
                                .send(Event::Capture(api.capture(id)?))
                                .map_err(|_| "closed")?;
                        }
                        Some(Command::Ignore(id)) => {
                            api.ignore(id)?;
                        }
                        Some(Command::LoadCollection) => {
                            events
                                .send(Event::Collection(api.collection()?))
                                .map_err(|_| "closed")?;
                        }
                        Some(Command::Refresh(id)) => {
                            events
                                .send(Event::Battle(api.battle(id, None)?))
                                .map_err(|_| "closed")?;
                        }
                        Some(Command::Encounter) => {
                            events
                                .send(Event::Encounter(api.encounter(true)?))
                                .map_err(|_| "closed")?;
                        }
                        None => {}
                    }
                    let e = api.encounter(false)?;
                    if let Some(id) = e.as_ref().and_then(|e| e.battle_id) {
                        last_battle = Some(id);
                    }
                    if visible.load(Ordering::Relaxed) {
                        if let Some(id) = e.as_ref().and_then(|e| e.battle_id).or(last_battle) {
                            last_battle = Some(id);
                            events
                                .send(Event::Battle(api.battle(id, None)?))
                                .map_err(|_| "closed")?;
                        }
                    }
                    if e.as_ref().is_some_and(|e| !e.supports_pip()) {
                        events.send(Event::Encounter(None)).map_err(|_| "closed")?;
                        return Err("unsupported monster/profile; presentation skipped");
                    }
                    events.send(Event::Encounter(e)).map_err(|_| "closed")?;
                    if explicit {
                        events
                            .send(Event::Bootstrap(api.bootstrap()?))
                            .map_err(|_| "closed")?;
                    }
                    Ok::<(), &'static str>(())
                })();
                if explicit {
                    let _ =
                        events.send(Event::Finished(result.as_ref().err().map(|e| (*e).into())));
                }
                match result {
                    Err(e) if last_error != Some(e) => {
                        eprintln!("[LUMA BACKEND] {e}; local Companion continues");
                        last_error = Some(e);
                    }
                    Ok(()) if last_error.take().is_some() => {
                        eprintln!("[LUMA BACKEND] connection restored")
                    }
                    _ => {}
                }
                // Discard a failed mutation; only a new explicit command may retry it.
                command = match rx.recv_timeout(Duration::from_secs(5)) {
                    Ok(c) => Some(c),
                    Err(mpsc::RecvTimeoutError::Timeout) => None,
                    Err(_) => break,
                };
            }
        });
        Self {
            requests,
            events: receiver,
            open,
        }
    }
    pub fn set_open(&self, open: bool) {
        self.open.store(open, Ordering::Relaxed);
    }
    pub fn request(&self, c: Command) -> bool {
        self.requests.try_send(c).is_ok()
    }
    pub fn event(&self) -> Option<Event> {
        self.events.try_recv().ok()
    }
}
#[cfg(test)]
mod tests;
