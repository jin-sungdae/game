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
void luma_work_area(double *x, double *y, double *width, double *height) {
    NSScreen *screen = NSScreen.screens.firstObject;
    NSRect r = screen.visibleFrame;
    *x=r.origin.x; *y=r.origin.y; *width=r.size.width; *height=r.size.height;
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
