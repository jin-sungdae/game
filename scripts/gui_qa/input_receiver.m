// QA-only receiver. Never injects input or changes another application's windows.
#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#include <math.h>
#include <stdlib.h>

static pid_t targetPID;
static NSWindow *receiver;
static id monitor;
static BOOL finished;
static NSUInteger receiverEvents, observedEvents;
static NSMutableDictionary<NSNumber *, NSNumber *> *gestures;
static double wallTime(void) { return NSDate.date.timeIntervalSince1970; }
static NSArray *rectArray(NSRect r) { return @[@(r.origin.x),@(r.origin.y),@(r.size.width),@(r.size.height)]; }
static void emit(NSDictionary *row) {
    NSData *data=[NSJSONSerialization dataWithJSONObject:row options:NSJSONWritingSortedKeys error:nil];
    if(data) { fwrite(data.bytes,1,data.length,stdout); fputc('\n',stdout); fflush(stdout); }
}
// Query only windows owned by the explicit target. Never serialize arbitrary titles.
static NSArray *targetWindows(void) {
    NSArray *all=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly,kCGNullWindowID));
    NSMutableArray *result=[NSMutableArray new];
    NSScreen *primary=NSScreen.screens.firstObject;
    for(NSDictionary *w in all) {
        if([w[(id)kCGWindowOwnerPID] intValue]!=targetPID) continue;
        CGRect q;
        if(!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds],&q)) continue;
        NSRect r=NSMakeRect(q.origin.x,NSMaxY(primary.frame)-q.origin.y-q.size.height,q.size.width,q.size.height);
        NSMutableDictionary *row=[@{@"id":w[(id)kCGWindowNumber],@"frame":rectArray(r),@"layer":w[(id)kCGWindowLayer]} mutableCopy];
        NSString *label=w[(id)kCGWindowName];
        if([@[@"moa",@"pip",@"interaction"] containsObject:label?:@""]) row[@"label"]=label;
        [result addObject:row];
    }
    return result;
}
static NSDictionary *observation(void) {
    return @{@"pid":@(targetPID),@"frontPid":@(NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier),@"windows":targetWindows(),@"wallTime":@(wallTime())};
}
static void input(NSEvent *event, NSString *kind, NSString *source, NSInteger windowID, pid_t pid) {
    NSPoint p;
    if([source isEqualToString:@"receiver"]) p=[receiver convertPointToScreen:event.locationInWindow];
    else {
        // CGEvent location is event-time global Quartz coordinates, not a later cursor poll.
        CGPoint q=CGEventGetLocation(event.CGEvent);
        p=NSMakePoint(q.x,NSMaxY(NSScreen.screens.firstObject.frame)-q.y);
    }
    double observedWallTime=wallTime();
    double eventWallTime=observedWallTime-(NSProcessInfo.processInfo.systemUptime-event.timestamp);
    BOOL observed=[source isEqualToString:@"luma-monitor"];
    if(observed) observedEvents++; else receiverEvents++;
    emit(@{@"type":@"input",@"kind":kind,@"source":source,@"wallTime":@(eventWallTime),@"observedWallTime":@(observedWallTime),@"uptime":@(event.timestamp),@"x":@(p.x),@"y":@(p.y),@"windowId":@(windowID),@"pid":@(pid),@"button":@(event.buttonNumber),@"observedOnly":@(observed),@"targetPid":@(observed ? CGEventGetIntegerValueField(event.CGEvent,kCGEventTargetUnixProcessID) : getpid())});
}
static void end(BOOL completed, NSString *reason) {
    if(finished) return;
    finished=YES;
    if(monitor) { [NSEvent removeMonitor:monitor]; monitor=nil; }
    emit(@{@"type":@"end",@"completed":@(completed),@"reason":reason,@"receiverEvents":@(receiverEvents),@"observedLumaEvents":@(observedEvents),@"wallTime":@(wallTime())});
    [NSApp terminate:nil];
}
@interface ReceiverView : NSView
@end
@implementation ReceiverView
- (BOOL)acceptsFirstResponder { return YES; }
- (BOOL)acceptsFirstMouse:(NSEvent *)event { return YES; }
- (void)drawRect:(NSRect)dirty { [[NSColor colorWithWhite:0.88 alpha:1] setFill]; NSRectFill(self.bounds); }
- (void)mouseDown:(NSEvent *)e { input(e,@"down",@"receiver",receiver.windowNumber,getpid()); }
- (void)mouseUp:(NSEvent *)e { input(e,@"up",@"receiver",receiver.windowNumber,getpid()); }
- (void)mouseDragged:(NSEvent *)e { input(e,@"drag",@"receiver",receiver.windowNumber,getpid()); }
- (void)rightMouseDown:(NSEvent *)e { [self mouseDown:e]; }
- (void)rightMouseUp:(NSEvent *)e { [self mouseUp:e]; }
- (void)rightMouseDragged:(NSEvent *)e { [self mouseDragged:e]; }
- (void)otherMouseDown:(NSEvent *)e { [self mouseDown:e]; }
- (void)otherMouseUp:(NSEvent *)e { [self mouseUp:e]; }
- (void)otherMouseDragged:(NSEvent *)e { [self mouseDragged:e]; }
@end
@interface ReceiverDelegate : NSObject <NSWindowDelegate>
@end
@implementation ReceiverDelegate
- (void)windowWillClose:(NSNotification *)note { end(NO,@"window-close"); }
@end
static BOOL number(const char *text, double *out) {
    char *tail=NULL; *out=strtod(text,&tail); return tail!=text && *tail=='\0' && isfinite(*out);
}
int main(int argc,const char **argv) {
    @autoreleasepool {
        BOOL observe=argc==3 && strcmp(argv[1],"observe")==0;
        double pidValue;
        if((!observe && argc!=7) || !number(argv[observe?2:1],&pidValue) || pidValue<=0 || pidValue>INT_MAX || floor(pidValue)!=pidValue) {
            fprintf(stderr,"usage: input-receiver LUMA_PID X Y WIDTH HEIGHT SECONDS | input-receiver observe PID\n"); return 2;
        }
        targetPID=(pid_t)pidValue;
        [NSApplication sharedApplication];
        if(observe) { emit(observation()); return 0; }
        double v[5];
        for(int i=0;i<5;i++) if(!number(argv[i+2],&v[i])) return 2;
        if(v[2]<=0 || v[3]<=0 || v[4]<=0 || v[4]>3600) return 2;
        [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
        receiver=[[NSWindow alloc] initWithContentRect:NSMakeRect(v[0],v[1],v[2],v[3]) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
        receiver.title=@"LUMA QA Input Receiver";
        receiver.releasedWhenClosed=NO;
        receiver.contentView=[[ReceiverView alloc] initWithFrame:NSMakeRect(0,0,v[2],v[3])];
        ReceiverDelegate *delegate=[ReceiverDelegate new]; receiver.delegate=delegate;
        gestures=[NSMutableDictionary new];
        NSEventMask mask=NSEventMaskLeftMouseDown|NSEventMaskLeftMouseUp|NSEventMaskLeftMouseDragged|NSEventMaskRightMouseDown|NSEventMaskRightMouseUp|NSEventMaskRightMouseDragged|NSEventMaskOtherMouseDown|NSEventMaskOtherMouseUp|NSEventMaskOtherMouseDragged;
        monitor=[NSEvent addGlobalMonitorForEventsMatchingMask:mask handler:^(NSEvent *e) {
            if(!e.CGEvent) return;
            if(CGEventGetIntegerValueField(e.CGEvent,kCGEventTargetUnixProcessID)!=targetPID) return;
            NSNumber *button=@(e.buttonNumber);
            BOOL down=e.type==NSEventTypeLeftMouseDown || e.type==NSEventTypeRightMouseDown || e.type==NSEventTypeOtherMouseDown;
            BOOL up=e.type==NSEventTypeLeftMouseUp || e.type==NSEventTypeRightMouseUp || e.type==NSEventTypeOtherMouseUp;
            if(down) {
                [gestures removeObjectForKey:button];
                CGPoint q=CGEventGetLocation(e.CGEvent);
                NSPoint p=NSMakePoint(q.x,NSMaxY(NSScreen.screens.firstObject.frame)-q.y);
                if(!NSPointInRect(p,[receiver convertRectToScreen:receiver.contentView.bounds])) return;
                NSInteger hit=[NSWindow windowNumberAtPoint:p belowWindowWithWindowNumber:0];
                for(NSDictionary *w in targetWindows()) if([w[@"id"] integerValue]==hit) { gestures[button]=@(hit); break; }
            }
            NSNumber *window=gestures[button];
            if(window) input(e,down?@"down":up?@"up":@"drag",@"luma-monitor",window.integerValue,targetPID);
            if(up) [gestures removeObjectForKey:button];
        }];
        [receiver orderFront:nil];
        fprintf(stderr,"Manually activate the QA receiver, then perform the requested clicks. No other application is activated automatically.\n");
        emit(@{@"type":@"ready",@"pid":@(getpid()),@"windowId":@(receiver.windowNumber),@"frame":rectArray(receiver.frame),@"wallTime":@(wallTime()),@"monitorInstalled":@(monitor!=nil)});
        [NSTimer scheduledTimerWithTimeInterval:0.1 repeats:YES block:^(NSTimer *timer) { (void)timer;
            NSMutableDictionary *row=[observation() mutableCopy]; row[@"type"]=@"heartbeat"; row[@"pid"]=@(getpid()); row[@"windowId"]=@(receiver.windowNumber); row[@"frame"]=rectArray(receiver.frame); emit(row);
        }];
        [NSTimer scheduledTimerWithTimeInterval:v[4] repeats:NO block:^(NSTimer *timer) { (void)timer; end(YES,@"timer"); }];
        [NSApp run];
        (void)delegate;
    }
    return 0;
}
