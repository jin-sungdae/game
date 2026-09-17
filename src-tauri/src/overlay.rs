use crate::desktop::{DesktopSafeArea, Insets, SafeAreaTracker, CONFIG};
use crate::entities::Area;
use std::{cell::RefCell, ffi::c_void, time::Instant};
extern "C" {
    pub fn luma_init();
    pub fn luma_focus_audit_start();
    pub fn luma_focus_audit_end();
    pub fn luma_attach(window: *mut c_void, index: i32, width: f64, height: f64);
    pub fn luma_place(index: i32, x: f64, y: f64, visible: i32);
    pub fn luma_action() -> i32;
    pub fn luma_is_active() -> i32;
    pub fn luma_cleanup();
    fn luma_desktop(
        screen: *mut Area,
        visible: *mut Area,
        docks: *mut Area,
        count: *mut i32,
        screen_id: *mut u32,
    );
    fn luma_set_safe_area(
        safe: *const Area,
        docks: *const Area,
        count: i32,
        fallback: *const Insets,
        retained: *const Insets,
        rejected: i32,
    );
    fn luma_trace_geometry(
        index: i32,
        x: f64,
        y: f64,
        ground: f64,
        width: f64,
        height: f64,
        margin: f64,
        ground_margin: f64,
        top_margin: f64,
        panel_x: f64,
        panel_y: f64,
        visible: i32,
    );
    fn luma_movement_windows(out: *mut Area, count: *mut i32);
    fn luma_cursor(x: *mut f64, y: *mut f64, down: *mut i32);
}
// All bridge calls must run on AppKit's main thread.
#[derive(Default)]
struct DesktopCache {
    tracker: SafeAreaTracker,
    window_sample: Option<(Instant, Option<Vec<Area>>)>,
    last: Option<(Instant, DesktopSafeArea)>,
}
thread_local! { static DESKTOP: RefCell<DesktopCache> = RefCell::new(DesktopCache::default()); }
pub fn area() -> Area {
    DESKTOP.with(|cache| {
        let mut cache = cache.borrow_mut();
        if let Some((time, sample)) = &cache.last {
            if time.elapsed().as_secs_f64() < CONFIG.dock_poll_seconds {
                return sample.final_luma_safe_area;
            }
        }
        let (mut screen, mut visible) = (Area::default(), Area::default());
        let mut docks = [Area::default(); 32];
        let (mut count, mut id) = (docks.len() as i32, 0);
        unsafe {
            luma_desktop(
                &mut screen,
                &mut visible,
                docks.as_mut_ptr(),
                &mut count,
                &mut id,
            )
        };
        let sample = cache.tracker.update(
            id,
            screen,
            visible,
            &docks[..(count.max(0) as usize).min(docks.len())],
        );
        unsafe {
            luma_set_safe_area(
                &sample.final_luma_safe_area,
                sample.detected_dock_bounds.as_ptr(),
                sample.detected_dock_bounds.len() as i32,
                &sample.fallback_safe_insets,
                &sample.retained_safe_insets,
                sample.rejected_dock_candidates as i32,
            )
        };
        let area = sample.final_luma_safe_area;
        cache.last = Some((Instant::now(), sample));
        area
    })
}
pub fn cursor() -> ((f64, f64), bool) {
    let (mut x, mut y, mut down) = (0.0, 0.0, 0);
    unsafe { luma_cursor(&mut x, &mut y, &mut down) };
    ((x, y), down != 0)
}

pub unsafe fn place_entity<S>(index: i32, entity: &crate::entities::Entity<S>, area: Area) {
    let bounds = area.panel_bounds(entity.x, entity.y, entity.size);
    let visible = area.fits(entity.size);
    luma_place(index, bounds.x, bounds.y, visible as i32);
    luma_trace_geometry(
        index,
        entity.x,
        entity.y,
        area.ground_y(),
        entity.size.width,
        entity.size.height,
        CONFIG.side_margin,
        CONFIG.ground_margin,
        CONFIG.top_margin,
        bounds.x,
        bounds.y,
        visible as i32,
    );
}

/// Metadata only, sampled once per second on the main thread. None suppresses excursions.
pub fn movement_windows() -> Option<Vec<Area>> {
    DESKTOP.with(|cache| {
        let mut cache = cache.borrow_mut();
        if let Some((time, sample)) = &cache.window_sample {
            if time.elapsed().as_secs_f64() < crate::movement::WINDOW_POLL_SECONDS {
                return sample.clone();
            }
        }
        let mut windows = [Area::default(); 64];
        let mut count = windows.len() as i32;
        unsafe {
            luma_movement_windows(windows.as_mut_ptr(), &mut count);
        }
        let result = if count < 0 {
            None
        } else {
            Some(windows[..(count as usize).min(windows.len())].to_vec())
        };
        cache.window_sample = Some((Instant::now(), result.clone()));
        result
    })
}
