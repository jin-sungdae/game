#import <AppKit/AppKit.h>

// Real NSPanel instances; no runtime class replacement or focus restoration.
@interface LumaPanel : NSPanel
@end
@implementation LumaPanel
- (BOOL)canBecomeKeyWindow { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }
@end
static NSMutableDictionary<NSNumber *, LumaPanel *> *panels;
static NSStatusItem *statusItem;
static int pendingAction;
@interface LumaMenu : NSObject
- (void)spawn:(id)sender;
- (void)despawn:(id)sender;
- (void)quit:(id)sender;
@end
@implementation LumaMenu
- (void)spawn:(id)sender { pendingAction = 1; }
- (void)despawn:(id)sender { pendingAction = 2; }
- (void)quit:(id)sender { pendingAction = 3; }
@end
static LumaMenu *menuTarget;
void luma_init(void) {
    panels = [NSMutableDictionary new];
    menuTarget = [LumaMenu new];
    statusItem = [NSStatusBar.systemStatusBar statusItemWithLength:NSVariableStatusItemLength];
    statusItem.button.title = @"LUMA";
    NSMenu *menu = [NSMenu new];
    NSArray *titles = @[@"Spawn PIP", @"Despawn PIP", @"Quit LUMA"];
    SEL actions[] = {@selector(spawn:), @selector(despawn:), @selector(quit:)};
    for (NSUInteger i=0; i<3; i++) {
        NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:titles[i] action:actions[i] keyEquivalent:@""];
        item.target = menuTarget; [menu addItem:item];
    }
    statusItem.menu = menu;
}
void luma_attach(void *window, int index, double width, double height) {
    NSWindow *host = (__bridge NSWindow *)window;
    LumaPanel *panel = [[LumaPanel alloc] initWithContentRect:NSMakeRect(0,0,width,height)
        styleMask:NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        backing:NSBackingStoreBuffered defer:NO];
    panel.title = host.title;
    panel.opaque = NO;
    panel.backgroundColor = NSColor.clearColor;
    panel.hasShadow = NO;
    panel.level = NSFloatingWindowLevel;
    panel.hidesOnDeactivate = NO;
    panel.becomesKeyOnlyIfNeeded = YES;
    panel.releasedWhenClosed = NO;
    panel.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary;
    // The hidden Tauri host retains the webview lifecycle; panel owns its view hierarchy.
    NSView *content = host.contentView;
    host.contentView = nil;
    panel.contentView = content;
    [host orderOut:nil];
    panels[@(index)] = panel;
    NSLog(@"[LUMA PANEL] %@ opaque=%d level=%ld keyAllowed=%d mainAllowed=%d", panel.title, panel.opaque, (long)panel.level, panel.canBecomeKeyWindow, panel.canBecomeMainWindow);
}
// Use AppKit bottom-left point coordinates end-to-end: no Retina conversion.
typedef struct { double x,y,w,h; } DesktopRect;
typedef struct { double bottom,left,right,top; } SafeInsets;
static NSDictionary *safeAreaSnapshot;
static NSArray *dockWindowCandidates;
static DesktopRect desktopRect(NSRect r) { return (DesktopRect){r.origin.x,r.origin.y,r.size.width,r.size.height}; }
static NSRect nsRect(DesktopRect r) { return NSMakeRect(r.x,r.y,r.w,r.h); }
static NSDictionary *rectJSON(NSRect r);
// Public metadata only. No window titles, images, screen-recording request or AX API.
void luma_desktop(DesktopRect *frame, DesktopRect *visible, DesktopRect *docks, int *count, unsigned *screenID) {
    NSScreen *screen=NSScreen.screens.firstObject;
    *frame=desktopRect(screen.frame); *visible=desktopRect(screen.visibleFrame);
    *screenID=[screen.deviceDescription[@"NSScreenNumber"] unsignedIntValue];
    int capacity=*count; *count=0;
    NSMutableArray *raw=[NSMutableArray new];
    NSArray *dockApps=[NSRunningApplication runningApplicationsWithBundleIdentifier:@"com.apple.dock"];
    NSArray *windows=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionAll,kCGNullWindowID));
    for(NSDictionary *w in windows) {
        if([w[(id)kCGWindowLayer] intValue]!=CGWindowLevelForKey(kCGDockWindowLevelKey)) continue;
        BOOL dockOwner=NO;
        for(NSRunningApplication *app in dockApps) if(app.processIdentifier==[w[(id)kCGWindowOwnerPID] intValue]) {dockOwner=YES;break;}
        if(!dockOwner || *count>=capacity) continue;
        CGRect r;
        if(!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds],&r)) continue;
        // Quartz global top-left points -> AppKit global bottom-left points.
        NSRect converted=NSMakeRect(r.origin.x,NSMaxY(screen.frame)-r.origin.y-r.size.height,r.size.width,r.size.height);
        docks[(*count)++]=desktopRect(converted);
        [raw addObject:rectJSON(converted)];
    }
    dockWindowCandidates=raw;
}
static NSDictionary *insetsJSON(SafeInsets i) {
    return @{@"bottom":@(i.bottom),@"left":@(i.left),@"right":@(i.right),@"top":@(i.top)};
}
void luma_set_safe_area(const DesktopRect *safe,const DesktopRect *docks,int count,const SafeInsets *fallback,const SafeInsets *retained,int rejected) {
    NSMutableArray *detected=[NSMutableArray new];
    for(int i=0;i<count;i++) [detected addObject:rectJSON(nsRect(docks[i]))];
    safeAreaSnapshot=@{@"finalLumaSafeArea":rectJSON(nsRect(*safe)),@"detectedDockBounds":detected,
        @"fallbackSafeInsets":insetsJSON(*fallback),@"retainedSafeInsets":insetsJSON(*retained),
        @"rejectedDockCandidates":@(rejected),@"dockWindowCandidates":dockWindowCandidates?:@[],
        @"dockBoundsStatus":count>0?@"EDGE_CANDIDATE":@"FALLBACK_UNVERIFIED",@"visualVerification":@"MANUAL_REQUIRED"};
}
// Read-only movement exclusion rectangles. Never activate/focus or request permissions.
void luma_movement_windows(DesktopRect *out, int *count) {
    int capacity=*count; *count=0;
    NSScreen *screen=NSScreen.screens.firstObject;
    NSArray *windows=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly|kCGWindowListExcludeDesktopElements,kCGNullWindowID));
    if(!screen || !windows) { *count=-1; return; }
    for(NSDictionary *w in windows) {
        if([w[(id)kCGWindowOwnerPID] intValue]==NSProcessInfo.processInfo.processIdentifier) continue;
        if([w[(id)kCGWindowLayer] intValue]!=0) continue;
        CGRect r;
        if(!w[(id)kCGWindowBounds] || !CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds],&r) || *count>=capacity) { *count=-1; return; }
        if(CGRectIsEmpty(r)) continue;
        out[(*count)++]=(DesktopRect){r.origin.x,NSMaxY(screen.frame)-r.origin.y-r.size.height,r.size.width,r.size.height};
    }
}
void luma_cursor(double *x, double *y, int *down) {
    NSPoint p=NSEvent.mouseLocation; *x=p.x; *y=p.y;
    *down=(NSEvent.pressedMouseButtons & 1) != 0;
}
void luma_place(int index, double x, double y, int visible) {
    LumaPanel *panel=panels[@(index)];
    if (!visible) { if(panel.visible) [panel orderOut:nil]; return; }
    NSPoint origin=panel.frame.origin;
    if(origin.x != x || origin.y != y) [panel setFrameOrigin:NSMakePoint(x,y)];
    if(!panel.visible) [panel orderFrontRegardless];
}
int luma_action(void) { int action=pendingAction; pendingAction=0; return action; }
int luma_is_active(void) { return NSApp.active; }
void luma_cleanup(void) {
    for (LumaPanel *panel in panels.allValues) [panel close];
    [panels removeAllObjects];
    [NSStatusBar.systemStatusBar removeStatusItem:statusItem];
    statusItem=nil;
}

// Opt-in measurements only; no activation or event taps. At most one row/sec/entity.
static NSDictionary *rectJSON(NSRect r) {
    return @{ @"x":@(r.origin.x), @"y":@(r.origin.y), @"w":@(r.size.width), @"h":@(r.size.height) };
}
void luma_trace_geometry(int index, double x, double y, double ground, double width, double height,
                         double margin, double groundMargin, double topMargin, double panelX, double panelY, int visible) {
    static int enabled = -1;
    static double last[2] = {-1,-1};
    if(enabled < 0) enabled = getenv("LUMA_GEOMETRY_AUDIT") != NULL;
    if(!enabled || index < 0 || index > 1) return;
    double now = NSProcessInfo.processInfo.systemUptime;
    if(now-last[index] < 1.0) return;
    last[index]=now;
    NSScreen *screen=NSScreen.screens.firstObject;
    NSDictionary *safe=safeAreaSnapshot[@"finalLumaSafeArea"];
    NSRect usable=NSMakeRect([safe[@"x"] doubleValue],[safe[@"y"] doubleValue],[safe[@"w"] doubleValue],[safe[@"h"] doubleValue]);
    NSRect actual=panels[@(index)].frame;
    NSRect expected=NSMakeRect(panelX,panelY,width,height);
    BOOL contained=NSMinX(actual)>=NSMinX(usable)+margin && NSMaxX(actual)<=NSMaxX(usable)-margin
        && NSMinY(actual)>=NSMinY(usable)+groundMargin && NSMaxY(actual)<=NSMaxY(usable)-topMargin;
    NSMutableDictionary *row=[@{@"entity":index==0?@"MOA":@"PIP", @"pid":@(getpid()), @"uptime":@(now),
        @"screenFrame":rectJSON(screen.frame), @"visibleFrame":rectJSON(screen.visibleFrame),
        @"computedGroundLine":@(ground), @"world":@{@"x":@(x),@"y":@(y)},
        @"panelFrame":rectJSON(actual), @"expectedPanelFrame":rectJSON(expected),
        @"visible":@(visible), @"fitsUsableBounds":@(contained),
        @"reservedIntersectionArea":@(MAX(0.0,actual.size.width*actual.size.height-NSIntersectionRect(actual,usable).size.width*NSIntersectionRect(actual,usable).size.height)),
        @"matchesWorldBounds":@(NSEqualRects(actual,expected))} mutableCopy];
    [row addEntriesFromDictionary:safeAreaSnapshot];
    double overlap=0;
    for(NSDictionary *d in safeAreaSnapshot[@"detectedDockBounds"]) {
        NSRect dock=NSMakeRect([d[@"x"] doubleValue],[d[@"y"] doubleValue],[d[@"w"] doubleValue],[d[@"h"] doubleValue]);
        NSRect intersection=NSIntersectionRect(actual,dock); overlap+=intersection.size.width*intersection.size.height;
    }
    row[@"detectedDockIntersectionArea"]=[safeAreaSnapshot[@"detectedDockBounds"] count]>0?@(overlap):NSNull.null;
    NSData *data=[NSJSONSerialization dataWithJSONObject:row options:NSJSONWritingSortedKeys error:nil];
    fprintf(stderr,"LUMA_GEOMETRY %s\n",[[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] UTF8String]);
}
