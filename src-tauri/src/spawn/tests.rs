use super::*;
use crate::{desktop::SafeAreaTracker, geometry::Area};
use std::cell::Cell;
struct FakeClock(Cell<Duration>);
impl Clock for FakeClock {
    fn now(&self) -> Duration {
        self.0.get()
    }
}
impl FakeClock {
    fn at(&self, t: Duration) {
        self.0.set(t);
    }
}
fn clock() -> FakeClock {
    FakeClock(Cell::new(Duration::ZERO))
}
fn director(seed: u64) -> Director {
    Director::new(true, seed, Config::default()).unwrap()
}
fn due(d: &mut Director, c: &FakeClock) -> Option<Opportunity> {
    c.at(d.next_spawn_at());
    if d.state() == SpawnState::Cooldown {
        assert_eq!(d.tick(c, 0, false), None);
        assert_eq!(d.state(), SpawnState::Waiting);
    }
    d.tick(c, 0, false)
}
#[test]
fn lifecycle_restart_and_authority() {
    let c = clock();
    let mut d = director(42);
    assert_eq!(d.state(), SpawnState::Waiting);
    assert_eq!(d.tick(&c, 0, false), Some(Opportunity::Reconcile));
    assert_eq!(d.state(), SpawnState::Requesting);
    d.resolved(&c, true);
    assert_eq!(d.state(), SpawnState::Active);
    c.at(Duration::from_secs(10000));
    assert_eq!(d.tick(&c, 0, false), None); // local disappearance cannot erase authority
    d.removed(&c);
    assert_eq!(d.state(), SpawnState::Cooldown);
    assert_eq!(due(&mut d, &c), Some(Opportunity::Reconcile));
    d.resolved(&c, false);
    assert_eq!(due(&mut d, &c), Some(Opportunity::RequestEncounter));
    d.resolved(&c, true);
    assert_eq!(d.state(), SpawnState::Active);
    let mut restarted = director(42);
    assert_eq!(restarted.tick(&c, 0, false), Some(Opportunity::Reconcile));
    restarted.resolved(&c, true);
    assert_eq!(restarted.tick(&c, 0, false), None);
}
#[test]
fn cooldown_seeded_and_no_per_tick_work() {
    let c = clock();
    let mut a = director(1);
    let mut b = director(1);
    let mut other = director(2);
    for d in [&mut a, &mut b, &mut other] {
        d.tick(&c, 0, false);
        d.resolved(&c, false);
    }
    assert_eq!(a.next_spawn_at(), b.next_spawn_at());
    assert_ne!(a.next_spawn_at(), other.next_spawn_at());
    assert!((Duration::from_secs(120)..=Duration::from_secs(300)).contains(&a.next_spawn_at()));
    let rng = a.random.0;
    for _ in 0..10000 {
        assert_eq!(a.tick(&c, 0, false), None);
    }
    assert_eq!(a.random.0, rng);
    assert_eq!(due(&mut a, &c), Some(Opportunity::RequestEncounter));
    for _ in 0..10000 {
        assert_eq!(a.tick(&c, 0, false), None);
    }
}
#[test]
fn budgets_active_encounter_and_disabled_runtime() {
    let c = clock();
    for (occupied, active) in [(1, false), (0, true), (3, false)] {
        let mut d = director(1);
        assert_eq!(d.tick(&c, occupied, active), None);
        assert_eq!(d.state(), SpawnState::Cooldown);
    }
    for max in [2, 3] {
        let mut d = Director::new(
            true,
            1,
            Config {
                max_wild_monsters: max,
                ..Config::default()
            },
        )
        .unwrap();
        assert_eq!(d.tick(&c, max, false), None);
        assert_eq!(due(&mut d, &c), Some(Opportunity::Reconcile));
    }
    let mut d = Director::disabled(1);
    for _ in 0..10000 {
        assert_eq!(d.tick(&c, 0, false), None);
    }
    assert_eq!(d.random.0, 1);
    assert!(Director::new(
        true,
        1,
        Config {
            max_wild_monsters: 0,
            ..Config::default()
        }
    )
    .is_err());
}
#[test]
fn backend_failure_bounded_backoff_recovery_and_lost_post() {
    let c = clock();
    let mut d = director(1);
    for delay in [5, 10, 30, 30, 30] {
        assert_eq!(due(&mut d, &c), Some(Opportunity::Reconcile));
        let now = c.now();
        d.failed(&c);
        assert_eq!(d.next_spawn_at() - now, Duration::from_secs(delay));
        for _ in 0..1000 {
            assert_eq!(d.tick(&c, 0, false), None);
        }
    }
    assert_eq!(due(&mut d, &c), Some(Opportunity::Reconcile));
    d.resolved(&c, false);
    assert_eq!(due(&mut d, &c), Some(Opportunity::RequestEncounter));
    d.failed(&c);
    assert_eq!(d.next_spawn_at() - c.now(), Duration::from_secs(5));
    assert_eq!(due(&mut d, &c), Some(Opportunity::Reconcile));
    d.resolved(&c, true); // committed POST with lost response recovered
    assert_eq!(d.state(), SpawnState::Active);
}
fn safe(x: f64, y: f64) -> DesktopSafeArea {
    let screen = Area {
        x,
        y,
        w: 1800.0,
        h: 1100.0,
    };
    SafeAreaTracker::default().update(
        1,
        screen,
        Area {
            h: 1072.0,
            ..screen
        },
        &[Area {
            x: x + 200.0,
            y,
            w: 1400.0,
            h: 240.0,
        }],
    )
}
fn fixture(zone: SpawnZone, size: Size) -> Candidate {
    Candidate {
        zone,
        size,
        ..ContentProvider.candidate("PIP").unwrap()
    }
}
#[test]
fn all_zones_negative_monitors_sizes_dock_menu_and_determinism() {
    for (x, y) in [(0.0, 0.0), (-1900.25, -1200.5)] {
        let safe = safe(x, y);
        let a = safe.final_luma_safe_area;
        let e = Environment {
            safe_area: &safe,
            cursor: Some((10000.0, 10000.0)),
            windows: Some(&[]),
        };
        for size in [
            crate::geometry::PIP_SIZE,
            Size {
                width: 140.0,
                height: 240.0,
            },
        ] {
            for zone in [
                SpawnZone::Bottom,
                SpawnZone::Top,
                SpawnZone::LeftEdge,
                SpawnZone::RightEdge,
                SpawnZone::FreeArea,
                SpawnZone::NearDock,
                SpawnZone::LowerCorner,
            ] {
                let c = fixture(zone, size);
                let p = placement(&c, &e, 42).unwrap();
                assert_eq!(Some(p), placement(&c, &e, 42));
                let b = size.bounds(p.0, p.1);
                assert!(b.x >= a.x + 8.0 && b.x + b.w <= a.x + a.w - 8.0);
                assert!(b.y >= a.y + 8.0 && b.y + b.h <= a.y + a.h - 8.0);
                assert!(b.y >= y + 240.0 && b.y + b.h <= y + 1072.0);
                match zone {
                    SpawnZone::Bottom | SpawnZone::NearDock | SpawnZone::LowerCorner => {
                        assert_eq!(p.1, a.ground_y().ceil())
                    }
                    SpawnZone::Top => assert_eq!(b.y, (a.y + a.h - 8.0 - size.height).floor()),
                    SpawnZone::LeftEdge => assert_eq!(b.x, (a.x + 8.0).ceil()),
                    SpawnZone::RightEdge => assert_eq!(b.x, (a.x + a.w - 8.0 - size.width).floor()),
                    _ => {}
                }
            }
        }
    }
}
#[test]
fn cursor_windows_unknown_and_impossible_placement() {
    let safe = safe(0.0, 0.0);
    let c = fixture(SpawnZone::Bottom, crate::geometry::PIP_SIZE);
    let mut e = Environment {
        safe_area: &safe,
        cursor: Some((10000.0, 10000.0)),
        windows: Some(&[]),
    };
    let p = placement(&c, &e, 42).unwrap();
    e.cursor = Some(p);
    let alternate = placement(&c, &e, 42).unwrap();
    assert!(crate::movement::unobstructed(
        alternate,
        alternate,
        0.0,
        c.size,
        p,
        Some(&[]),
        100.0
    ));
    e.cursor = Some((10000.0, 10000.0));
    let windows = [c.size.bounds(p.0, p.1)];
    e.windows = Some(&windows);
    let alternate = placement(&c, &e, 42).unwrap();
    assert!(crate::movement::unobstructed(
        alternate,
        alternate,
        0.0,
        c.size,
        e.cursor.unwrap(),
        Some(&windows),
        100.0
    ));
    let blocked = [safe.final_luma_safe_area];
    e.windows = Some(&blocked);
    assert!(placement(&c, &e, 42).is_none());
    e.windows = None;
    assert!(placement(&c, &e, 42).is_none());
    e.windows = Some(&[]);
    e.cursor = None;
    assert!(placement(&c, &e, 42).is_none());
    e.cursor = Some((10000.0, 10000.0));
    assert!(placement(
        &fixture(
            SpawnZone::FreeArea,
            Size {
                width: 10000.0,
                height: 10000.0
            }
        ),
        &e,
        42
    )
    .is_none());
}
struct FixtureProvider(Candidate);
impl SpawnCandidateProvider for FixtureProvider {
    fn candidate(&self, _: &str) -> Option<Candidate> {
        Some(self.0.clone())
    }
}
#[test]
fn provider_authority_lifetime_and_inactive_conditions() {
    let safe = safe(0.0, 0.0);
    let env = Environment {
        safe_area: &safe,
        cursor: Some((10000.0, 10000.0)),
        windows: Some(&[]),
    };
    let encounter:crate::backend::Encounter=serde_json::from_value(serde_json::json!({
        "encounterId":"00000000-0000-0000-0000-000000000001",
        "monster":{"code":"PIP","name":"PIP","level":1,"rarity":"COMMON","movementProfile":"GROUND"},
        "spawnedAt":"2026-09-22T00:00:00Z","expiresAt":"2026-09-22T00:01:00Z"
    })).unwrap();
    let remaining = Duration::from_secs(10);
    let intent = intent_for_encounter(
        &encounter,
        remaining,
        Duration::from_secs(3),
        &ContentProvider,
        &env,
        42,
    )
    .unwrap();
    assert_eq!(intent.lifetime, remaining);
    assert_eq!(intent.requested_at, Duration::from_secs(3));
    assert!(ContentProvider.candidate("TEST_ONLY").is_none());
    for condition in [
        SpawnCondition::Day,
        SpawnCondition::Night,
        SpawnCondition::FocusSession,
        SpawnCondition::SpecialEvent,
    ] {
        let provider = FixtureProvider(Candidate {
            condition,
            ..fixture(SpawnZone::Top, crate::geometry::PIP_SIZE)
        });
        assert!(
            intent_for_encounter(&encounter, remaining, Duration::ZERO, &provider, &env, 42)
                .is_none()
        );
    }
    let provider = FixtureProvider(Candidate {
        monster_code: "TEST_ONLY".into(),
        ..fixture(SpawnZone::Top, crate::geometry::PIP_SIZE)
    });
    assert!(
        intent_for_encounter(&encounter, remaining, Duration::ZERO, &provider, &env, 42).is_none()
    );
    assert!(intent_for_encounter(
        &encounter,
        Duration::ZERO,
        Duration::ZERO,
        &ContentProvider,
        &env,
        42
    )
    .is_none());
}
