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
    assert_eq!(pick(Timid, Some(100.), Floating, 0.1), AvoidCompanion);
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

#[test]
fn ground_batch_behavior_decisions_keep_existing_profiles() {
    let mut sleepy = Controller::new(Profile::Sleepy, Fixed(0.9), 0.);
    assert_eq!(
        sleepy
            .poll(0., None, MovementProfile::Ground, false)
            .unwrap()
            .intent,
        Intent::Pause
    );
    let walk = sleepy
        .poll(10., None, MovementProfile::Ground, false)
        .unwrap();
    assert_eq!(walk.intent, Intent::Wander);
    assert_eq!(walk.speed, 8.);
    let pause = Controller::new(Profile::Passive, Fixed(0.1), 0.)
        .poll(0., None, MovementProfile::Ground, false)
        .unwrap();
    assert_eq!(pause.intent, Intent::Idle);
    assert_eq!(pause.speed, 0.);
    let approach = Controller::new(Profile::Curious, Fixed(0.1), 0.)
        .poll(0., Some(600.), MovementProfile::Ground, false)
        .unwrap();
    assert_eq!(approach.intent, Intent::ApproachCompanion);
    assert_eq!(approach.speed, 14.);
}

#[test]
fn bubu_jump_batch_playful_shortburst_decision_unchanged() {
    assert_eq!(
        pick(Profile::Playful, None, MovementProfile::Jump, 0.1),
        Intent::ShortBurst
    );
}

#[test]
fn nova_curious_free2d_approach_and_pause_unchanged() {
    use crate::movement::MovementProfile::Free2d;
    assert_eq!(
        pick(Profile::Curious, Some(600.), Free2d, 0.1),
        Intent::ApproachCompanion
    );
    assert_eq!(
        pick(Profile::Curious, Some(100.), Free2d, 0.1),
        Intent::Pause
    );
}

#[test]
fn living_species_are_distinct_bounded_and_provisional_neutral() {
    let rows: serde_json::Value =
        serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).unwrap();
    let mut expressions = Vec::new();
    let mut dormant = 0;
    for row in rows.as_array().unwrap() {
        let code = row["monsterCode"].as_str().unwrap();
        let e = Expression::for_species(code);
        if row["enabled"] == true {
            assert!(!expressions.contains(&e), "duplicate expression {code}");
            assert!((0.65..=1.2).contains(&e.distance));
            assert!((0.8..=1.1).contains(&e.speed));
            assert!((1.0..=1.5).contains(&e.interval));
            expressions.push(e);
        } else {
            assert_eq!(e, Expression::default());
            dormant += 1;
        }
    }
    assert_eq!(expressions.len(), 15);
    assert_eq!(dormant, 15);
    assert_eq!(Expression::for_species("UNKNOWN"), Expression::default());
}

#[test]
fn living_species_preserve_intent_constraints_and_lifecycle() {
    for code in [
        "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP", "SHADE",
        "EMBER", "LUNET", "NOVA", "NOCT",
    ] {
        for movement in [
            MovementProfile::Ground,
            MovementProfile::Jump,
            MovementProfile::Flying,
            MovementProfile::Floating,
            MovementProfile::Static,
            MovementProfile::Edge,
            MovementProfile::Free2d,
        ] {
            let p = profile(code).unwrap();
            let mut baseline = Controller::new(p, Fixed(0.9), 0.);
            let mut living = Controller::new(p, Fixed(0.9), 0.).for_species(code);
            let before = baseline.poll(0., Some(600.), movement, false).unwrap();
            let after = living.poll(0., Some(600.), movement, false).unwrap();
            assert_eq!(before.intent, after.intent);
            assert_eq!(before.direction, after.direction);
            if movement == MovementProfile::Static {
                assert_eq!(after.speed, 0.);
                assert_eq!(after.distance, 0.);
            }
            assert!(living.poll(100., None, movement, true).is_none());
            living.hold(false);
            assert!(living.poll(101., None, movement, false).is_none());
            assert!(living.poll(102., None, movement, false).is_none());
            living.hold(true);
            assert!(living.poll(999., None, movement, false).is_none());
        }
    }
}

#[test]
fn living_seeded_replay_and_bounded_decision_budget() {
    for code in ["PIP", "BUBU", "LUNET", "NOCT", "NOVA"] {
        let mut a = Controller::new(profile(code).unwrap(), Seeded::new(42), 0.).for_species(code);
        let mut b = Controller::new(profile(code).unwrap(), Seeded::new(42), 0.).for_species(code);
        for i in 0..18000 {
            let now = f64::from(i) / 30.;
            assert_eq!(
                a.poll(now, Some(600.), MovementProfile::Ground, false),
                b.poll(now, Some(600.), MovementProfile::Ground, false)
            );
        }
        assert!(a.decisions <= 300); // At most one per two seconds, independent of render FPS.
    }
}

#[test]
fn living_ground_speed_still_enters_existing_move_animation() {
    for code in ["PIP", "MOSSY", "PEBB", "TIKKI"] {
        let mut c = Controller::new(
            profile(code).unwrap(),
            Fixed(if code == "PIP" { 0.7 } else { 0.9 }),
            0.,
        )
        .for_species(code);
        c.poll(0., None, MovementProfile::Ground, false);
        let d = c.poll(10., None, MovementProfile::Ground, false).unwrap();
        assert!(
            d.speed >= 8.,
            "{code} must reach existing MOVE entry threshold"
        );
    }
}

#[test]
fn caplet_expression_is_deterministic_and_does_not_change_sleepy_policy() {
    let mut caplet = Controller::new(Profile::Sleepy, Seeded::new(42), 0.).for_species("CAPLET");
    let mut legacy = Controller::new(Profile::Sleepy, Seeded::new(42), 0.);
    for i in 0..1000 {
        let now = i as f64 * 0.05;
        assert_eq!(
            caplet.poll(now, None, MovementProfile::Ground, false),
            legacy.poll(now, None, MovementProfile::Ground, false)
        );
        assert_eq!(caplet.next_decision_at, legacy.next_decision_at);
        assert!(!legacy.sleep_pose());
        assert_eq!(
            caplet.sleep_pose(),
            caplet.decisions > 0 && caplet.current.intent == Intent::Pause
        );
    }
    let count = caplet.decisions;
    assert!(caplet
        .poll(100., None, MovementProfile::Ground, true)
        .is_none());
    assert_eq!(caplet.decisions, count);
}
