use super::*;
use std::{cell::Cell, rc::Rc};
fn context(movement: MovementProfile) -> Context {
    Context {
        position: (500., 300.),
        cursor: (-9999., -9999.),
        companion_distance: Some(600.),
        movement,
        moving: false,
    }
}
fn movement(code: &str) -> MovementProfile {
    let rows: serde_json::Value =
        serde_json::from_str(include_str!("../../../../src/entities/monster-dex.json")).unwrap();
    serde_json::from_value(
        rows.as_array()
            .unwrap()
            .iter()
            .find(|r| r["monsterCode"] == code)
            .unwrap()["movementProfile"]
            .clone(),
    )
    .unwrap()
}
#[test]
fn production_registry_is_exact_and_preserves_personality_and_physics() {
    let rows: serde_json::Value =
        serde_json::from_str(include_str!("../../../../src/entities/monster-dex.json")).unwrap();
    let active: Vec<_> = rows
        .as_array()
        .unwrap()
        .iter()
        .filter(|r| r["enabled"] == true && r["contentReady"] == true)
        .collect();
    assert_eq!(active.len(), CONFIGS.len());
    for row in active {
        let code = row["monsterCode"].as_str().unwrap();
        let c = Controller::for_species(code, Seeded::new(42), 0.).unwrap();
        assert_eq!(c.profile, profile(code).unwrap());
        let cfg = c.living.config.unwrap();
        assert!(cfg.speed <= 24. && cfg.step <= 56. && cfg.rest >= 2.);
    }
    assert!(Controller::for_species("MONSTER_005", Seeded::new(42), 0.).is_none());
}
fn trace(code: &str) -> Vec<String> {
    let mut c = Controller::for_species(code, Seeded::new(77), 0.).unwrap();
    let mut trace = vec![];
    for i in 0..1200 {
        let t = f64::from(i) * 0.1;
        if let Some(d) = c.poll_species(t, context(movement(code))) {
            trace.push(format!("{t:.1}:{:?}", d.intent));
        }
    }
    trace
}
#[test]
fn same_physics_and_personality_still_have_distinct_action_timelines() {
    let traces: std::collections::BTreeSet<_> = CONFIGS.iter().map(|c| trace(c.code)).collect();
    assert_eq!(
        traces.len(),
        15,
        "species differ in decisions/timing, not image names or displacement speed"
    );
    for (a, b) in [
        ("WISP", "LUNET"),
        ("MELLO", "BUBU"),
        ("PIP", "TIKKI"),
        ("SHADE", "NOCT"),
    ] {
        assert_ne!(trace(a), trace(b));
    }
    assert_eq!(trace("BUBU"), trace("BUBU"));
}
#[test]
fn cursor_retreat_and_lateral_observation_are_distinct_and_bounded() {
    for (code, intent) in [
        ("WISP", Intent::AvoidCursor),
        ("LUNET", Intent::SideStepCursor),
        ("NOCT", Intent::AvoidCursor),
    ] {
        let mut c = Controller::for_species(code, Seeded::new(42), 0.).unwrap();
        let mut cx = context(movement(code));
        cx.cursor = (280., 300.);
        c.poll_species(0., cx);
        let d = c.poll_species(2., cx).unwrap();
        assert_eq!(d.intent, intent);
        assert!(d.distance > 0. && d.speed > 0.);
        let n = c.decisions;
        cx.moving = true;
        for i in 0..100 {
            assert!(c.poll_species(3. + f64::from(i) / 100., cx).is_none());
        }
        assert_eq!(c.decisions, n, "no per-frame RNG while moving");
    }
}
struct Fixed(f64);
impl Random for Fixed {
    fn unit(&mut self) -> f64 {
        self.0
    }
}
#[test]
fn mello_observes_bubu_pairs_hops_and_static_only_looks() {
    let mut m = Controller::for_species("MELLO", Fixed(0.1), 0.).unwrap();
    assert_eq!(
        m.poll_species(0., context(MovementProfile::Jump))
            .unwrap()
            .intent,
        Intent::Observe
    );
    let mut b = Controller::for_species("BUBU", Fixed(0.1), 0.).unwrap();
    b.poll_species(0., context(MovementProfile::Jump));
    assert!(b.living.followup.is_some());
    let hop = b
        .poll_species(0.21, context(MovementProfile::Jump))
        .unwrap();
    assert_eq!(hop.intent, Intent::ShortBurst);
    let mut airborne = context(MovementProfile::Jump);
    airborne.moving = true;
    assert!(b.poll_species(3., airborne).is_none());
    b.poll_species(3., context(MovementProfile::Jump));
    assert!(
        b.living.followup.is_none(),
        "only one paired hop, never an infinite chain"
    );
    let mut mimi = Controller::for_species("MIMI", Fixed(0.1), 0.).unwrap();
    for i in 0..30 {
        let d = mimi
            .poll_species(f64::from(i) * 10., context(MovementProfile::Static))
            .unwrap();
        assert_eq!((d.speed, d.distance), (0., 0.));
        assert!(matches!(d.intent, Intent::Observe | Intent::Rest));
    }
}
#[test]
fn repeated_behavior_is_suppressed_without_disabling_safety_avoidance() {
    let mut c = Controller::for_species("EMBER", Fixed(0.9), 0.).unwrap();
    let mut rests = 0;
    for i in 0..100 {
        let at = f64::from(i) * 10.;
        c.poll_species(at, context(MovementProfile::Free2d));
        c.poll_species(at + 2., context(MovementProfile::Free2d));
        if matches!(c.current.intent, Intent::Rest | Intent::Observe) {
            rests += 1;
        }
    }
    assert!(
        rests > 5,
        "aggressive still pauses between repeated approaches"
    );
    let mut timid = Controller::for_species("WISP", Fixed(0.9), 0.).unwrap();
    let mut cx = context(MovementProfile::Floating);
    cx.companion_distance = Some(100.);
    for i in 0..300 {
        let t = f64::from(i) * 10.;
        timid.poll_species(t, cx);
        timid.poll_species(t + 2., cx);
    }
    assert_eq!(timid.current.intent, Intent::AvoidCompanion);
}
#[test]
fn hold_terminal_interaction_and_turn_preparation_have_explicit_lifetimes() {
    let mut c = Controller::for_species("PIP", Fixed(0.5), 0.).unwrap();
    let cx = context(MovementProfile::Ground);
    c.poll_species(0., cx);
    assert!(c.living.pending.is_some());
    c.hold(false);
    assert!(c.living.pending.is_none());
    assert!(c.cue(0.).is_none());
    c.interaction();
    assert!(c.poll_species(10., cx).is_none());
    let d = c.poll_species(12., cx).unwrap();
    assert_eq!(d.intent, Intent::Observe);
    assert_eq!(c.cue(12.).unwrap().kind, CueKind::React);
    assert!(c.cue(14.).is_none());
    c.hold(true);
    assert!(c.poll_species(1000., cx).is_none());
    let mut turn = Controller::for_species("PEBB", Fixed(0.9), 0.).unwrap();
    turn.living.last_direction = Some(-1.);
    assert_eq!(turn.poll_species(0., cx).unwrap().speed, 0.);
    assert!(turn.poll_species(1., cx).is_none());
    assert_eq!(turn.cue(0.).unwrap().kind, CueKind::Turn);
    assert!(turn.poll_species(1.81, cx).unwrap().speed > 0.);
}
#[test]
fn personality_still_changes_the_actual_species_selection_distribution() {
    fn activity(profile: Profile) -> u64 {
        let mut c = Controller::for_species("PIP", Seeded::new(99), 0.).unwrap();
        c.profile = profile;
        let mut count = 0;
        for i in 0..2000 {
            if let Some(d) = c.poll_species(f64::from(i), context(MovementProfile::Ground)) {
                if d.speed > 0. {
                    count += 1;
                }
            }
        }
        count
    }
    assert!(activity(Profile::Aggressive) > activity(Profile::Sleepy));
    assert!(activity(Profile::Playful) > activity(Profile::Passive));
}
#[test]
fn no_random_work_before_deadline_and_no_catchup_storm() {
    struct Count(Rc<Cell<u64>>);
    impl Random for Count {
        fn unit(&mut self) -> f64 {
            self.0.set(self.0.get() + 1);
            0.1
        }
    }
    let calls = Rc::new(Cell::new(0));
    let mut c = Controller::for_species("MOSSY", Count(calls.clone()), 0.).unwrap();
    let cx = context(MovementProfile::Ground);
    c.poll_species(0., cx);
    let before = calls.get();
    for i in 1..1000 {
        c.poll_species(f64::from(i) / 1000., cx);
    }
    assert_eq!(calls.get(), before);
    let decisions = c.decisions;
    c.poll_species(10000., cx);
    assert_eq!(c.decisions, decisions + 1);
}
