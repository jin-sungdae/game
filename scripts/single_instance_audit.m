#import <AppKit/AppKit.h>
// Desktop integration test, not application implementation. No activation or process-name killing.
static NSMutableArray *foregroundEvents;
static pid_t baselinePID;
static NSString *readLog(NSString *path) { return [NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:nil]?:@""; }
static NSArray *auditRows(NSString *path) {
    NSMutableArray *rows=[NSMutableArray new];
    for(NSString *line in [readLog(path) componentsSeparatedByString:@"\n"]) if([line hasPrefix:@"LUMA_AUDIT "]) {
        id row=[NSJSONSerialization JSONObjectWithData:[[line substringFromIndex:11] dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];
        if(row) [rows addObject:row];
    }
    return rows;
}
static void pump(void) {
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.01]];
    NSRunningApplication *front=NSWorkspace.sharedWorkspace.frontmostApplication;
    if(front.processIdentifier!=baselinePID && ![foregroundEvents.lastObject[@"pid"] isEqual:@(front.processIdentifier)])
        [foregroundEvents addObject:@{@"source":@"poll",@"pid":@(front.processIdentifier),@"bundle":front.bundleIdentifier?:@""}];
}
static NSUInteger windowsFor(pid_t pid) {
    if(!pid) return 0;
    NSUInteger count=0;
    NSArray *windows=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionAll,kCGNullWindowID));
    for(NSDictionary *row in windows) if([row[(id)kCGWindowOwnerPID] intValue]==pid) count++;
    return count;
}
static NSTask *launch(NSString *bundle,NSString *log,BOOL direct) {
    [[NSFileManager defaultManager] createFileAtPath:log contents:nil attributes:nil];
    NSTask *task=[NSTask new];
    if(direct) {
        task.executableURL=[NSURL fileURLWithPath:[bundle stringByAppendingPathComponent:@"Contents/MacOS/luma-spike"]];
        NSMutableDictionary *env=[NSProcessInfo.processInfo.environment mutableCopy];
        env[@"LUMA_FOCUS_AUDIT"]=@"1";env[@"LUMA_SMOKE"]=@"1";
        task.environment=env;
        NSFileHandle *handle=[NSFileHandle fileHandleForWritingAtPath:log];
        task.standardOutput=handle;task.standardError=handle;
    } else {
        task.executableURL=[NSURL fileURLWithPath:@"/usr/bin/open"];
        task.arguments=@[@"-n",@"-W",@"--stdout",log,@"--stderr",log,@"--env",@"LUMA_FOCUS_AUDIT=1",@"--env",@"LUMA_SMOKE=1",bundle];
    }
    NSError *error=nil;
    if(![task launchAndReturnError:&error]) {fprintf(stderr,"launch failed: %s\n",error.description.UTF8String);return nil;}
    return task;
}
static BOOL cleanAudit(NSArray *rows) {
    if(!rows.count) return NO;
    for(NSDictionary *row in rows) if([row[@"activations"] intValue] || [row[@"keyWindows"] intValue]) return NO;
    return YES;
}
int main(int argc,const char **argv) { @autoreleasepool {
    if(argc!=3) {fprintf(stderr,"usage: single-instance-audit APP_BUNDLE NEW_OUTPUT_DIR\n");return 2;}
    NSString *bundle=[NSURL fileURLWithPath:@(argv[1])].path,*out=[NSURL fileURLWithPath:@(argv[2])].path;
    if([[NSFileManager defaultManager] fileExistsAtPath:out]) {fprintf(stderr,"use a new output directory\n");return 2;}
    [[NSFileManager defaultManager] createDirectoryAtPath:out withIntermediateDirectories:YES attributes:nil error:nil];
    NSRunningApplication *baseline=NSWorkspace.sharedWorkspace.frontmostApplication;
    baselinePID=baseline.processIdentifier; foregroundEvents=[NSMutableArray new];
    NSNotificationCenter *center=NSWorkspace.sharedWorkspace.notificationCenter;
    id observer=[center addObserverForName:NSWorkspaceDidActivateApplicationNotification object:nil queue:nil usingBlock:^(NSNotification *note){
        NSRunningApplication *a=note.userInfo[NSWorkspaceApplicationKey];
        [foregroundEvents addObject:@{@"source":@"notification",@"pid":@(a.processIdentifier),@"bundle":a.bundleIdentifier?:@""}];
    }];
    NSString *firstPath=[out stringByAppendingPathComponent:@"primary.log"];
    NSTask *first=launch(bundle,firstPath,NO); if(!first)return 3;
    CFAbsoluteTime deadline=CFAbsoluteTimeGetCurrent()+5;
    while(first.running && ![readLog(firstPath) containsString:@"[LUMA STATE]"] && CFAbsoluteTimeGetCurrent()<deadline) pump();
    BOOL ready=[readLog(firstPath) containsString:@"[LUMA STATE]"];
    pid_t primaryPID=[auditRows(firstPath).firstObject[@"pid"] intValue];
    NSUInteger initialWindows=windowsFor(primaryPID);
    NSMutableArray *runs=[NSMutableArray new];
    if(ready) for(int i=1;i<=3;i++) {
        NSString *path=[out stringByAppendingPathComponent:[NSString stringWithFormat:@"secondary-%d.log",i]];
        NSTask *second=launch(bundle,path,i==2); if(!second)return 3;
        CFAbsoluteTime started=CFAbsoluteTimeGetCurrent();
        NSUInteger maxWindows=0;
        while(second.running && CFAbsoluteTimeGetCurrent()-started<3) {
            pump(); pid_t pid=[auditRows(path).firstObject[@"pid"] intValue];
            maxWindows=MAX(maxWindows,windowsFor(pid));
        }
        BOOL exited=!second.running;
        NSArray *audit=auditRows(path); NSString *log=readLog(path);
        BOOL pass=exited && second.terminationReason==NSTaskTerminationReasonExit && second.terminationStatus==0
            && cleanAudit(audit) && ![log containsString:@"[LUMA PANEL]"] && ![log containsString:@"[LUMA STATE]"]
            && maxWindows==0 && first.running;
        [runs addObject:@{@"number":@(i),@"mode":i==2?@"direct-bundle-executable":@"LaunchServices",@"pid":audit.firstObject[@"pid"]?:@0,
            @"seconds":@(CFAbsoluteTimeGetCurrent()-started),@"exited":@(exited),@"exitCode":exited?@(second.terminationStatus):NSNull.null,
            @"maximumObservedWindows":@(maxWindows),@"primaryStillRunning":@(first.running),@"audit":audit,@"pass":@(pass)}];
        if(!pass)break;
    }
    deadline=CFAbsoluteTimeGetCurrent()+15;
    while(first.running && CFAbsoluteTimeGetCurrent()<deadline)pump();
    [center removeObserver:observer];
    NSString *primary=readLog(firstPath);NSArray *audit=auditRows(firstPath);
    BOOL firstExited=!first.running;
    BOOL pass=ready && runs.count==3 && firstExited && first.terminationStatus==0 && cleanAudit(audit)
        && [primary containsString:@"[LUMA SMOKE] normal exit"] && [primary containsString:@"Some((Spawning"]
        && [primary containsString:@"Some((Engaged"] && [primary containsString:@"[LUMA EXIT]"]
        && [primary componentsSeparatedByString:@"[LUMA PANEL]"].count-1==3;
    for(NSDictionary *run in runs) if(![run[@"pass"] boolValue])pass=NO;
    for(NSDictionary *event in foregroundEvents) if([event[@"pid"] intValue]!=baselinePID)pass=NO;
    NSDictionary *report=@{@"baselineBundle":baseline.bundleIdentifier?:@"",@"baselinePID":@(baselinePID),@"primaryPID":@(primaryPID),
        @"primaryReady":@(ready),@"primaryInitialWindows":@(initialWindows),@"primaryAudit":audit,@"primaryExited":@(firstExited),
        @"primaryExitCode":firstExited?@(first.terminationStatus):NSNull.null,@"primaryPanelCreationCount":@([primary componentsSeparatedByString:@"[LUMA PANEL]"].count-1),
        @"secondaries":runs,@"foregroundEvents":foregroundEvents,@"pass":@(pass)};
    [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:nil] writeToFile:[out stringByAppendingPathComponent:@"report.json"] atomically:YES];
    printf("single-instance %s; secondaries=%lu; primary panels=%lu\n",pass?"PASS":"FAIL",(unsigned long)runs.count,(unsigned long)([primary componentsSeparatedByString:@"[LUMA PANEL]"].count-1));
    return pass?0:1;
} }
