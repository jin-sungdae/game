//! Species expression over existing personality decisions, never a movement/profile override.
//! Distance/speed are bounded multipliers; interval only changes the next idle decision.
//! No per-tick parsing, allocation, timer, RNG stream or animation state is added.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Expression {
    pub distance: f64,
    pub speed: f64,
    pub interval: f64,
}
impl Default for Expression {
    fn default() -> Self {
        Self {
            distance: 1.,
            speed: 1.,
            interval: 1.,
        }
    }
}
impl Expression {
    pub fn for_species(code: &str) -> Self {
        // Only currently enabled Production identities. Provisional content is never activated.
        // Ground: small lively steps / rooted rest / heavy stones / inquisitive range.
        // Aerial bodies change excursion extent, never native trajectory or landing ownership.
        let (distance, speed, interval) = match code {
            "PIP" => (0.9, 1.0, 1.0),
            "MOSSY" => (0.7, 0.85, 1.4),
            "PEBB" => (0.65, 0.8, 1.3),
            "TIKKI" => (1.15, 1.05, 1.1),
            "MELLO" => (0.85, 0.9, 1.2),
            "BUBU" => (1.1, 1.1, 1.0),
            "CHIRP" => (1.2, 1.1, 1.05),
            "PUFF" => (0.8, 0.85, 1.2),
            "WISP" => (1.05, 1.0, 1.1),
            "LUNET" => (0.9, 0.8, 1.4),
            "MIMI" => (1.0, 1.0, 1.5), // STATIC still always pauses.
            "SHADE" => (0.85, 0.9, 1.25),
            "NOCT" => (1.1, 1.0, 1.4),
            "EMBER" => (0.95, 1.1, 1.05),
            "NOVA" => (1.2, 1.05, 1.15),
            _ => return Self::default(),
        };
        Self {
            distance,
            speed,
            interval,
        }
    }
}
