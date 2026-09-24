#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
// QA-only executable. No application/runtime changes, no permission auto-grants.
static id attr(AXUIElementRef e,CFStringRef k){CFTypeRef v=NULL; if(AXUIElementCopyAttributeValue(e,k,&v)!=kAXErrorSuccess)return NSNull.null;return CFBridgingRelease(v);}
static NSDictionary *node(AXUIElementRef e,int depth){
 NSMutableDictionary *d=[NSMutableDictionary new];
 for(NSString *k in @[@"AXRole",@"AXSubrole",@"AXTitle",@"AXDescription",@"AXValue",@"AXFocused",@"AXEnabled"]){id v=attr(e,(__bridge CFStringRef)k);if([v isKindOfClass:NSString.class]||[v isKindOfClass:NSNumber.class])d[k]=v;}
 for(NSString*k in @[@"AXPosition",@"AXSize"]){id v=attr(e,(__bridge CFStringRef)k);if(v!=NSNull.null&&CFGetTypeID((__bridge CFTypeRef)v)==AXValueGetTypeID()){if([k isEqual:@"AXPosition"]){CGPoint p;AXValueGetValue((__bridge AXValueRef)v,kAXValueCGPointType,&p);d[k]=@[@(p.x),@(p.y)];}else{CGSize s;AXValueGetValue((__bridge AXValueRef)v,kAXValueCGSizeType,&s);d[k]=@[@(s.width),@(s.height)];}}}
 if(depth>0){id c=attr(e,kAXChildrenAttribute);if([c isKindOfClass:NSArray.class]){NSMutableArray*a=[NSMutableArray new];for(id child in c)[a addObject:node((__bridge AXUIElementRef)child,depth-1)];d[@"children"]=a;}}
 return d;
}
static NSArray *windows(pid_t pid){NSMutableArray*a=[NSMutableArray new];for(NSDictionary*d in CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly|kCGWindowListExcludeDesktopElements,kCGNullWindowID)))if([d[(id)kCGWindowOwnerPID]intValue]==pid)[a addObject:d];return a;}
static NSDictionary *snapshot(pid_t pid){NSRunningApplication*f=NSWorkspace.sharedWorkspace.frontmostApplication;AXUIElementRef ax=AXUIElementCreateApplication(f.processIdentifier);id focused=attr(ax,kAXFocusedUIElementAttribute);NSDictionary*focus=focused==NSNull.null?@{}:node((__bridge AXUIElementRef)focused,0);CFRelease(ax);return @{@"timestamp":@([[NSDate date]timeIntervalSince1970]),@"pid":@(pid),@"frontPid":@(f.processIdentifier),@"frontBundle":f.bundleIdentifier?:@"",@"focused":focus,@"windows":windows(pid)};}
static void print(id r){puts([[NSString alloc]initWithData:[NSJSONSerialization dataWithJSONObject:r options:NSJSONWritingSortedKeys error:nil] encoding:NSUTF8StringEncoding].UTF8String);fflush(stdout);}
static void mouse(CGEventType type,CGPoint p){CGEventRef e=CGEventCreateMouseEvent(NULL,type,p,(type==kCGEventRightMouseDown||type==kCGEventRightMouseUp)?kCGMouseButtonRight:kCGMouseButtonLeft);CGEventPost(kCGHIDEventTap,e);CFRelease(e);}
static BOOL press(AXUIElementRef e,NSString *label,int depth){
 if(!depth)return NO;
 id role=attr(e,kAXRoleAttribute);if([role isEqual:@"AXButton"]||[role isEqual:@"AXMenuItem"]){for(NSString *key in @[@"AXTitle",@"AXDescription"]){if([attr(e,(__bridge CFStringRef)key)isEqual:label])return AXUIElementPerformAction(e,kAXPressAction)==kAXErrorSuccess;}}
 id children=attr(e,kAXChildrenAttribute);if([children isKindOfClass:NSArray.class])for(id c in children)if(press((__bridge AXUIElementRef)c,label,depth-1))return YES;return NO;
}
int main(int argc,const char **argv){@autoreleasepool{
 if(argc<2)return 2;NSString*cmd=@(argv[1]);
 int need=[@{@"probe":@2,@"snapshot":@3,@"ax":@3,@"press":@4,@"type":@3,@"click":@4,@"right":@4,@"drag":@6,@"observe":@4}[cmd] intValue];if(!need||argc!=need)return 2;
 if([cmd isEqual:@"probe"]){NSMutableArray*a=[NSMutableArray new];for(NSScreen*s in NSScreen.screens)[a addObject:@{@"frame":NSStringFromRect(s.frame),@"visibleFrame":NSStringFromRect(s.visibleFrame),@"scale":@(s.backingScaleFactor)}];print(@{@"accessibility":@(AXIsProcessTrusted()),@"screenRecording":@(CGPreflightScreenCaptureAccess()),@"postEvent":@(CGPreflightPostEventAccess()),@"screens":a,@"reduceMotion":@(NSWorkspace.sharedWorkspace.accessibilityDisplayShouldReduceMotion)});return 0;}
 if([cmd isEqual:@"snapshot"]){print(snapshot(atoi(argv[2])));return 0;}
 if([cmd isEqual:@"ax"]){AXUIElementRef e=AXUIElementCreateApplication(atoi(argv[2]));print(node(e,12));CFRelease(e);return 0;}
 if([cmd isEqual:@"press"]){AXUIElementRef e=AXUIElementCreateApplication(atoi(argv[2]));BOOL ok=press(e,@(argv[3]),15);CFRelease(e);print(@{@"pressed":@(ok)});return ok?0:1;}
 if([cmd isEqual:@"type"]){if(!CGPreflightPostEventAccess())return 3;NSString*s=@(argv[2]);for(NSUInteger i=0;i<s.length;i++){if(![NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier isEqual:@"com.apple.TextEdit"])return 4;unichar c=[s characterAtIndex:i];CGEventRef e=CGEventCreateKeyboardEvent(NULL,c=='\n'?36:0,true);if(c!='\n')CGEventKeyboardSetUnicodeString(e,1,&c);CGEventPost(kCGHIDEventTap,e);CGEventSetType(e,kCGEventKeyUp);CGEventPost(kCGHIDEventTap,e);CFRelease(e);usleep(4000);}return 0;}
 if([cmd isEqual:@"click"]||[cmd isEqual:@"right"]||[cmd isEqual:@"drag"]){if(!CGPreflightPostEventAccess())return 3;CGPoint p=CGPointMake(atof(argv[2]),atof(argv[3]));mouse(kCGEventMouseMoved,p);mouse([cmd isEqual:@"right"]?kCGEventRightMouseDown:kCGEventLeftMouseDown,p);usleep(80000);if([cmd isEqual:@"drag"]){CGPoint end=CGPointMake(atof(argv[4]),atof(argv[5]));for(int i=1;i<=30;i++){CGPoint q=CGPointMake(p.x+(end.x-p.x)*i/30,p.y+(end.y-p.y)*i/30);mouse(kCGEventLeftMouseDragged,q);usleep(16000);}p=end;}mouse([cmd isEqual:@"right"]?kCGEventRightMouseUp:kCGEventLeftMouseUp,p);return 0;}
 if([cmd isEqual:@"observe"]){double end=NSDate.date.timeIntervalSince1970+atof(argv[3]);while(NSDate.date.timeIntervalSince1970<end){@autoreleasepool{print(snapshot(atoi(argv[2])));}usleep(50000);}return 0;}
 return 2;
}}
