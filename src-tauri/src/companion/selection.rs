use super::{config::*, transitions::Behavior};

pub fn weights(
    p: CompanionPersonality,
    tuning: WeightTuning,
    sleep_ready: bool,
    nearby: bool,
) -> [u32; 4] {
    let low_energy = 100 - p.energy.value();
    [
        tuning.base[0]
            + p.energy.value() * tuning.walking_energy / 100
            + p.mischief.value() * tuning.walking_mischief / 100,
        tuning.base[1]
            + low_energy * tuning.sitting_low_energy / 100
            + (100 - p.bravery.value()) * tuning.sitting_low_bravery / 100,
        tuning.base[2]
            + p.curiosity.value() * tuning.looking_curiosity / 100
            + p.affection.value() * tuning.looking_affection / 100
            + if nearby {
                tuning.nearby_looking_bonus
            } else {
                0
            },
        if sleep_ready {
            tuning.base[3] + low_energy * tuning.sleeping_low_energy / 100
        } else {
            0
        },
    ]
}
/// Cumulative weighted selection, deterministic for a supplied [0, 1) sample.
pub fn choose(weights: [u32; 4], unit: f64) -> Option<Behavior> {
    let total: u32 = weights.iter().sum();
    let mut point = unit * f64::from(total);
    for (weight, behavior) in weights.into_iter().zip([
        Behavior::Walking,
        Behavior::Sitting,
        Behavior::Looking,
        Behavior::Sleeping,
    ]) {
        if point < f64::from(weight) {
            return Some(behavior);
        }
        point -= f64::from(weight);
    }
    None // zero weights: safely remain idle and reschedule.
}

/// Discourage the last autonomous choice without prohibiting the only eligible behavior.
/// Called at decision boundaries, never during an active action or on every animation frame.
pub fn suppress_recent(mut weights: [u32; 4], recent: Option<Behavior>) -> [u32; 4] {
    let index = match recent {
        Some(Behavior::Walking) => 0,
        Some(Behavior::Sitting) => 1,
        Some(Behavior::Looking) => 2,
        Some(Behavior::Sleeping) => 3,
        None => return weights,
    };
    if weights[index] > 0 {
        weights[index] = (weights[index] / 4).max(1);
    }
    weights
}
