//! Exact approved bytes also make absent source delivery a compile failure.
//! At startup the native asset resolver checks the actual frontend bundle against these bytes.
pub fn approved_bytes(code: &str) -> Option<&'static [u8]> {
    Some(match code {
        "PIP" => include_bytes!("../../../public/assets/monsters/pip/base.png"),
        "MELLO" => include_bytes!("../../../public/assets/monsters/mello/base.png"),
        "MOSSY" => include_bytes!("../../../public/assets/monsters/mossy/base.png"),
        "CHIRP" => include_bytes!("../../../public/assets/monsters/chirp/base.png"),
        "BUBU" => include_bytes!("../../../public/assets/monsters/bubu/base.png"),
        "PEBB" => include_bytes!("../../../public/assets/monsters/pebb/base.png"),
        "PUFF" => include_bytes!("../../../public/assets/monsters/puff/base.png"),
        "TIKKI" => include_bytes!("../../../public/assets/monsters/tikki/base.png"),
        "MIMI" => include_bytes!("../../../public/assets/monsters/mimi/base.png"),
        "WISP" => include_bytes!("../../../public/assets/monsters/wisp/base.png"),
        _ => return None,
    })
}
pub fn available(code: &str, bytes: Option<&[u8]>) -> bool {
    approved_bytes(code)
        .zip(bytes)
        .is_some_and(|(approved, actual)| approved == actual)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn missing_corrupt_wrong_species_and_unknown_assets_fail_closed() {
        for code in [
            "PIP", "MELLO", "MOSSY", "CHIRP", "BUBU", "PEBB", "PUFF", "TIKKI", "MIMI", "WISP",
        ] {
            assert!(available(code, approved_bytes(code)));
            assert!(!available(code, None));
            assert!(!available(code, Some(b"broken")));
            if code != "PIP" {
                assert!(!available(code, approved_bytes("PIP")));
            }
        }
        assert!(!available("UNKNOWN", approved_bytes("PIP")));
    }
}
