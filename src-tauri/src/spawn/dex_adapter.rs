//! Narrow projection of the merged Monster Dex JSON, not another monster master.
use super::*;
use serde::Deserialize;
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Metadata {
    monster_code: String,
    enabled: bool,
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
        "EDGE" | "NEAR_DESKTOP_EDGE" => SpawnZone::LowerCorner,
        "FREE_AREA" | "FLOATING_AREA" => SpawnZone::FreeArea,
        "NEAR_DOCK" => SpawnZone::NearDock,
        _ => return None,
    })
}
pub(super) fn pip_candidate(code: &str) -> Option<Candidate> {
    if code != "PIP" {
        return None;
    }
    let records: Vec<Metadata> =
        serde_json::from_str(include_str!("../../../src/entities/monster-dex.json")).ok()?;
    let mut matches = records.into_iter().filter(|m| m.monster_code == code);
    let metadata = matches.next()?;
    if matches.next().is_some()
        || !metadata.enabled
        || metadata.production_status != "PRODUCTION"
        || metadata.movement_profile != MovementProfile::Ground
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
            assert!(zone(&metadata.spawn_profile).is_some());
            if metadata.monster_code != "PIP" {
                assert!(pip_candidate(&metadata.monster_code).is_none());
            }
        }
        assert!(zone("UNREVIEWED_PROFILE").is_none());
        let pip = pip_candidate("PIP").unwrap();
        assert_eq!(pip.zone, SpawnZone::Bottom);
        assert_eq!(pip.movement_profile, MovementProfile::Ground);
        assert_eq!(pip.condition, SpawnCondition::AnyTime);
    }
}
