//! OS visible frame is a hint, not the safe placement contract (auto-hide Dock).
use crate::geometry::Area;
use serde::Serialize;
use std::collections::BTreeMap;

pub struct DesktopSafeAreaConfig {
    pub ground_margin: f64,
    pub side_margin: f64,
    pub top_margin: f64,
    pub menu_gap: f64,
    pub fallback_bottom_inset: f64,
    pub fallback_side_inset: f64,
    pub dock_poll_seconds: f64,
    pub edge_tolerance: f64,
    pub max_edge_fraction: f64,
    pub minimum_aspect: f64,
}
// Fixed conservative reservation, NOT a claim about the system's maximum Dock size.
// Unknown/hidden Dock may move to any of the three edges, so reserve all three.
pub const CONFIG: DesktopSafeAreaConfig = DesktopSafeAreaConfig {
    ground_margin: 8.0,
    side_margin: 8.0,
    top_margin: 8.0,
    menu_gap: 6.0,
    fallback_bottom_inset: 192.0,
    fallback_side_inset: 192.0,
    dock_poll_seconds: 1.0,
    edge_tolerance: 24.0,
    max_edge_fraction: 0.35,
    minimum_aspect: 2.0,
};
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, Serialize)]
pub struct Insets {
    pub bottom: f64,
    pub left: f64,
    pub right: f64,
    pub top: f64,
}
impl Insets {
    fn union(self, other: Self) -> Self {
        Self {
            bottom: self.bottom.max(other.bottom),
            left: self.left.max(other.left),
            right: self.right.max(other.right),
            top: self.top.max(other.top),
        }
    }
    fn apply(self, screen: Area) -> Area {
        Area {
            x: screen.x + self.left,
            y: screen.y + self.bottom,
            w: (screen.w - self.left - self.right).max(0.0),
            h: (screen.h - self.bottom - self.top).max(0.0),
        }
    }
}
#[derive(Clone, Debug, Serialize)]
pub struct DesktopSafeArea {
    pub screen_frame: Area,
    pub os_visible_frame: Area,
    pub detected_dock_bounds: Vec<Area>,
    pub rejected_dock_candidates: usize,
    pub fallback_safe_insets: Insets,
    pub retained_safe_insets: Insets,
    pub final_luma_safe_area: Area,
}
#[derive(Default)]
pub struct SafeAreaTracker {
    retained: BTreeMap<u32, Insets>,
}
impl SafeAreaTracker {
    pub fn update(
        &mut self,
        screen_id: u32,
        screen: Area,
        visible: Area,
        candidates: &[Area],
    ) -> DesktopSafeArea {
        let fallback = Insets {
            bottom: CONFIG.fallback_bottom_inset,
            left: CONFIG.fallback_side_inset,
            right: CONFIG.fallback_side_inset,
            top: 0.0,
        };
        let os = Insets {
            bottom: (visible.y - screen.y).max(0.0),
            left: (visible.x - screen.x).max(0.0),
            right: (screen.x + screen.w - visible.x - visible.w).max(0.0),
            top: (screen.y + screen.h - visible.y - visible.h).max(0.0),
        };
        let mut next = fallback.union(os);
        let mut detected = Vec::new();
        for &dock in candidates {
            if let Some(insets) = occupied_edge(screen, dock) {
                next = next.union(insets);
                detected.push(dock);
            }
        }
        // Do not fall when Dock hides, moves to another edge, or metadata disappears.
        // Display identity (not origin) isolates history across monitor arrangements.
        let retained = self.retained.entry(screen_id).or_default();
        *retained = retained.union(next);
        DesktopSafeArea {
            screen_frame: screen,
            os_visible_frame: visible,
            rejected_dock_candidates: candidates.len() - detected.len(),
            detected_dock_bounds: detected,
            fallback_safe_insets: fallback,
            retained_safe_insets: *retained,
            final_luma_safe_area: retained.apply(screen),
        }
    }
}
fn occupied_edge(screen: Area, dock: Area) -> Option<Insets> {
    if ![dock.x, dock.y, dock.w, dock.h]
        .iter()
        .all(|x| x.is_finite())
        || dock.w <= 0.0
        || dock.h <= 0.0
    {
        return None;
    }
    let left = dock.x.max(screen.x);
    let right = (dock.x + dock.w).min(screen.x + screen.w);
    let bottom = dock.y.max(screen.y);
    let top = (dock.y + dock.h).min(screen.y + screen.h);
    if right <= left || top <= bottom {
        return None;
    }
    let mut i = Insets::default();
    if dock.w >= dock.h * CONFIG.minimum_aspect
        && dock.h <= screen.h * CONFIG.max_edge_fraction
        && (dock.y - screen.y).abs() <= CONFIG.edge_tolerance
    {
        i.bottom = top - screen.y;
    } else if dock.h >= dock.w * CONFIG.minimum_aspect
        && dock.w <= screen.w * CONFIG.max_edge_fraction
    {
        if (dock.x - screen.x).abs() <= CONFIG.edge_tolerance {
            i.left = right - screen.x;
        } else if (dock.x + dock.w - screen.x - screen.w).abs() <= CONFIG.edge_tolerance {
            i.right = screen.x + screen.w - left;
        } else {
            return None;
        }
    } else {
        return None;
    }
    Some(i)
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::{Size, MOA_SIZE, PIP_SIZE};
    fn screen() -> Area {
        Area {
            x: 0.0,
            y: 0.0,
            w: 1600.0,
            h: 1000.0,
        }
    }
    #[test]
    fn full_visible_frame_with_bottom_overlay_uses_dock_and_fallback() {
        let s = screen();
        let dock = Area {
            x: 200.0,
            y: 0.0,
            w: 1200.0,
            h: 240.0,
        };
        let result = SafeAreaTracker::default().update(1, s, s, &[dock]);
        assert_eq!(result.final_luma_safe_area.y, 240.0);
        assert_eq!(result.detected_dock_bounds.len(), 1);
        assert_eq!(result.final_luma_safe_area.ground_y(), 248.0);
    }
    #[test]
    fn left_and_right_dock_edges_are_reserved() {
        let s = screen();
        for (x, left) in [(0.0, true), (1360.0, false)] {
            let dock = Area {
                x,
                y: 100.0,
                w: 240.0,
                h: 800.0,
            };
            let r = SafeAreaTracker::default().update(1, s, s, &[dock]);
            assert_eq!(
                if left {
                    r.retained_safe_insets.left
                } else {
                    r.retained_safe_insets.right
                },
                240.0
            );
            assert_eq!(r.detected_dock_bounds.len(), 1);
        }
    }
    #[test]
    fn hidden_or_fullscreen_proxy_never_means_ground_eight() {
        let s = screen();
        for candidates in [vec![], vec![s]] {
            let r = SafeAreaTracker::default().update(1, s, s, &candidates);
            assert_eq!(r.final_luma_safe_area.ground_y(), 200.0);
            assert!(r.detected_dock_bounds.is_empty());
            assert_eq!(r.retained_safe_insets.left, 192.0);
            assert_eq!(r.retained_safe_insets.right, 192.0);
        }
    }
    #[test]
    fn auto_hide_and_metadata_loss_do_not_lower_ground() {
        let s = screen();
        let mut t = SafeAreaTracker::default();
        let dock = Area {
            x: 100.0,
            y: 0.0,
            w: 1400.0,
            h: 250.0,
        };
        let first = t.update(1, s, s, &[dock]).final_luma_safe_area;
        for candidates in [vec![], vec![s], vec![Area { h: 90.0, ..dock }]] {
            assert_eq!(t.update(1, s, s, &candidates).final_luma_safe_area, first);
        }
    }
    #[test]
    fn negative_monitor_and_monitor_change_keep_separate_history() {
        let s = screen();
        let mut t = SafeAreaTracker::default();
        t.update(
            1,
            s,
            s,
            &[Area {
                x: 100.0,
                y: 0.0,
                w: 1400.0,
                h: 250.0,
            }],
        );
        let other = Area {
            x: -1800.0,
            y: -1200.0,
            ..s
        };
        assert_eq!(
            t.update(2, other, other, &[]).final_luma_safe_area.y,
            -1008.0
        );
        assert_eq!(
            t.update(1, other, other, &[]).final_luma_safe_area.y,
            -950.0
        );
    }
    #[test]
    fn safe_ground_bounds_for_different_heights_and_drag_down() {
        let s = screen();
        let a = SafeAreaTracker::default()
            .update(1, s, s, &[])
            .final_luma_safe_area;
        for size in [
            MOA_SIZE,
            PIP_SIZE,
            Size {
                width: 140.0,
                height: 240.0,
            },
        ] {
            let (x, y) = a.clamp(-9999.0, -9999.0, size);
            let b = a.panel_bounds(x, y, size);
            assert!(b.y >= 200.0 && b.x >= 200.0);
            assert_eq!(a.ground(x, size).1, 200.0);
            assert!(b.y + b.h <= s.h - CONFIG.top_margin);
        }
    }
    #[test]
    fn actual_controller_drag_release_returns_to_safe_ground() {
        use crate::behaviors::World;
        use crate::entities::CompanionState;
        let s = screen();
        let a = SafeAreaTracker::default()
            .update(1, s, s, &[])
            .final_luma_safe_area;
        let mut world = World::new(a, 0.0, 42);
        world.spawn(0.0);
        let start = (world.view.moa.x, world.view.moa.y);
        world.drag(0.0, start);
        world.tick(0.1, 0.03, (start.0, -10000.0), true);
        assert_eq!(world.view.moa.state, CompanionState::Dragging);
        assert_eq!(world.view.moa.y, 200.0);
        world.tick(0.2, 0.03, (start.0, -10000.0), false);
        assert_eq!(world.view.moa.state, CompanionState::Idle);
        assert_eq!(world.view.moa.y, world.view.pip.as_ref().unwrap().y);
    }
}
