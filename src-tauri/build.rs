fn main() {
    assert!(
        std::env::var("CARGO_CFG_TARGET_OS").unwrap() == "macos",
        "This spike requires macOS"
    );
    let mut native = cc::Build::new();
    if std::env::var("DEBUG").as_deref() == Ok("true") {
        native.define("LUMA_DEBUG_BUILD", None);
    }
    native
        .file("native/panel.m")
        .file("native/focus_audit.m")
        .flag("-fobjc-arc")
        .compile("luma_panel");
    println!("cargo:rustc-link-lib=framework=AppKit");
    println!("cargo:rerun-if-changed=native/panel.m");
    println!("cargo:rerun-if-changed=native/focus_audit.m");
    tauri_build::build();
}
