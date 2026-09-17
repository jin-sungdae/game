# LUMA Single Instance Guard

## Implementation

The first plugin registered on the Tauri builder is the official
`tauri-plugin-single-instance = "=2.4.4"`, with an empty callback.
It is a macOS-only Rust dependency. There is no JavaScript dependency or
frontend permission/capability change. Tauri remains 2.11.5 and Tao remains
0.35.3 with its existing opt-in startup patch.

Tauri initializes plugins while building the application, before the application
setup callback. The plugin therefore rejects a secondary before `luma_init`,
native panel attachment or World construction. The primary receives the plugin's
notification but deliberately ignores it: no show, focus, activation, PIP spawn,
argument handling or working-directory handling is performed.

On macOS the official plugin uses a Unix domain socket derived from the bundle
identifier (`/tmp/dev_luma_spike_si.sock`). A secondary that successfully notifies
the listener calls `std::process::exit(0)`. It does not run application setup or
normal application exit cleanup. A secondary's focus audit consequently has a
startup row but no normal-exit row; process exit and absence of panel/state logs
are checked separately. The primary removes its listener socket on normal exit.

Sources: [official Tauri 2 plugin documentation](https://v2.tauri.app/plugin/single-instance/),
[official macOS implementation, version 2.4.4](https://docs.rs/crate/tauri-plugin-single-instance/2.4.4/source/src/platform_impl/macos.rs).

## Scope and maintenance risks

- Acceptance covers launching another copy **after the first is running**.
  The official macOS listener binds asynchronously; simultaneous cold launches
  are not an atomic election guarantee and are not claimed as validated here.
- The official implementation fails open on some socket errors/bind failures.
  This is not a fail-closed lock. Shared `/tmp` and a fixed identifier also mean
  another user/process using the same socket path can interfere.
- Old builds without this plugin cannot participate in the guard. Quit all old
  copies once when upgrading, then launch the new build.
- Development and bundled builds sharing this identifier share the guard. Quit
  the bundled primary before expecting a dev build to start its own entities.
- Revalidate duplicate launch, normal-exit/relaunch and focus when upgrading the
  plugin or Tauri. Do not add the usual single-instance `set_focus` example.
- Cargo.lock adds platform-specific transitive dependencies of the official
  plugin; existing package versions are retained. Native NSPanel, Tao vendor,
  Companion behavior and rendering code are unchanged.

## Reproducing the platform integration test

Quit existing LUMA copies through their normal Quit command. Keep another
application in the foreground without switching applications during the test.

```sh
npm ci
npm run tauri -- build --debug --bundles app
clang -fobjc-arc -framework AppKit scripts/single_instance_audit.m -o /tmp/luma-single-audit
/tmp/luma-single-audit "$PWD/src-tauri/target/debug/bundle/macos/LUMA Spike.app" /tmp/luma-single-run-1
```

Use a new output directory for each run. The test takes about 10 seconds and
uses existing `LUMA_SMOKE`/`LUMA_FOCUS_AUDIT` hooks. It starts one primary and
three secondaries (two LaunchServices launches and one direct bundle executable).
It checks secondary exit, no secondary panel/state initialization, sampled
CoreGraphics window counts, native activation/key-window audit, and foreground
notifications plus 10 ms polling. The primary must continue its PIP smoke
lifecycle and quit normally. This harness does not activate applications, inject
input, search for processes to kill, or terminate processes by name.

The primary intentionally creates three native panels (MOA, initially hidden
PIP and interaction panel). This is one entity world, not three MOAs. Secondary
panel creation must be zero. Sampling alone cannot exclude sub-sample windows;
the setup/panel logs and pre-setup exit path supplement the measurements.

Actual human mouse/typing verification is distinct from this automated native
test. It must not be reported as performed by the harness.

## Validation

- Rust tests: 30 passed.
- `cargo clippy --locked --no-deps -- -D warnings`: passed for application code;
  existing vendored Tao dependency warnings remain.
- Rust formatting: passed.
- `npm ci` and `npm run build`: passed (build invoked by Tauri bundle build).
- Debug `.app` build: passed.
- Tao patch check: passed, exactly the existing three documented vendor files.
- Existing automation policy tests: 8 passed; no automation code changed.
- Actual macOS duplicate-launch evidence: pending platform run.
