//! Narrow projection of the merged Monster Dex JSON, not another monster master.
use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Metadata {
    monster_code: String,
    enabled: bool,
    content_ready: bool,
    rarity: String,
    asset_identity: String,
    production_status: String,
    spawn_profile: String,
    spawn_condition: SpawnCondition,
    movement_profile: MovementProfile,
}
/// Content profiles are coarser than concrete placement zones. Ambiguous edge profiles
/// use the lower safe corner; floating content uses the interior. No gameplay activation.
fn zone(profile: &str) -> Option<SpawnZone> {
    Some(match profile {
        "BOTTOM" => SpawnZone::Bottom,
        "TOP" => SpawnZone::Top,
        "EDGE" | "NEAR_DESKTOP_EDGE" => SpawnZone::Edge,
        "LOWER_CORNER" => SpawnZone::LowerCorner,
        "FREE_AREA" | "FLOATING_AREA" => SpawnZone::FreeArea,
        "NEAR_DOCK" => SpawnZone::NearDock,
        _ => return None,
    })
}
pub(super) fn content_candidate(code: &str) -> Option<Candidate> {
    let records: Vec<Metadata> =
        serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).ok()?;
    let mut matches = records.into_iter().filter(|m| m.monster_code == code);
    let metadata = matches.next()?;
    if matches.next().is_some() {
        return None;
    }
    from_metadata(code, metadata)
}
fn from_metadata(code: &str, metadata: Metadata) -> Option<Candidate> {
    // MovementProfile deserialization rejects unknown engine profiles.
    if metadata.asset_identity != code.to_lowercase()
        || !["COMMON", "UNCOMMON", "RARE", "EPIC", "SPECIAL"].contains(&metadata.rarity.as_str())
        || !metadata.enabled
        || !metadata.content_ready
        || metadata.production_status != "PRODUCTION"
        || !metadata.spawn_condition.enabled()
    {
        return None;
    }
    Some(Candidate {
        monster_code: metadata.monster_code,
        zone: zone(&metadata.spawn_profile)?,
        movement_profile: metadata.movement_profile,
        size: crate::geometry::PIP_SIZE,
        lifetime: Duration::from_secs(60),
        condition: metadata.spawn_condition,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn merged_dex_vocabulary_and_pip_compatibility() {
        let records: Vec<Metadata> =
            serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).unwrap();
        for metadata in records {
            if metadata.enabled {
                assert!(zone(&metadata.spawn_profile).is_some());
            } else if metadata.spawn_profile == "LOWER_CORNER" {
                assert_eq!(zone(&metadata.spawn_profile), Some(SpawnZone::LowerCorner));
            } else {
                assert!(zone(&metadata.spawn_profile).is_some());
            }
            if ![
                "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP",
                "SHADE", "EMBER", "LUNET", "NOVA", "NOCT",
            ]
            .contains(&metadata.monster_code.as_str())
            {
                assert!(content_candidate(&metadata.monster_code).is_none());
            }
        }
        assert!(zone("UNREVIEWED_PROFILE").is_none());
        let pip = content_candidate("PIP").unwrap();
        assert_eq!(pip.zone, SpawnZone::NearDock);
        assert_eq!(pip.movement_profile, MovementProfile::Ground);
        assert_eq!(pip.condition, SpawnCondition::AnyTime);
    }
}

#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MonsterIdentity {
    pub monster_code: String,
    pub asset_identity: String,
    pub rarity: String,
    pub level: u32,
    pub encounter_id: Option<uuid::Uuid>,
    pub movement_profile: MovementProfile,
}
pub fn identity(code: &str) -> Option<MonsterIdentity> {
    let records: Vec<Metadata> =
        serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).ok()?;
    let m = records.into_iter().find(|m| {
        m.monster_code == code
            && m.enabled
            && m.content_ready
            && m.production_status == "PRODUCTION"
    })?;
    Some(MonsterIdentity {
        monster_code: m.monster_code,
        asset_identity: m.asset_identity,
        rarity: m.rarity,
        level: 0,
        encounter_id: None,
        movement_profile: m.movement_profile,
    })
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    #[test]
    fn unsupported_zone_fails_closed_and_lower_corner_has_explicit_mapping() {
        assert!(zone("UNSUPPORTED").is_none());
        assert_eq!(zone("LOWER_CORNER"), Some(SpawnZone::LowerCorner));
        assert_eq!(
            content_candidate("MOSSY").unwrap().zone,
            SpawnZone::LowerCorner
        );
        assert!(content_candidate("SHADE").is_some());
        assert!(content_candidate("constructor").is_none());
        assert_eq!(identity("PIP").unwrap().asset_identity, "pip");
    }
    #[test]
    fn all_movement_wire_profiles_reuse_the_existing_engine_enum() {
        let names = [
            "GROUND", "JUMP", "FREE_2D", "FLOATING", "FLYING", "EDGE", "STATIC",
        ];
        let expected = [
            MovementProfile::Ground,
            MovementProfile::Jump,
            MovementProfile::Free2d,
            MovementProfile::Floating,
            MovementProfile::Flying,
            MovementProfile::Edge,
            MovementProfile::Static,
        ];
        for (name, profile) in names.into_iter().zip(expected) {
            assert_eq!(
                serde_json::from_value::<MovementProfile>(serde_json::json!(name)).unwrap(),
                profile
            );
        }
    }
}

#[cfg(test)]
pub(super) fn fixture_zone(profile: &str) -> Option<SpawnZone> {
    zone(profile)
}

#[cfg(test)]
mod advanced_contract {
    use super::*;
    #[test]
    fn readiness_gate_is_independent_of_supported_profiles_and_rarities() {
        let records: Vec<serde_json::Value> =
            serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).unwrap();
        for code in ["SHADE", "EMBER", "LUNET", "NOVA", "NOCT"] {
            let mut fixture = records
                .iter()
                .find(|m| m["monsterCode"] == code)
                .unwrap()
                .clone();
            assert!(content_candidate(code).is_some());
            for (key, value) in [
                ("enabled", false.into()),
                ("contentReady", false.into()),
                ("productionStatus", "PROVISIONAL".into()),
            ] {
                let mut rejected = fixture.clone();
                rejected[key] = value;
                assert!(from_metadata(code, serde_json::from_value(rejected).unwrap()).is_none());
            }
            fixture["enabled"] = true.into();
            fixture["contentReady"] = true.into();
            fixture["productionStatus"] = "PRODUCTION".into();
            let candidate =
                from_metadata(code, serde_json::from_value(fixture.clone()).unwrap()).unwrap();
            assert_eq!(candidate.monster_code, code);
            for rarity in ["COMMON", "UNCOMMON", "RARE", "EPIC", "SPECIAL"] {
                fixture["rarity"] = rarity.into();
                let other =
                    from_metadata(code, serde_json::from_value(fixture.clone()).unwrap()).unwrap();
                assert_eq!(candidate.zone, other.zone);
                assert_eq!(candidate.movement_profile, other.movement_profile);
                assert_eq!(candidate.condition, other.condition);
            }
            fixture["spawnCondition"] = "SPECIAL_EVENT".into();
            assert!(from_metadata(code, serde_json::from_value(fixture).unwrap()).is_none());
        }
    }
}
