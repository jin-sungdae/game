//! Local master data; no persistence, runtime trait changes or balance service.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TraitScore(u8);
impl TraitScore {
    pub const fn new(value: u8) -> Self {
        assert!(value <= 100, "personality must be in 0..=100");
        Self(value)
    }
    pub fn value(self) -> u32 {
        u32::from(self.0)
    }
}
#[derive(Clone, Copy, Debug)]
pub struct CompanionPersonality {
    pub curiosity: TraitScore,
    pub bravery: TraitScore,
    pub affection: TraitScore,
    pub energy: TraitScore,
    pub mischief: TraitScore,
}
pub const MOA_PERSONALITY: CompanionPersonality = CompanionPersonality {
    curiosity: TraitScore::new(80),
    bravery: TraitScore::new(40),
    affection: TraitScore::new(75),
    energy: TraitScore::new(50),
    mischief: TraitScore::new(30),
};
#[derive(Clone, Copy, Debug)]
pub struct DurationRange {
    pub min: f64,
    pub max: f64,
}
impl DurationRange {
    pub fn sample(self, unit: f64) -> f64 {
        self.min + (self.max - self.min) * unit
    }
}
#[derive(Clone, Copy, Debug)]
pub struct WeightTuning {
    // Order: walking, sitting, looking, sleeping. Coefficients are contribution at score 100.
    pub base: [u32; 4],
    pub walking_energy: u32,
    pub walking_mischief: u32,
    pub sitting_low_energy: u32,
    pub sitting_low_bravery: u32,
    pub looking_curiosity: u32,
    pub looking_affection: u32,
    pub sleeping_low_energy: u32,
    pub nearby_looking_bonus: u32,
}
#[derive(Clone, Copy, Debug)]
pub struct BehaviorConfig {
    pub idle: DurationRange,
    pub sitting: DurationRange,
    pub looking: DurationRange,
    pub sleeping: DurationRange,
    pub sleep_after_quiet: f64,
    pub reaction_duration: f64,
    pub walk_duration: f64,
    pub walk_preparation: f64,
    pub walk_recovery: f64,
    pub walk_radius: f64,
    pub walk_speed: f64,
    pub cursor_radius: f64,
    pub cursor_cooldown: f64,
    pub click_distance: f64,
    pub weights: WeightTuning,
}
pub const MOA_BEHAVIOR: BehaviorConfig = BehaviorConfig {
    idle: DurationRange {
        min: 30.0,
        max: 60.0,
    },
    sitting: DurationRange {
        min: 8.0,
        max: 16.0,
    },
    looking: DurationRange { min: 3.0, max: 6.0 },
    sleeping: DurationRange {
        min: 20.0,
        max: 40.0,
    },
    sleep_after_quiet: 120.0,
    reaction_duration: 1.2,
    walk_duration: 5.0,
    walk_preparation: 0.0,
    walk_recovery: 0.0,
    walk_radius: 180.0,
    walk_speed: 40.0,
    cursor_radius: 160.0,
    cursor_cooldown: 15.0,
    click_distance: 5.0,
    weights: WeightTuning {
        base: [10, 10, 10, 5],
        walking_energy: 50,
        walking_mischief: 10,
        sitting_low_energy: 35,
        sitting_low_bravery: 5,
        looking_curiosity: 50,
        looking_affection: 10,
        sleeping_low_energy: 50,
        nearby_looking_bonus: 40,
    },
};

/// All 15 forms have an identity contract; unavailable forms are not runtime-enabled.
/// Battle/skill/evolution remain authoritative domain events, never autonomous inventions.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LivingCoverage {
    Animated,
    BaseOnly,
    AwaitingAssets,
}
pub fn living_coverage(species: &str, stage: u32) -> Option<LivingCoverage> {
    use LivingCoverage::*;
    match (species, stage) {
        ("MOA", 1) => Some(Animated),
        ("MOA", 2..=3) => Some(BaseOnly),
        ("MOA", 4..=5) | ("RUU" | "NOX", 1..=5) => Some(AwaitingAssets),
        _ => None,
    }
}
/// Decision policy is independent of sprite availability. Runtime activation still uses
/// living_config, so a policy never substitutes another species' production artwork.
pub fn decision_config(species: &str) -> Option<(CompanionPersonality, BehaviorConfig)> {
    let mut config = MOA_BEHAVIOR;
    let personality = match species {
        "MOA" => MOA_PERSONALITY,
        "RUU" => {
            config.idle = DurationRange { min: 18., max: 32. };
            config.looking = DurationRange { min: 2., max: 4. };
            config.cursor_cooldown = 10.;
            config.weights.base = [35, 5, 15, 5];
            CompanionPersonality {
                curiosity: TraitScore::new(95),
                bravery: TraitScore::new(75),
                affection: TraitScore::new(60),
                energy: TraitScore::new(85),
                mischief: TraitScore::new(60),
            }
        }
        "NOX" => {
            config.idle = DurationRange { min: 40., max: 70. };
            config.looking = DurationRange { min: 5., max: 9. };
            config.cursor_cooldown = 22.;
            config.weights.base = [3, 20, 25, 5];
            config.weights.walking_energy = 25;
            config.weights.nearby_looking_bonus = 65;
            CompanionPersonality {
                curiosity: TraitScore::new(65),
                bravery: TraitScore::new(20),
                affection: TraitScore::new(45),
                energy: TraitScore::new(25),
                mischief: TraitScore::new(10),
            }
        }
        _ => return None,
    };
    Some((personality, config))
}
/// Growth changes cadence, preparation and recovery rather than sprite scale or top speed.
/// These simulation policies do not approve or register missing stage artwork.
pub fn stage_config(species: &str, stage: u32) -> Option<(CompanionPersonality, BehaviorConfig)> {
    living_coverage(species, stage)?;
    let (personality, mut config) = decision_config(species)?;
    let growth = f64::from(stage - 1);
    config.idle.min += growth * 5.;
    config.idle.max += growth * 5.;
    config.weights.nearby_looking_bonus += (stage - 1) * 5;
    config.cursor_cooldown += growth * 3.;
    config.walk_radius = [100., 130., 160., 180., 180.][(stage - 1) as usize];
    // Young forms dart briefly; adults pause deliberately and settle after each excursion.
    let cadence = match species {
        "RUU" => 0.6,
        "NOX" => 1.4,
        _ => 1.,
    };
    config.walk_preparation = [0., 0.2, 0.3, 0.45, 0.6][(stage - 1) as usize] * cadence;
    config.walk_recovery = [0., 1., 1.5, 2., 3.][(stage - 1) as usize] * cadence;
    Some((personality, config))
}
pub fn living_config(species: &str, stage: u32) -> Option<(CompanionPersonality, BehaviorConfig)> {
    match living_coverage(species, stage)? {
        LivingCoverage::AwaitingAssets => None,
        LivingCoverage::Animated | LivingCoverage::BaseOnly => stage_config(species, stage),
    }
}
