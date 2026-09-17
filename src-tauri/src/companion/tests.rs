use super::*;
use config::{TraitScore, MOA_BEHAVIOR, MOA_PERSONALITY};
use transitions::{Behavior, Event};

const FAR: (f64, f64) = (-10000.0, 10000.0);
fn area() -> Area {
    Area {
        x: -800.0,
        y: 60.0,
        w: 800.0,
        h: 600.0,
    }
}
fn controller(config: BehaviorConfig) -> CompanionController {
    CompanionController::new(area(), 0.0, 42, MOA_PERSONALITY, config)
}
fn forced(behavior: Behavior) -> BehaviorConfig {
    let mut config = MOA_BEHAVIOR;
    config.idle = config::DurationRange { min: 1.0, max: 1.0 };
    config.sleep_after_quiet = 0.0;
    config.weights = config::WeightTuning {
        base: match behavior {
            Behavior::Walking => [1, 0, 0, 0],
            Behavior::Sitting => [0, 1, 0, 0],
            Behavior::Looking => [0, 0, 1, 0],
            Behavior::Sleeping => [0, 0, 0, 1],
        },
        walking_energy: 0,
        walking_mischief: 0,
        sitting_low_energy: 0,
        sitting_low_bravery: 0,
        looking_curiosity: 0,
        looking_affection: 0,
        sleeping_low_energy: 0,
        nearby_looking_bonus: 0,
    };
    config
}
#[test]
fn idle_to_each_autonomous_behavior() {
    for behavior in [
        Behavior::Walking,
        Behavior::Sitting,
        Behavior::Looking,
        Behavior::Sleeping,
    ] {
        let mut c = controller(forced(behavior));
        c.tick(1.0, 0.03, area(), FAR, false);
        assert_eq!(c.entity().state, behavior.state());
        c.tick(1.0 + c.duration, 0.03, area(), FAR, false);
        assert_eq!(c.entity().state, CompanionState::Idle);
    }
}
#[test]
fn sleep_requires_long_quiet_and_does_not_move_or_follow_cursor() {
    let mut config = forced(Behavior::Sleeping);
    config.sleep_after_quiet = 120.0;
    let mut c = controller(config);
    c.tick(119.0, 0.03, area(), FAR, false);
    assert_eq!(c.entity().state, CompanionState::Idle);
    c.tick(120.0, 0.03, area(), FAR, false);
    assert_eq!(c.entity().state, CompanionState::Sleeping);
    let position = (c.entity().x, c.entity().y);
    c.tick(121.0, 0.1, area(), position, false);
    assert_eq!(c.entity().state, CompanionState::Sleeping);
    assert_eq!((c.entity().x, c.entity().y), position);
}
#[test]
fn drag_suppresses_automatic_events_and_release_is_idle() {
    let mut c = controller(forced(Behavior::Walking));
    let start = (c.entity().x, c.entity().y);
    c.begin_drag(0.0, area(), start);
    c.react(200.0, area(), Some(0.0));
    c.tick(200.0, 0.03, area(), (start.0 + 50.0, start.1), true);
    assert_eq!(c.entity().state, CompanionState::Dragging);
    c.tick(201.0, 0.03, area(), (start.0 + 50.0, start.1), false);
    assert_eq!(c.entity().state, CompanionState::Idle);
    assert_eq!(c.entered_at, 201.0);
}
#[test]
fn drag_out_and_back_is_not_a_click() {
    let mut c = controller(MOA_BEHAVIOR);
    let start = (c.entity().x, c.entity().y);
    c.begin_drag(0.0, area(), start);
    c.tick(0.1, 0.03, area(), (start.0 + 30.0, start.1), true);
    c.tick(0.2, 0.03, area(), start, false);
    assert_eq!(c.entity().state, CompanionState::Idle);
}
#[test]
fn reaction_interrupts_resting_states_and_returns_idle() {
    for behavior in [
        Behavior::Walking,
        Behavior::Sitting,
        Behavior::Looking,
        Behavior::Sleeping,
    ] {
        let mut c = controller(forced(behavior));
        c.tick(1.0, 0.03, area(), FAR, false);
        c.react(2.0, area(), Some(0.0));
        assert_eq!(c.entity().state, CompanionState::Reacting);
        assert_eq!(c.entity().facing, 1);
        let position = (c.entity().x, c.entity().y);
        c.tick(2.5, 0.1, area(), FAR, false);
        assert_eq!((c.entity().x, c.entity().y), position);
        c.tick(3.3, 0.03, area(), FAR, false);
        assert_eq!(c.entity().state, CompanionState::Idle);
    }
}
#[test]
fn personality_weights_and_sleep_eligibility() {
    let config = MOA_BEHAVIOR.weights;
    let mut low = MOA_PERSONALITY;
    low.energy = TraitScore::new(0);
    low.curiosity = TraitScore::new(0);
    let mut high = low;
    high.energy = TraitScore::new(100);
    high.curiosity = TraitScore::new(100);
    let a = selection::weights(low, config, true, false);
    let b = selection::weights(high, config, true, false);
    assert!(b[0] > a[0]);
    assert!(a[1] > b[1]);
    assert!(b[2] > a[2]);
    assert!(a[3] > b[3]);
    assert_eq!(selection::weights(low, config, false, false)[3], 0);
    assert!(selection::weights(low, config, true, true)[2] > a[2]);
    assert_eq!(
        [
            MOA_PERSONALITY.curiosity.value(),
            MOA_PERSONALITY.bravery.value(),
            MOA_PERSONALITY.affection.value(),
            MOA_PERSONALITY.energy.value(),
            MOA_PERSONALITY.mischief.value()
        ],
        [80, 40, 75, 50, 30]
    );
}
#[test]
#[should_panic(expected = "personality must be in 0..=100")]
fn personality_rejects_out_of_range_master_values() {
    TraitScore::new(101);
}
#[test]
fn cumulative_choice_boundaries_and_zero_weights() {
    assert_eq!(
        selection::choose([1, 2, 3, 4], 0.0),
        Some(Behavior::Walking)
    );
    assert_eq!(
        selection::choose([1, 2, 3, 4], 0.1),
        Some(Behavior::Sitting)
    );
    assert_eq!(
        selection::choose([1, 2, 3, 4], 0.3),
        Some(Behavior::Looking)
    );
    assert_eq!(
        selection::choose([1, 2, 3, 4], 0.6),
        Some(Behavior::Sleeping)
    );
    assert_eq!(selection::choose([0; 4], 0.5), None);
}
#[test]
fn cursor_nearby_looks_and_tracks_direction_with_cooldown() {
    let mut c = controller(MOA_BEHAVIOR);
    let (x, y) = (c.entity().x, c.entity().y);
    c.tick(
        16.0,
        0.03,
        area(),
        (x + MOA_SIZE.width / 2.0, y + MOA_SIZE.height / 2.0),
        false,
    );
    assert_eq!(c.entity().state, CompanionState::Looking);
    assert_eq!(c.entity().facing, 1);
    c.tick(
        16.1,
        0.03,
        area(),
        (x - MOA_SIZE.width / 2.0, y + MOA_SIZE.height / 2.0),
        false,
    );
    assert_eq!(c.entity().facing, -1);
    c.tick(23.0, 0.03, area(), (x, y), false);
    assert_eq!(c.entity().state, CompanionState::Idle);
    c.tick(23.1, 0.03, area(), (x, y), false);
    assert_eq!(c.entity().state, CompanionState::Idle);
}
#[test]
fn walking_and_drag_clamp_to_negative_and_changed_work_area() {
    let mut c = controller(forced(Behavior::Walking));
    c.tick(1.0, 0.03, area(), FAR, false);
    assert!(
        c.target >= area().x
            && c.target
                <= area().x + area().w - MOA_SIZE.width / 2.0 - crate::geometry::LAYOUT.margin
    );
    let x = c.entity().x;
    c.tick(1.1, 1000.0, area(), FAR, false);
    assert!((c.entity().x - x).abs() <= MOA_BEHAVIOR.walk_speed * 0.1 + f64::EPSILON);
    let small = Area {
        x: 100.0,
        y: 50.0,
        w: 50.0,
        h: 50.0,
    };
    c.tick(1.2, 0.03, small, FAR, false);
    assert_eq!((c.entity().x, c.entity().y), (156.0, 58.0));
    c.begin_drag(2.0, area(), (156.0, 58.0));
    c.tick(3.0, 0.03, area(), (-9000.0, 9000.0), true);
    assert_eq!((c.entity().x, c.entity().y), (-744.0, 548.0));
}
#[test]
fn seeded_replay_and_idle_interval_are_deterministic() {
    let (mut a, mut b) = (controller(MOA_BEHAVIOR), controller(MOA_BEHAVIOR));
    assert!((30.0..=60.0).contains(&a.duration));
    for i in 0..10000 {
        let now = f64::from(i) * 0.1;
        a.tick(now, 0.1, area(), FAR, false);
        b.tick(now, 0.1, area(), FAR, false);
        assert_eq!(
            (
                a.entity().state,
                a.entity().x,
                a.entity().y,
                a.entity().facing
            ),
            (
                b.entity().state,
                b.entity().x,
                b.entity().y,
                b.entity().facing
            )
        );
    }
}
#[test]
fn movement_target_clamps_both_edges_with_center_anchor() {
    for target in [-10000.0, 10000.0] {
        let mut c = controller(forced(Behavior::Walking));
        c.tick(1.0, 0.03, area(), FAR, false);
        c.target = target;
        c.tick(1.1, 0.03, area(), FAR, false);
        let bounds = c.entity.size.bounds(c.target, c.entity.y);
        assert!(bounds.x >= area().x + crate::geometry::LAYOUT.margin);
        assert!(bounds.x + bounds.w <= area().x + area().w - crate::geometry::LAYOUT.margin);
        assert_eq!(c.entity.y, area().ground_y());
    }
}
#[test]
fn transition_policy_rejects_autonomous_drag_and_non_idle_decisions() {
    for event in [
        Event::Decision(Behavior::Sleeping),
        Event::Finished,
        Event::CursorNearby,
        Event::Reaction,
    ] {
        assert_eq!(transitions::next(CompanionState::Dragging, event), None);
    }
    assert_eq!(
        transitions::next(CompanionState::Sleeping, Event::Decision(Behavior::Walking)),
        None
    );
    assert_eq!(
        transitions::next(CompanionState::Sleeping, Event::CursorNearby),
        None
    );
}
