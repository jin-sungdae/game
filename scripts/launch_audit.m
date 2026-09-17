#import <AppKit/AppKit.h>

// Read-only foreground observer + child-process launcher. Never activates any app.
// Usage: launch-audit BINARY COUNT SECONDS OUTPUT_DIR EXPECTED_BUNDLE_ID
static void pump(double seconds) {
    NSDate *until=[NSDate dateWithTimeIntervalSinceNow:seconds];
    while (until.timeIntervalSinceNow>0) [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:MIN(0.01,until.timeIntervalSinceNow)]];
}
int main(int argc,const char **argv) { @autoreleasepool {
    if(argc!=6 && argc!=7) {fprintf(stderr,"usage: launch-audit BINARY COUNT SECONDS OUTPUT_DIR EXPECTED_BUNDLE_ID [smoke]\n");return 2;}
    NSString *binary=[NSURL fileURLWithPath:@(argv[1])].path, *directory=[NSURL fileURLWithPath:@(argv[4])].path, *expected=@(argv[5]);
    BOOL smoke=argc==7 && [@(argv[6]) isEqualToString:@"smoke"];
    if(argc==7 && !smoke) return 2;
    int count=atoi(argv[2]);double duration=atof(argv[3]);
    if(count<1||count>100||duration<2||duration>600) return 2;
    [[NSFileManager defaultManager] createDirectoryAtPath:directory withIntermediateDirectories:YES attributes:nil error:nil];
    NSMutableArray *runs=[NSMutableArray new];
    // Wait for user preparation; never bring the target application forward.
    CFAbsoluteTime deadline=CFAbsoluteTimeGetCurrent()+120;
    while (![NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier isEqualToString:expected] && CFAbsoluteTimeGetCurrent()<deadline) {
        fprintf(stderr,"WAIT: foreground=%s expected=%s\n", (NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier?:@"unknown").UTF8String, expected.UTF8String);
        pump(5);
    }
    for(int i=1;i<=count;i++) { @autoreleasepool {
        NSRunningApplication *baseline=NSWorkspace.sharedWorkspace.frontmostApplication;
        if(![baseline.bundleIdentifier isEqualToString:expected]) {
            fprintf(stderr,"ABORT: expected foreground %s, found %s; no focus restoration attempted\n",expected.UTF8String,(baseline.bundleIdentifier?:@"").UTF8String);return 3;
        }
        pid_t baselinePid=baseline.processIdentifier;
        NSMutableArray *events=[NSMutableArray new];
        CFAbsoluteTime start=CFAbsoluteTimeGetCurrent();
        NSNotificationCenter *center=NSWorkspace.sharedWorkspace.notificationCenter;
        id observer=[center addObserverForName:NSWorkspaceDidActivateApplicationNotification object:nil queue:nil usingBlock:^(NSNotification *note) {
            NSRunningApplication *app=note.userInfo[NSWorkspaceApplicationKey];
            [events addObject:@{@"source":@"notification",@"seconds":@(CFAbsoluteTimeGetCurrent()-start),@"pid":@(app.processIdentifier),@"bundle":app.bundleIdentifier?:@""}];
        }];
        NSString *logPath=[directory stringByAppendingPathComponent:[NSString stringWithFormat:@"launch-%02d.log",i]];
        [[NSFileManager defaultManager] createFileAtPath:logPath contents:nil attributes:nil];
        NSFileHandle *log=[NSFileHandle fileHandleForWritingAtPath:logPath];
        NSTask *task=[NSTask new];
        BOOL bundle=[binary.pathExtension isEqualToString:@"app"];
        task.executableURL=[NSURL fileURLWithPath:bundle?@"/usr/bin/open":binary];
        if(bundle) task.arguments=@[@"-n",@"-W",@"--stdout",logPath,@"--stderr",logPath,
            @"--env",@"LUMA_FOCUS_AUDIT=1",@"--env",[NSString stringWithFormat:@"LUMA_AUDIT_EXIT_SECONDS=%.2f",duration],binary];
        if(bundle && smoke) {
            NSMutableArray *args=[task.arguments mutableCopy];
            [args insertObjects:@[@"--env",@"LUMA_SMOKE=1"] atIndexes:[NSIndexSet indexSetWithIndexesInRange:NSMakeRange(args.count-1,2)]];
            task.arguments=args;
        }
        NSMutableDictionary *env=[NSProcessInfo.processInfo.environment mutableCopy];
        env[@"LUMA_FOCUS_AUDIT"]=@"1";env[@"LUMA_AUDIT_EXIT_SECONDS"]=[NSString stringWithFormat:@"%.2f",duration];
        [env removeObjectForKey:@"LUMA_SMOKE"];
        if(smoke) env[@"LUMA_SMOKE"]=@"1";
        task.environment=env;task.standardOutput=log;task.standardError=log;
        NSError *error=nil;
        if(![task launchAndReturnError:&error]) {fprintf(stderr,"launch failed: %s\n",error.description.UTF8String);return 4;}
        pid_t child=task.processIdentifier, last=baselinePid;
        BOOL timedOut=NO;
        while(task.running) {
            pump(.01);
            NSRunningApplication *front=NSWorkspace.sharedWorkspace.frontmostApplication;
            if(front.processIdentifier!=last) {
                last=front.processIdentifier;
                [events addObject:@{@"source":@"poll-10ms",@"seconds":@(CFAbsoluteTimeGetCurrent()-start),@"pid":@(last),@"bundle":front.bundleIdentifier?:@""}];
            }
            if(CFAbsoluteTimeGetCurrent()-start>duration+15) {timedOut=YES;[task terminate];break;}
        }
        pump(.2);[center removeObserver:observer];[log closeFile];
        NSString *text=[NSString stringWithContentsOfFile:logPath encoding:NSUTF8StringEncoding error:nil]?:@"";
        NSMutableArray *internal=[NSMutableArray new];unsigned activations=0, keys=0;BOOL exitSeen=NO;pid_t lumaPid=0;
        for(NSString *line in [text componentsSeparatedByString:@"\n"]) if([line hasPrefix:@"LUMA_AUDIT "]) {
            NSDictionary *row=[NSJSONSerialization JSONObjectWithData:[[line substringFromIndex:11] dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];
            if(row) {lumaPid=[row[@"pid"] intValue];[internal addObject:row];activations=MAX(activations,[row[@"activations"] unsignedIntValue]);keys=MAX(keys,[row[@"keyWindows"] unsignedIntValue]);if([row[@"event"] isEqual:@"exit"]) exitSeen=YES;}
        }
        BOOL changed=NO;for(NSDictionary *event in events) if([event[@"pid"] intValue]!=baselinePid) changed=YES;
        BOOL ready=[text containsString:@"[LUMA STATE]"];
        BOOL pass=!timedOut&&task.terminationReason==NSTaskTerminationReasonExit&&task.terminationStatus==0&&ready&&exitSeen&&!changed&&activations==0&&keys==0;
        NSDictionary *result=@{@"run":@(i),@"baselinePid":@(baselinePid),@"baselineBundle":expected,@"launcherPid":@(child),@"lumaPid":@(lumaPid),@"launchServices":@(bundle),@"events":events,@"internal":internal,@"appActivations":@(activations),@"keyWindows":@(keys),@"foregroundChanged":@(changed),@"ready":@(ready),@"exitSeen":@(exitSeen),@"exitCode":@(task.terminationStatus),@"terminationReason":@(task.terminationReason),@"timedOut":@(timedOut),@"pass":@(pass)};
        [runs addObject:result];
        NSDictionary *report=@{@"binary":binary,@"mode":smoke?@"existing-smoke":@"normal",@"requestedRuns":@(count),@"secondsPerRun":@(duration),@"expectedBundle":expected,@"runs":runs};
        [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:nil] writeToFile:[directory stringByAppendingPathComponent:@"report.json"] atomically:YES];
        printf("run %02d/%02d %s activations=%u keyWindows=%u changed=%d\n",i,count,pass?"PASS":"FAIL",activations,keys,changed);fflush(stdout);
        if(!pass) return 1; // Fail closed; never silently restore baseline or retry a failed run.
    }}
    return 0;
}}
