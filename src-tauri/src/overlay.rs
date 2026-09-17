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
