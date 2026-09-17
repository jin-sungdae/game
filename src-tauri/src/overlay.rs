use crate::entities::Area;
use std::ffi::c_void;
extern "C" {
    pub fn luma_init();
    pub fn luma_focus_audit_start();
    pub fn luma_focus_audit_end();
    pub fn luma_attach(window: *mut c_void, index: i32, width: f64, height: f64);
    pub fn luma_place(index: i32, x: f64, y: f64, visible: i32);
    pub fn luma_action() -> i32;
    pub fn luma_is_active() -> i32;
    pub fn luma_cleanup();
    fn luma_work_area(x: *mut f64, y: *mut f64, w: *mut f64, h: *mut f64);
    fn luma_trace_geometry(
        index: i32,
        x: f64,
        y: f64,
        ground: f64,
        width: f64,
        height: f64,
        margin: f64,
        ground_margin: f64,
        panel_x: f64,
        panel_y: f64,
        visible: i32,
    );
    fn luma_cursor(x: *mut f64, y: *mut f64, down: *mut i32);
}
// All bridge calls must run on AppKit's main thread.
pub fn area() -> Area {
    let mut a = Area {
        x: 0.0,
        y: 0.0,
        w: 0.0,
        h: 0.0,
    };
    unsafe { luma_work_area(&mut a.x, &mut a.y, &mut a.w, &mut a.h) };
    a
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
        crate::geometry::LAYOUT.margin,
        crate::geometry::LAYOUT.ground_margin,
        bounds.x,
        bounds.y,
        visible as i32,
    );
}
