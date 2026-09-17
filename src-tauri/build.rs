fn main() {
    assert!(
        std::env::var("CARGO_CFG_TARGET_OS").unwrap() == "macos",
        "This spike requires macOS"
    );
    cc::Build::new()
        .file("native/panel.m")
        .flag("-fobjc-arc")
        .compile("luma_panel");
    println!("cargo:rustc-link-lib=framework=AppKit");
    println!("cargo:rerun-if-changed=native/panel.m");
    tauri_build::build();
}
