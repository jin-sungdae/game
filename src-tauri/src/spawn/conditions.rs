//! Desktop local calendar time is independent of monotonic cooldowns and UTC server leases.
use chrono::{DateTime, FixedOffset, Local, NaiveTime, Timelike};
pub trait CalendarClock: Send {
    fn local_now(&self) -> DateTime<FixedOffset>;
}
pub struct LocalClock;
impl CalendarClock for LocalClock {
    fn local_now(&self) -> DateTime<FixedOffset> {
        Local::now().fixed_offset()
    }
}
pub fn night(time: NaiveTime) -> bool {
    time.hour() >= 22 || time.hour() < 6
}
