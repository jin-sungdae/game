//! Bounded retries driven by the existing World tick. Only accepted placement enqueues.
use crate::backend::discovery::Job;
#[derive(Default)]
pub struct Sync {
    pending: Vec<Pending>,
}
struct Pending {
    job: Job,
    attempts: usize,
    due: f64,
    in_flight: bool,
}
impl Sync {
    pub fn placed(&mut self, id: uuid::Uuid, code: &str, now: f64) {
        if self.pending.len() >= 32 || self.pending.iter().any(|p| p.job.encounter_id == id) {
            return;
        }
        self.pending.push(Pending {
            job: Job {
                encounter_id: id,
                code: code.into(),
            },
            attempts: 0,
            due: now,
            in_flight: false,
        });
    }
    pub fn next(&mut self, now: f64) -> Option<Job> {
        if self.pending.iter().any(|p| p.in_flight) {
            return None;
        }
        let p = self
            .pending
            .iter_mut()
            .find(|p| p.attempts < 4 && now >= p.due)?;
        p.in_flight = true;
        Some(p.job.clone())
    }
    pub fn complete(&mut self, job: &Job, now: f64, success: bool, sent: bool) {
        if success {
            self.pending.retain(|p| p.job != *job);
            return;
        }
        if let Some(p) = self.pending.iter_mut().find(|p| p.job == *job) {
            p.in_flight = false;
            if sent {
                p.attempts += 1;
            }
            p.due = now + [5.0, 15.0, 30.0][p.attempts.saturating_sub(1).min(2)];
        }
    }
    pub fn refresh(&mut self) {
        for p in &mut self.pending {
            if !p.in_flight {
                p.attempts = 0;
                p.due = 0.0;
            }
        }
    }
    #[cfg(test)]
    pub fn contains(&self, code: &str) -> bool {
        self.pending.iter().any(|p| p.job.code == code)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounded_deduplicated_retry_and_refresh() {
        let mut s = Sync::default();
        let id = uuid::Uuid::from_u128(1);
        s.placed(id, "PIP", 0.0);
        s.placed(id, "PIP", 0.0);
        for now in [0.0, 5.0, 20.0, 50.0] {
            let job = s.next(now).unwrap();
            assert!(s.next(now).is_none());
            s.complete(&job, now, false, true);
            assert!(s.next(now).is_none());
        }
        assert!(s.next(999.0).is_none());
        s.refresh();
        let job = s.next(999.0).unwrap();
        s.complete(&job, 999.0, true, true);
        assert!(!s.contains("PIP"));
        for i in 1..=40 {
            s.placed(uuid::Uuid::from_u128(i), "PIP", 0.0);
        }
        assert_eq!(s.pending.len(), 32);
    }
}
