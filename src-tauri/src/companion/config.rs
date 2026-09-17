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
