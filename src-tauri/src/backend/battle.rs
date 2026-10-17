use super::*;
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
pub struct DamageEvent {
    pub r#type: String,
    pub damage: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Hp {
    pub hp: u32,
    pub max_hp: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
pub struct Reward {
    pub gold: u64,
    pub exp: u64,
    pub bond: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Status {
    Active,
    Victory,
    Defeat,
    Captured,
    Escaped,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Battle {
    pub battle_id: uuid::Uuid,
    pub encounter_id: uuid::Uuid,
    pub turn: u32,
    pub status: Status,
    pub encounter_status: String,
    pub companion: Hp,
    pub monster: Hp,
    pub events: Vec<String>,
    #[serde(default)]
    pub presentation_events: Vec<DamageEvent>,
    pub reward: Option<Reward>,
    #[serde(default)]
    pub skills: Vec<SkillOption>,
    #[serde(default)]
    pub skill_cue: Option<SkillCue>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SkillOption {
    pub code: String,
    pub name: String,
    pub ready_turn: u32,
    pub asset_status: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SkillPhase {
    pub phase: String,
    pub duration_ms: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SkillCue {
    pub command_id: uuid::Uuid,
    pub skill_code: String,
    pub species: String,
    pub cast_motion: String,
    pub element: String,
    pub asset_status: String,
    pub phases: Vec<SkillPhase>,
}
#[derive(Deserialize)]
pub struct SkillResult {
    pub battle: Battle,
    pub cue: SkillCue,
}
impl Battle {
    fn valid(&self) -> bool {
        !self.battle_id.is_nil()
            && !self.encounter_id.is_nil()
            && self.companion.max_hp > 0
            && self.companion.hp <= self.companion.max_hp
            && self.monster.max_hp > 0
            && self.monster.hp <= self.monster.max_hp
            && matches!(
                self.encounter_status.as_str(),
                "ACTIVE" | "EXPIRED" | "CAPTURED" | "DEFEATED" | "ESCAPED" | "PLAYER_DEFEATED"
            )
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Collected {
    pub monster_code: String,
    pub monster_name: String,
    pub capture_count: u64,
    pub first_captured_at: DateTime<Utc>,
    pub last_captured_at: DateTime<Utc>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Capture {
    pub battle_id: uuid::Uuid,
    pub encounter_id: uuid::Uuid,
    pub success: bool,
    pub chance: f64,
    #[serde(default)]
    pub base_chance: Option<f64>,
    #[serde(default)]
    pub item_bonus: Option<f64>,
    #[serde(default)]
    pub final_chance: Option<f64>,
    pub battle: Battle,
    pub collection: Option<Collected>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Resolution {
    pub encounter_id: uuid::Uuid,
    pub encounter_status: String,
}
#[derive(Clone, Debug)]
pub enum Command {
    InteractCompanion,
    Discover(super::discovery::Job),
    Spawn(crate::spawn::runtime::Action),
    LoadItems(Option<uuid::Uuid>),
    Purchase(String),
    UseItem(String, Option<uuid::Uuid>),
    Evolve,
    Encounter,
    StartBattle(uuid::Uuid),
    Attack(uuid::Uuid),
    Skill(uuid::Uuid, uuid::Uuid, String, u32),
    Capture(uuid::Uuid),
    LoadCollection,
    Ignore(uuid::Uuid),
    Refresh(uuid::Uuid),
}
#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Presentation {
    pub encounter_id: Option<uuid::Uuid>,
    pub monster_level: u32,
    pub battle: Option<Battle>,
    pub busy: bool,
    pub error: Option<String>,
    pub feedback: Option<String>,
    pub collection: Vec<Collected>,
    pub capture_chance: Option<f64>,
    pub capture_base_chance: Option<f64>,
    pub capture_item_bonus: Option<f64>,
    pub capture_final_chance: Option<f64>,
}
impl Presentation {
    pub fn command(&mut self, action: &str) -> Option<Command> {
        if self.busy {
            return None;
        }
        let c = match action {
            "encounter" => Command::Encounter,
            "interact" | "battle" => Command::StartBattle(self.encounter_id?),
            "attack" => Command::Attack(self.battle.as_ref()?.battle_id),
            "capture" => Command::Capture(self.battle.as_ref()?.battle_id),
            "collection" => Command::LoadCollection,
            "ignore" => Command::Ignore(self.encounter_id?),
            "refresh" => Command::Refresh(self.battle.as_ref()?.battle_id),
            a if a.starts_with("skill:") => {
                let battle = self.battle.as_ref()?;
                let code = a.strip_prefix("skill:")?;
                if battle.status != Status::Active
                    || !battle
                        .skills
                        .iter()
                        .any(|s| s.code == code && s.ready_turn <= battle.turn)
                {
                    return None;
                }
                Command::Skill(
                    battle.battle_id,
                    uuid::Uuid::new_v4(),
                    code.into(),
                    battle.turn,
                )
            }
            _ => return None,
        };
        self.busy = true;
        self.error = None;
        Some(c)
    }
    pub fn finish(&mut self, error: Option<String>) {
        self.busy = false;
        self.error = error;
    }
    pub fn apply_battle(&mut self, b: Battle) {
        if self.encounter_id == Some(b.encounter_id)
            && !self
                .battle
                .as_ref()
                .is_some_and(|old| old.battle_id == b.battle_id && old.turn > b.turn)
        {
            if !b.events.is_empty() {
                self.feedback = Some(b.events.join(" · "));
            }
            self.battle = Some(b);
        }
    }
}
impl Api {
    pub fn skill(
        &self,
        id: uuid::Uuid,
        command: uuid::Uuid,
        code: &str,
        turn: u32,
    ) -> Result<Battle, &'static str> {
        let result: SkillResult = self
            .request_json(
                &format!("/api/v1/battles/{id}/skills"),
                Some(
                    &serde_json::json!({"commandId":command,"skillCode":code,"expectedTurn":turn}),
                ),
            )?
            .ok_or("missing skill result")?;
        if !result.battle.valid()
            || result.battle.battle_id != id
            || Some(result.battle.turn) != turn.checked_add(1)
            || result.cue.command_id != command
            || result.cue.skill_code != code
            || result.cue.phases.len() != 6
            || result.cue.phases.iter().enumerate().any(|(i, p)| {
                let expected = [
                    "CAST_START",
                    "CHARGE",
                    "RELEASE",
                    "PROJECTILE",
                    "IMPACT",
                    "RECOVERY",
                ][i];
                (p.phase != expected && !(i == 3 && p.phase == "AREA"))
                    || p.duration_ms == 0
                    || p.duration_ms > 2000
            })
        {
            return Err("invalid skill result");
        }
        let mut battle = result.battle;
        battle.skill_cue = Some(result.cue);
        Ok(battle)
    }
    pub fn battle(&self, id: uuid::Uuid, action: Option<&str>) -> Result<Battle, &'static str> {
        let path = match action {
            Some("start") => format!("/api/v1/encounters/{id}/battle"),
            Some("attack") => format!("/api/v1/battles/{id}/attack"),
            None => format!("/api/v1/battles/{id}"),
            _ => return Err("invalid command"),
        };
        let b: Battle = self
            .request(&path, action.is_some())?
            .ok_or("missing battle")?;
        if !b.valid()
            || (action == Some("start") && b.encounter_id != id)
            || (action != Some("start") && b.battle_id != id)
        {
            return Err("invalid battle response");
        }
        Ok(b)
    }
    pub fn capture(&self, id: uuid::Uuid) -> Result<Capture, &'static str> {
        let c: Capture = self
            .request(&format!("/api/v1/battles/{id}/capture"), true)?
            .ok_or("missing capture")?;
        if !c.battle.valid()
            || c.battle_id != id
            || c.battle.battle_id != id
            || c.encounter_id != c.battle.encounter_id
            || !c.chance.is_finite()
            || !(0.05..=0.95).contains(&c.chance)
        {
            return Err("invalid capture response");
        }
        Ok(c)
    }
    #[cfg(test)]
    pub fn collection(&self) -> Result<Vec<Collected>, &'static str> {
        let c: Vec<Collected> = self
            .request("/api/v1/collection", false)?
            .ok_or("missing collection")?;
        if c.iter().any(|c| {
            c.capture_count == 0
                || c.monster_code.is_empty()
                || c.last_captured_at < c.first_captured_at
        }) {
            return Err("invalid collection");
        }
        Ok(c)
    }
    pub fn ignore(&self, id: uuid::Uuid) -> Result<Resolution, &'static str> {
        let r: Resolution = self
            .request(&format!("/api/v1/encounters/{id}/ignore"), true)?
            .ok_or("missing resolution")?;
        if r.encounter_id != id || r.encounter_status != "ESCAPED" {
            return Err("invalid resolution");
        }
        Ok(r)
    }
}

#[cfg(test)]
mod skill_tests {
    use super::*;
    fn battle(turn: u32) -> Battle {
        serde_json::from_value(serde_json::json!({"battleId":uuid::Uuid::from_u128(2),"encounterId":uuid::Uuid::from_u128(1),"turn":turn,"status":"ACTIVE","encounterStatus":"ACTIVE","companion":{"hp":100,"maxHp":100},"monster":{"hp":30,"maxHp":30},"events":[],"reward":null,"skills":[{"code":"MOA_S1","name":"Heal","readyTurn":2,"assetStatus":"ASSET_REQUIRED"}]})).unwrap()
    }
    #[test]
    fn native_skill_command_uses_server_availability_and_unique_identity() {
        let mut p = Presentation {
            encounter_id: Some(uuid::Uuid::from_u128(1)),
            battle: Some(battle(1)),
            ..Default::default()
        };
        assert!(p.command("skill:MOA_S1").is_none());
        p.battle = Some(battle(2));
        assert!(p.command("skill:UNKNOWN").is_none());
        let Some(Command::Skill(id, command, code, turn)) = p.command("skill:MOA_S1") else {
            panic!("skill command missing")
        };
        assert_eq!(id, uuid::Uuid::from_u128(2));
        assert!(!command.is_nil());
        assert_eq!(code, "MOA_S1");
        assert_eq!(turn, 2);
        assert!(p.command("skill:MOA_S1").is_none());
    }
    #[test]
    fn stale_replay_cannot_rewind_current_hp_or_turn() {
        let mut p = Presentation {
            encounter_id: Some(uuid::Uuid::from_u128(1)),
            battle: Some(battle(3)),
            ..Default::default()
        };
        p.apply_battle(battle(1));
        assert_eq!(p.battle.unwrap().turn, 3);
    }
}
