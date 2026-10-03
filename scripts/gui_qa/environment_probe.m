#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
// Read-only metadata. Never read window titles or change focus/window geometry.
static NSDictionary *rect(NSRect r) { return @{@"x":@(r.origin.x),@"y":@(r.origin.y),@"w":@(r.size.width),@"h":@(r.size.height)}; }
int main(void) { @autoreleasepool {
 NSArray *screens=NSScreen.screens; NSScreen *s=screens.firstObject;
 NSArray *visible=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly|kCGWindowListExcludeDesktopElements,kCGNullWindowID));
 NSArray *all=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionAll,kCGNullWindowID));
 NSMutableArray *obstacles=[NSMutableArray new],*owned=[NSMutableArray new],*docks=[NSMutableArray new],*displays=[NSMutableArray new];
 NSMutableSet *luma=[NSMutableSet new],*dock=[NSMutableSet new];
 for(NSRunningApplication *a in NSWorkspace.sharedWorkspace.runningApplications) {
  if([a.bundleIdentifier isEqual:@"dev.luma.spike"]) [luma addObject:@(a.processIdentifier)];
  if([a.bundleIdentifier isEqual:@"com.apple.dock"]) [dock addObject:@(a.processIdentifier)];
 }
 BOOL complete=s && visible && all;
 for(NSScreen *d in screens) [displays addObject:@{@"id":d.deviceDescription[@"NSScreenNumber"],@"frame":rect(d.frame),@"visibleFrame":rect(d.visibleFrame),@"scale":@(d.backingScaleFactor)}];
 for(NSDictionary *w in visible) {
  BOOL own=[luma containsObject:w[(id)kCGWindowOwnerPID]];
  if(!own && [w[(id)kCGWindowLayer] intValue]!=0) continue;
  CGRect r; if(!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds],&r)) {complete=NO;continue;}
  if(CGRectIsEmpty(r)) continue;
  NSDictionary *row=@{@"id":w[(id)kCGWindowNumber],@"bounds":rect(NSMakeRect(r.origin.x,NSMaxY(s.frame)-r.origin.y-r.size.height,r.size.width,r.size.height))};
  [(own?owned:obstacles) addObject:row];
 }
 for(NSDictionary *w in all) {
  if(![dock containsObject:w[(id)kCGWindowOwnerPID]] || [w[(id)kCGWindowLayer] intValue]!=CGWindowLevelForKey(kCGDockWindowLevelKey)) continue;
  CGRect r; if(!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds],&r)){complete=NO;continue;}
  [docks addObject:rect(NSMakeRect(r.origin.x,NSMaxY(s.frame)-r.origin.y-r.size.height,r.size.width,r.size.height))];
 }
 NSPoint p=NSEvent.mouseLocation;
 NSDictionary *out=@{@"version":@1,@"timestamp":@(NSDate.date.timeIntervalSince1970),@"complete":@(complete),@"screenId":s.deviceDescription[@"NSScreenNumber"]?:NSNull.null,@"frame":rect(s.frame),@"visibleFrame":rect(s.visibleFrame),@"displays":displays,@"obstacles":obstacles,@"lumaWindows":owned,@"lumaProcessCount":@(luma.count),@"docks":docks,@"cursor":@[@(p.x),@(p.y)],@"space":@{@"id":NSNull.null,@"status":@"UNAVAILABLE_PUBLIC_API"},@"screenRecording":@(CGPreflightScreenCaptureAccess()),@"accessibility":@(AXIsProcessTrusted())};
 puts([[NSString alloc]initWithData:[NSJSONSerialization dataWithJSONObject:out options:NSJSONWritingSortedKeys error:nil] encoding:NSUTF8StringEncoding].UTF8String);
 return complete?0:2;
}}
