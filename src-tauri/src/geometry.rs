//! AppKit logical points, +Y upward. Entity position is the panel's bottom-center.
use serde::Serialize;
#[derive(Clone, Copy, Debug, Serialize)]
pub struct Size {
    pub width: f64,
    pub height: f64,
}
pub const MOA_SIZE: Size = Size {
    width: 96.0,
    height: 104.0,
};
pub const PIP_SIZE: Size = Size {
    width: 96.0,
    height: 104.0,
};
pub const MENU_SIZE: Size = Size {
    width: 160.0,
    height: 140.0,
};
pub use crate::desktop::CONFIG as LAYOUT;
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct Area {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}
impl Size {
    pub fn bounds(self, x: f64, y: f64) -> Area {
        Area {
            x: x - self.width / 2.0,
            y,
            w: self.width,
            h: self.height,
        }
    }
}
impl Area {
    pub fn ground_y(self) -> f64 {
        self.y + LAYOUT.ground_margin
    }
    pub fn fits(self, size: Size) -> bool {
        (self.x + LAYOUT.side_margin).ceil()
            <= (self.x + self.w - LAYOUT.side_margin - size.width).floor()
            && self.ground_y().ceil() <= (self.y + self.h - LAYOUT.top_margin - size.height).floor()
    }
    /// Clamp the whole panel. If it cannot fit, caller hides it (never claims containment).
    pub fn clamp(self, x: f64, y: f64, size: Size) -> (f64, f64) {
        let left = self.x + LAYOUT.side_margin + size.width / 2.0;
        let right = self.x + self.w - LAYOUT.side_margin - size.width / 2.0;
        let bottom = self.ground_y();
        let top = self.y + self.h - LAYOUT.top_margin - size.height;
        (
            x.clamp(left, right.max(left)),
            y.clamp(bottom, top.max(bottom)),
        )
    }
    pub fn ground(self, x: f64, size: Size) -> (f64, f64) {
        self.clamp(x, self.ground_y(), size)
    }
    /// NSPanel frame origins use integral logical points on the validated macOS host.
    /// Project only presentation; keep simulation/subpixel movement continuous.
    pub fn panel_bounds(self, x: f64, y: f64, size: Size) -> Area {
        let mut b = size.bounds(x, y);
        let left = (self.x + LAYOUT.side_margin).ceil();
        let bottom = self.ground_y().ceil();
        b.x = b.x.round().clamp(
            left,
            (self.x + self.w - LAYOUT.side_margin - size.width)
                .floor()
                .max(left),
        );
        b.y = b.y.round().clamp(
            bottom,
            (self.y + self.h - LAYOUT.top_margin - size.height)
                .floor()
                .max(bottom),
        );
        b
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn check(a: Area, size: Size, p: (f64, f64)) {
        assert!(a.fits(size));
        let b = size.bounds(p.0, p.1);
        assert!(b.x >= a.x + LAYOUT.side_margin);
        assert!(b.x + b.w <= a.x + a.w - LAYOUT.side_margin);
        assert!(b.y >= a.ground_y());
        assert!(b.y + b.h <= a.y + a.h - LAYOUT.top_margin);
    }
    #[test]
    fn dock_sides_negative_monitors_and_all_edges() {
        // visibleFrames supplied by OS: no Dock orientation logic in the model.
        for a in [
            Area {
                x: 0.0,
                y: 80.0,
                w: 1440.0,
                h: 790.0,
            }, // bottom Dock, top menu
            Area {
                x: 80.0,
                y: 0.0,
                w: 1360.0,
                h: 870.0,
            }, // left Dock
            Area {
                x: 0.0,
                y: 0.0,
                w: 1360.0,
                h: 870.0,
            }, // right Dock
            Area {
                x: -1920.0,
                y: -1000.0,
                w: 1920.0,
                h: 960.0,
            },
        ] {
            for size in [
                MOA_SIZE,
                Size {
                    width: 160.0,
                    height: 220.0,
                },
            ] {
                for (x, y) in [
                    (-10000.0, -10000.0),
                    (10000.0, 10000.0),
                    (-10000.0, 10000.0),
                    (10000.0, -10000.0),
                ] {
                    check(a, size, a.clamp(x, y, size));
                    check(a, size, a.ground(x, size));
                }
            }
        }
    }
    #[test]
    fn different_heights_share_ground_and_anchor_roundtrips() {
        let a = Area {
            x: -500.0,
            y: -300.0,
            w: 1500.0,
            h: 900.0,
        };
        let tall = Size {
            width: 140.0,
            height: 240.0,
        };
        let moa = a.ground(200.0, MOA_SIZE);
        let pip = a.ground(400.0, tall);
        assert_eq!(moa.1, pip.1);
        for (p, size) in [(moa, MOA_SIZE), (pip, tall)] {
            let b = size.bounds(p.0, p.1);
            assert_eq!((b.x + b.w / 2.0, b.y), p);
            check(a, size, p);
        }
    }
    #[test]
    fn impossible_viewport_is_explicit_and_does_not_panic() {
        let a = Area {
            x: 100.0,
            y: -50.0,
            w: 50.0,
            h: 50.0,
        };
        assert!(!a.fits(MOA_SIZE));
        let p = a.clamp(0.0, 0.0, MOA_SIZE);
        assert!(p.0.is_finite() && p.1.is_finite());
    }
    #[test]
    fn native_projection_is_integral_and_stays_inside_fractional_edges() {
        let a = Area {
            x: -1200.25,
            y: -600.5,
            w: 1500.0,
            h: 900.0,
        };
        for (x, y) in [(-10000.0, -10000.0), (10000.0, 10000.0), (100.3, 0.8)] {
            let p = a.clamp(x, y, MOA_SIZE);
            let b = a.panel_bounds(p.0, p.1, MOA_SIZE);
            assert_eq!(b.x.fract(), 0.0);
            assert_eq!(b.y.fract(), 0.0);
            check(a, MOA_SIZE, (b.x + b.w / 2.0, b.y));
        }
    }
}
