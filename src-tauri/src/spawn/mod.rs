//! Desktop orchestration only. No HTTP, OS tracking, monster selection or entity mutation.
use crate::{desktop::DesktopSafeArea, geometry::Size, movement::MovementProfile};
use std::time::{Duration, Instant};
mod dex_adapter;
pub mod runtime;

pub trait Clock {
    fn now(&self) -> Duration;
}
pub struct SystemClock(Instant);
impl Default for SystemClock {
    fn default() -> Self {
        Self(Instant::now())
    }
}
impl Clock for SystemClock {
    fn now(&self) -> Duration {
        self.0.elapsed()
    }
}
/// Adapts the existing World monotonic timestamp; never reads a wall clock.
pub struct WorldClock(pub f64);
impl Clock for WorldClock {
    fn now(&self) -> Duration {
        Duration::try_from_secs_f64(self.0).unwrap_or_default()
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SpawnZone {
    Bottom,
    Top,
    LeftEdge,
    RightEdge,
    FreeArea,
    NearDock,
    LowerCorner,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SpawnCondition {
    AnyTime,
    Day,
    Night,
    FocusSession,
    SpecialEvent,
}
impl SpawnCondition {
    /// Only ANY_TIME is enabled in v0.1; no inferred OS/user activity.
    pub fn enabled(self) -> bool {
        self == Self::AnyTime
    }
}
#[derive(Clone, Debug)]
pub struct Candidate {
    pub monster_code: String,
    pub zone: SpawnZone,
    pub movement_profile: MovementProfile,
    pub size: Size,
    pub lifetime: Duration,
    pub condition: SpawnCondition,
}
/// Metadata lookup AFTER authoritative selection. Must not select a server monster.
pub trait SpawnCandidateProvider {
    fn candidate(&self, server_monster_code: &str) -> Option<Candidate>;
}
pub struct ContentProvider;
impl SpawnCandidateProvider for ContentProvider {
    fn candidate(&self, code: &str) -> Option<Candidate> {
        dex_adapter::content_candidate(code)
    }
}
#[derive(Clone, Debug)]
pub struct SpawnIntent {
    pub monster_code: String,
    pub spawn_zone: SpawnZone,
    pub movement_profile: MovementProfile,
    pub requested_at: Duration,
    /// Presentation hint, always capped by the authoritative remaining lease.
    pub lifetime: Duration,
    pub reason: &'static str,
    pub position: (f64, f64),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SpawnState {
    Waiting,
    Requesting,
    Active,
    Cooldown,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Reconciliation {
    Required,
    Complete,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Opportunity {
    Reconcile,
    RequestEncounter,
}
#[derive(Clone, Copy)]
pub struct Config {
    pub max_wild_monsters: usize,
    pub minimum_cooldown: Duration,
    pub maximum_cooldown: Duration,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            max_wild_monsters: 1,
            minimum_cooldown: Duration::from_secs(120),
            maximum_cooldown: Duration::from_secs(300),
        }
    }
}
pub struct SeededRandom(u64);
impl SeededRandom {
    pub fn new(seed: u64) -> Self {
        Self(seed)
    }
    fn unit(&mut self) -> f64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1);
        (self.0 >> 11) as f64 / ((1_u64 << 53) as f64)
    }
}
pub struct Director {
    enabled: bool,
    state: SpawnState,
    reconciliation: Reconciliation,
    next_spawn_at: Duration,
    config: Config,
    random: SeededRandom,
    failures: usize,
    pending: Option<Opportunity>,
}
impl Director {
    pub fn new(enabled: bool, seed: u64, config: Config) -> Result<Self, &'static str> {
        if config.max_wild_monsters == 0
            || config.minimum_cooldown.is_zero()
            || config.maximum_cooldown < config.minimum_cooldown
            || config.maximum_cooldown > Duration::from_secs(86400)
        {
            return Err("invalid spawn budget/cooldown");
        }
        Ok(Self {
            enabled,
            state: SpawnState::Waiting,
            reconciliation: Reconciliation::Required,
            next_spawn_at: Duration::ZERO,
            config,
            random: SeededRandom::new(seed),
            failures: 0,
            pending: None,
        })
    }
    pub fn disabled(seed: u64) -> Self {
        Self::new(false, seed, Config::default()).expect("valid defaults")
    }
    pub fn adopt(&mut self) {
        self.state = SpawnState::Active;
        self.reconciliation = Reconciliation::Complete;
    }
    pub fn state(&self) -> SpawnState {
        self.state
    }
    pub fn next_spawn_at(&self) -> Duration {
        self.next_spawn_at
    }
    fn cooldown(&mut self, now: Duration) {
        let spread = self.config.maximum_cooldown - self.config.minimum_cooldown;
        let delay = self.config.minimum_cooldown + spread.mul_f64(self.random.unit());
        self.next_spawn_at = now.saturating_add(delay);
        self.state = SpawnState::Cooldown;
    }
    /// Call from the existing World tick. No RNG, provider, allocation or OS calls before due.
    /// occupied counts server entities only, including encounters with no visible entity.
    pub fn tick(
        &mut self,
        clock: &impl Clock,
        occupied: usize,
        server_active: bool,
    ) -> Option<Opportunity> {
        if !self.enabled || matches!(self.state, SpawnState::Requesting | SpawnState::Active) {
            return None;
        }
        let now = clock.now();
        if now < self.next_spawn_at {
            return None;
        }
        if self.state == SpawnState::Cooldown {
            self.state = SpawnState::Waiting;
            return None;
        }
        if server_active || occupied >= self.config.max_wild_monsters {
            self.cooldown(now);
            return None;
        }
        let action = match self.reconciliation {
            Reconciliation::Required => Opportunity::Reconcile,
            Reconciliation::Complete => Opportunity::RequestEncounter,
        };
        self.state = SpawnState::Requesting;
        self.pending = Some(action);
        Some(action)
    }
    /// Complete one serialized GET-active/POST operation. None means a confirmed empty GET/POST.
    /// Existing active encounter always wins, even if placement is unavailable.
    pub fn resolved(&mut self, clock: &impl Clock, active: bool) {
        if self.state != SpawnState::Requesting {
            return;
        }
        let was_reconcile = self.pending == Some(Opportunity::Reconcile);
        self.pending = None;
        self.failures = 0;
        self.reconciliation = Reconciliation::Complete;
        if active {
            self.state = SpawnState::Active;
        } else if was_reconcile
            && !self.next_spawn_at.is_zero()
            && clock.now() >= self.next_spawn_at
        {
            // Cooldown/backoff was already paid before reconciliation. Do not double it.
            self.state = SpawnState::Waiting;
        } else {
            self.cooldown(clock.now());
        }
    }
    pub fn failed(&mut self, clock: &impl Clock) {
        if self.state != SpawnState::Requesting {
            return;
        }
        self.pending = None;
        // A lost POST response may already have committed: GET active before another POST.
        self.reconciliation = Reconciliation::Required;
        let seconds = [5, 10, 30][self.failures.min(2)];
        self.failures = (self.failures + 1).min(3);
        self.next_spawn_at = clock.now().saturating_add(Duration::from_secs(seconds));
        self.state = SpawnState::Cooldown;
    }
    /// Server-confirmed terminal/removal; local lease expiry alone must not clear authority.
    pub fn removed(&mut self, clock: &impl Clock) {
        if self.state == SpawnState::Active {
            self.reconciliation = Reconciliation::Required;
            self.cooldown(clock.now());
        }
    }
}

pub struct Environment<'a> {
    pub safe_area: &'a DesktopSafeArea,
    pub cursor: Option<(f64, f64)>,
    pub windows: Option<&'a [crate::geometry::Area]>,
}
/// Bounded candidate search using the selected monitor's final safe area only.
pub fn placement(
    candidate: &Candidate,
    environment: &Environment<'_>,
    seed: u64,
) -> Option<(f64, f64)> {
    let a = environment.safe_area.final_luma_safe_area;
    let s = candidate.size;
    let cursor = environment.cursor?;
    let windows = environment.windows?;
    if ![a.x, a.y, a.w, a.h, s.width, s.height, cursor.0, cursor.1]
        .iter()
        .all(|n| n.is_finite())
        || s.width <= 0.0
        || s.height <= 0.0
        || !a.fits(s)
        || windows
            .iter()
            .any(|w| ![w.x, w.y, w.w, w.h].iter().all(|v| v.is_finite()) || w.w < 0.0 || w.h < 0.0)
    {
        return None;
    }
    let (left, bottom) = a.clamp(f64::MIN, f64::MIN, s);
    let (right, top) = a.clamp(f64::MAX, f64::MAX, s);
    let mut rng = SeededRandom::new(seed);
    for _ in 0..16 {
        let u = rng.unit();
        let v = rng.unit();
        let x = left + (right - left) * u;
        let y = bottom + (top - bottom) * v;
        let p = match candidate.zone {
            SpawnZone::Bottom | SpawnZone::NearDock => (x, bottom),
            SpawnZone::Top => (x, top),
            SpawnZone::LeftEdge => (left, y),
            SpawnZone::RightEdge => (right, y),
            SpawnZone::FreeArea => (x, y),
            SpawnZone::LowerCorner => (if u < 0.5 { left } else { right }, bottom),
        };
        // Integral native presentation bounds are the actual safety/avoidance envelope.
        let bounds = a.panel_bounds(p.0, p.1, s);
        let p = (bounds.x + bounds.w / 2.0, bounds.y);
        if crate::movement::unobstructed(p, p, 0.0, s, cursor, Some(windows), 100.0)
            && !environment.safe_area.detected_dock_bounds.iter().any(|d| {
                bounds.x < d.x + d.w
                    && bounds.x + bounds.w > d.x
                    && bounds.y < d.y + d.h
                    && bounds.y + bounds.h > d.y
            })
        {
            return Some(p);
        }
    }
    None
}
/// Called only with a validated server Encounter, never an opportunity/debug monster.
pub fn intent_for_encounter(
    encounter: &crate::backend::Encounter,
    remaining: Duration,
    requested_at: Duration,
    provider: &impl SpawnCandidateProvider,
    environment: &Environment<'_>,
    seed: u64,
) -> Option<SpawnIntent> {
    if encounter.encounter_id.is_nil() || remaining.is_zero() {
        return None;
    }
    let candidate = provider.candidate(&encounter.monster.code)?;
    if candidate.monster_code != encounter.monster.code
        || !candidate.condition.enabled()
        || !metadata_matches(encounter, &candidate)
        || candidate.lifetime.is_zero()
    {
        return None;
    }
    Some(SpawnIntent {
        position: placement(&candidate, environment, seed)?,
        monster_code: candidate.monster_code,
        spawn_zone: candidate.zone,
        movement_profile: candidate.movement_profile,
        requested_at,
        lifetime: candidate.lifetime.min(remaining),
        reason: "server-confirmed encounter",
    })
}
#[cfg(test)]
mod tests;

pub fn metadata_matches(encounter: &crate::backend::Encounter, candidate: &Candidate) -> bool {
    serde_json::from_value::<MovementProfile>(serde_json::Value::String(
        encounter.monster.movement_profile.clone(),
    ))
    .ok()
        == Some(candidate.movement_profile)
        && dex_adapter::identity(&encounter.monster.code)
            .is_some_and(|m| m.rarity == encounter.monster.rarity)
}
pub use dex_adapter::{identity, MonsterIdentity};
