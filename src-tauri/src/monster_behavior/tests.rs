use super::*;
struct Fixed(f64);
impl Random for Fixed {
    fn unit(&mut self) -> f64 {
        self.0
    }
}
fn pick(p: Profile, d: Option<f64>, m: MovementProfile, r: f64) -> Intent {
    Controller::new(p, Fixed(r), 0.)
        .poll(0., d, m, false)
        .unwrap()
        .intent
}
#[test]
fn profiles_and_companion_fallback() {
    use {Intent::*, MovementProfile::*, Profile::*};
    assert_eq!(pick(Curious, Some(600.), Ground, 0.1), ApproachCompanion);
    assert_eq!(pick(Curious, Some(100.), Ground, 0.1), Pause);
    assert_eq!(pick(Timid, Some(100.), Edge, 0.1), AvoidCompanion);
    assert_eq!(pick(Timid, Some(600.), Floating, 0.1), Pause);
    assert_eq!(pick(Aggressive, Some(600.), Free2d, 0.9), ApproachCompanion);
    assert_eq!(pick(Sleepy, Some(600.), Ground, 0.99), Pause);
    assert_eq!(pick(Trickster, Some(600.), Static, 0.99), Pause);
    assert_eq!(pick(Trickster, Some(600.), Edge, 0.99), EdgeShift);
    assert_eq!(pick(Passive, None, Ground, 0.1), Idle);
    for p in [
        Curious, Timid, Playful, Aggressive, Sleepy, Trickster, Passive,
    ] {
        assert!(!matches!(
            pick(p, None, Ground, 0.3),
            ApproachCompanion | AvoidCompanion
        ));
    }
}
#[test]
fn hysteresis_stop_resume_cooldown_and_terminal() {
    let mut c = Controller::new(Profile::Curious, Fixed(0.1), 0.);
    assert_eq!(
        c.poll(0., Some(500.), MovementProfile::Ground, false)
            .unwrap()
            .intent,
        Intent::ApproachCompanion
    );
    assert_eq!(
        c.poll(4., Some(240.), MovementProfile::Ground, false)
            .unwrap()
            .intent,
        Intent::ApproachCompanion
    );
    assert!(c.stop_approach(Some(170.)));
    assert_eq!(
        c.poll(8., Some(240.), MovementProfile::Ground, false)
            .unwrap()
            .intent,
        Intent::Wander
    );
    c.hold(false);
    let n = c.decisions;
    assert!(c
        .poll(9., Some(500.), MovementProfile::Ground, false)
        .is_none());
    assert!(c
        .poll(10., Some(500.), MovementProfile::Ground, false)
        .is_none());
    assert_eq!(c.decisions, n);
    assert!(c
        .poll(11., Some(500.), MovementProfile::Ground, false)
        .is_some());
    c.hold(true);
    assert!(c
        .poll(100., Some(500.), MovementProfile::Ground, false)
        .is_none());
}
#[test]
fn seeded_replay_bias_and_fifteen_controller_tick_budget() {
    let mut traces = Vec::new();
    for _ in 0..2 {
        let mut c = Controller::new(Profile::Playful, Seeded::new(99), 0.);
        let mut trace = Vec::new();
        for i in 0..1800 {
            if let Some(d) = c.poll(
                f64::from(i) / 30.,
                Some(600.),
                MovementProfile::Ground,
                false,
            ) {
                trace.push(d);
            }
        }
        assert!((15..=30).contains(&trace.len()));
        traces.push(trace);
    }
    assert_eq!(traces[0], traces[1]);
    assert!(traces[0].iter().any(|d| d.intent == Intent::ShortBurst));
    let mut sleepy = Controller::new(Profile::Sleepy, Seeded::new(88), 0.);
    let mut paused = 0;
    for i in 0..1000 {
        if sleepy
            .poll(f64::from(i) * 4., None, MovementProfile::Ground, false)
            .unwrap()
            .intent
            == Intent::Pause
        {
            paused += 1;
        }
    }
    assert!(paused > 700);
    for seed in 0..15 {
        let mut c = Controller::new(Profile::Passive, Seeded::new(seed), 0.);
        for i in 0..1800 {
            c.poll(f64::from(i) / 30., None, MovementProfile::Ground, false);
        }
        assert!((15..=30).contains(&c.decisions));
        let n = c.decisions;
        c.poll(1000., None, MovementProfile::Ground, false);
        assert_eq!(c.decisions, n + 1);
    }
}
#[test]
fn content_profiles_are_independent_of_physics() {
    for (code, expected) in [
        ("MELLO", Profile::Curious),
        ("WISP", Profile::Timid),
        ("PIP", Profile::Playful),
        ("EMBER", Profile::Aggressive),
        ("MOSSY", Profile::Sleepy),
        ("SHADE", Profile::Trickster),
        ("PEBB", Profile::Passive),
        ("MIMI", Profile::Trickster),
    ] {
        assert_eq!(profile(code), Some(expected));
    }
    assert!(profile("UNKNOWN").is_none());
}
