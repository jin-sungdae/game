//! Authority and retry bookkeeping; no I/O, entity mutation or independent timer.
use super::*;
use crate::backend::Encounter;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Action {
    Reconcile,
    Create,
    Resolve(uuid::Uuid),
}
pub struct Runtime {
    pub director: Director,
    calendar: Box<dyn conditions::CalendarClock>,
    provider: Box<dyn SpawnCandidateProvider + Send>,
    pub encounter: Option<Encounter>,
    pub deadline: f64,
    pending: Option<Action>,
    placed: bool,
    attempts: usize,
    placement_at: f64,
    resolving: bool,
    resolution_at: f64,
    failures: usize,
    available_assets: std::collections::HashSet<String>,
}
impl Runtime {
    #[cfg(test)]
    pub(crate) fn set_test_calendar(&mut self, clock: Box<dyn conditions::CalendarClock>) {
        self.calendar = clock;
    }
    pub fn new(seed: u64) -> Self {
        Self {
            director: Director::new(true, seed, Config::default()).expect("valid spawn defaults"),
            calendar: Box::new(conditions::LocalClock),
            provider: Box::new(ContentProvider),
            encounter: None,
            deadline: 0.0,
            pending: None,
            placed: false,
            attempts: 0,
            placement_at: 0.0,
            resolving: false,
            resolution_at: 0.0,
            failures: 0,
            available_assets: Default::default(),
        }
    }
    pub fn load_assets(&mut self, mut load: impl FnMut(&str) -> Option<Vec<u8>>) {
        self.available_assets.clear();
        for code in [
            "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP",
            "SHADE", "EMBER", "LUNET", "NOVA", "NOCT",
        ] {
            let bytes = load(&format!("assets/monsters/{}/base.png", code.to_lowercase()));
            if assets::available(code, bytes.as_deref()) {
                self.available_assets.insert(code.into());
            }
        }
    }
    pub fn identity(&self, code: &str) -> Option<MonsterIdentity> {
        self.provider.identity(code)
    }
    pub fn hidden(&mut self) {
        self.placed = false;
    }
    pub fn observe(&mut self, now: f64, value: Option<Encounter>, remaining: f64) {
        if let Some(e) = value {
            if self.encounter.as_ref().map(|e| e.encounter_id) != Some(e.encounter_id) {
                self.placed = false;
                self.attempts = 0;
                self.placement_at = now;
                self.resolving = false;
                self.resolution_at = now;
                self.failures = 0;
            }
            self.deadline = now + remaining.max(0.0);
            self.encounter = Some(e);
            self.director.adopt();
        } else if self.encounter.take().is_some() {
            self.placed = false;
            self.resolving = false;
            self.director.removed(&WorldClock(now));
        }
    }
    pub fn action(&mut self, now: f64) -> Option<Action> {
        if self.pending.is_some() {
            return None;
        }
        let action = if self.resolving {
            if now < self.resolution_at {
                return None;
            }
            Action::Resolve(self.encounter.as_ref()?.encounter_id)
        } else {
            match self.director.tick(
                &WorldClock(now),
                usize::from(self.encounter.is_some()),
                self.encounter.is_some(),
            )? {
                Opportunity::Reconcile => Action::Reconcile,
                Opportunity::RequestEncounter => Action::Create,
            }
        };
        self.pending = Some(action);
        Some(action)
    }
    pub fn complete(
        &mut self,
        now: f64,
        action: Action,
        result: Result<Option<Encounter>, String>,
    ) {
        if self.pending != Some(action) {
            return;
        }
        self.pending = None;
        match result {
            Ok(value) => {
                let remaining = value.as_ref().map_or(0.0, |e| {
                    e.remaining_at(self.calendar.local_now().with_timezone(&chrono::Utc))
                });
                self.director.resolved(&WorldClock(now), value.is_some());
                self.observe(now, value, remaining);
                self.failures = 0;
            }
            Err(error) => {
                eprintln!("[LUMA SPAWN] {action:?}: {error}");
                if matches!(action, Action::Resolve(_)) {
                    self.resolution_at = now + [5.0, 10.0, 30.0][self.failures.min(2)];
                    self.failures = (self.failures + 1).min(3);
                } else {
                    self.director.failed(&WorldClock(now));
                }
            }
        }
    }
    pub fn place(&mut self, now: f64, environment: &Environment<'_>) -> Option<SpawnIntent> {
        if self.placed || self.resolving || now < self.placement_at {
            return None;
        }
        let encounter = self.encounter.as_ref()?;
        if !self.available_assets.contains(&encounter.monster.code) {
            self.resolving = true;
            self.resolution_at = now;
            return None;
        }
        let Some(candidate) = self.provider.candidate(&encounter.monster.code) else {
            self.resolving = true;
            self.resolution_at = now;
            return None;
        };
        let local_time = self.calendar.local_now().time();
        if !metadata_matches_with(encounter, &candidate, self.provider.as_ref())
            || !candidate.condition.eligible(local_time)
        {
            self.resolving = true;
            self.resolution_at = now;
            return None;
        }
        if self.deadline <= now {
            return None;
        } // existing GET-active performs authoritative expiry
        let intent = intent_for_encounter_at(
            encounter,
            Duration::from_secs_f64((self.deadline - now).min(86400.0)),
            WorldClock(now).now(),
            self.provider.as_ref(),
            environment,
            (encounter.encounter_id.as_u128() as u64).wrapping_add(self.attempts as u64),
            local_time,
        );
        if intent.is_some() {
            self.placed = true;
        } else {
            self.attempts += 1;
            if self.attempts >= 4 {
                self.resolving = true;
                self.resolution_at = now;
            } else {
                self.placement_at = now + [5.0, 10.0, 30.0][self.attempts - 1];
            }
        }
        intent
    }
}

#[cfg(test)]
pub fn test_environment(world: &mut crate::behaviors::World) {
    world.spawn_runtime.load_assets(|path| {
        std::fs::read(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../public")
                .join(path),
        )
        .ok()
    });
    let a = world.area;
    world.set_spawn_environment(
        crate::desktop::DesktopSafeArea {
            screen_frame: a,
            os_visible_frame: a,
            detected_dock_bounds: vec![],
            rejected_dock_candidates: 0,
            fallback_safe_insets: Default::default(),
            retained_safe_insets: Default::default(),
            final_luma_safe_area: a,
        },
        (a.x - 1000.0, a.y - 1000.0),
        Some(vec![]),
    );
}
#[cfg(test)]
mod tests;

#[cfg(test)]
mod batch1;

#[cfg(test)]
mod advanced;

#[cfg(test)]
mod batch2;

#[cfg(test)]
mod batch3;
