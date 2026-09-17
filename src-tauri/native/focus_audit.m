#import <AppKit/AppKit.h>

// Opt-in diagnostics, installed before Tauri constructs NSApplication/event loop.
// Notification observation only: no activation, key capture, or event injection.
static NSMutableArray *observers;
static unsigned activeCount, keyCount;
static CFAbsoluteTime started;
static void record(NSString *event) {
    NSRunningApplication *front = NSWorkspace.sharedWorkspace.frontmostApplication;
    NSDictionary *row = @{@"event":event, @"seconds":@(CFAbsoluteTimeGetCurrent()-started),
        @"pid":@(getpid()), @"frontPid":@(front.processIdentifier),
        @"frontBundle":front.bundleIdentifier ?: @"", @"activations":@(activeCount), @"keyWindows":@(keyCount)};
    NSData *json = [NSJSONSerialization dataWithJSONObject:row options:NSJSONWritingSortedKeys error:nil];
    fprintf(stderr,"LUMA_AUDIT %s\n",[[[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding] UTF8String]);
    fflush(stderr);
}
void luma_focus_audit_start(void) {
    if (!getenv("LUMA_FOCUS_AUDIT")) return;
    started=CFAbsoluteTimeGetCurrent();
    observers=[NSMutableArray new];
    NSNotificationCenter *center=NSNotificationCenter.defaultCenter;
    [observers addObject:[center addObserverForName:NSApplicationDidBecomeActiveNotification object:nil queue:nil usingBlock:^(NSNotification *note) {(void)note; activeCount++; record(@"app-active");}]];
    [observers addObject:[center addObserverForName:NSWindowDidBecomeKeyNotification object:nil queue:nil usingBlock:^(NSNotification *note) {(void)note; keyCount++; record(@"key-window");}]];
    record(@"before-tauri");
    const char *timeout=getenv("LUMA_AUDIT_EXIT_SECONDS");
    if (timeout) {
        double seconds=atof(timeout);
        if (seconds>=1 && seconds<=600) dispatch_after(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(seconds*NSEC_PER_SEC)),dispatch_get_main_queue(),^{[NSApp terminate:nil];});
    }
}
void luma_focus_audit_end(void) {
    if (!observers) return;
    record(@"exit");
    for (id observer in observers) [NSNotificationCenter.defaultCenter removeObserver:observer];
    observers=nil;
}
