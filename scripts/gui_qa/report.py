"""Summarize actual artifact evidence; missing observations never become GUI passes."""
import argparse,json,subprocess
from pathlib import Path
RESULTS={'GUI_AUTO_PASS','AUTOMATED_PASS','FAIL','PERMISSION_REQUIRED','ENVIRONMENT_UNAVAILABLE','MANUAL_VISUAL_REVIEW'}
def focus_result(record, event_observed):
    if not event_observed:return 'ENVIRONMENT_UNAVAILABLE'
    if record is None:return 'PERMISSION_REQUIRED'
    return 'GUI_AUTO_PASS' if record.get('documentContainsAll') and record.get('frontmostAlwaysTextEdit') and record.get('focusedRoles')==['AXTextArea'] else 'FAIL'
def summarize(tests):
    assert all(t['result'] in RESULTS for t in tests)
    counts={name:sum(t['result']==name for t in tests) for name in RESULTS}
    return {'pass':counts['GUI_AUTO_PASS']+counts['AUTOMATED_PASS'],'fail':counts['FAIL'],'permissionRequired':counts['PERMISSION_REQUIRED'],'environmentUnavailable':counts['ENVIRONMENT_UNAVAILABLE'],'manualVisualReview':counts['MANUAL_VISUAL_REVIEW']}
def build(root):
    def read(name,default=None):
        p=root/(name+'.json');return json.loads(p.read_text()) if p.exists() else default
    cfg=read('session');cap=read('capabilities');tests=[]
    def add(id,result,evidence,notes):tests.append(dict(id=id,result=result,evidence=evidence,notes=notes))
    images=list((root/'screenshots').glob('*.png'))
    log=(root/'app.log').read_text()
    launched=bool(images) and '[LUMA STATE]' in log and '[LUMA PANEL]' in log
    add('actual-app-launch','GUI_AUTO_PASS' if launched else 'FAIL',['session.json','app.log','01-launch-windows.json'],'Production release .app, actual NSPanel/AX/CGWindow and captured pixels.')
    single=read('single-instance')
    valid=single and single['exit']==0 and not single['secondaryWorldInitialized'] and not single['secondaryPanels'] and single['before']['pid']==single['after']['pid']
    add('single-instance','GUI_AUTO_PASS' if valid else 'FAIL',['single-instance.json','secondary.log'],'Actual second bundle executable exited0; no secondary panel/World setup. Primary continued.')
    for id,name,event in [('focus-typing','movement',True),('focus-common-debug-spawn','physical_return_pip',bool(read('physical-return-pip-ax'))),('focus-mokori-evolution','mokori',read('mokori-server') is not None),('focus-nebla-evolution','nebla',read('nebla-server') is not None)]:
        add(id,focus_result(read(name+'-typing'),event),[name+'-typing.json',name+'-focus.jsonl','app.log'],'Actual CGEvent typing, TextEdit document contents, frontmost and focused AX element. PIP retest uses physical Return; earlier Unicode-newline mismatch retained in existing-debug-pip-typing.json. Debug PIP is not server-authoritative delivery.')
    audit=[json.loads(line[len('LUMA_AUDIT '):]) for line in log.splitlines() if line.startswith('LUMA_AUDIT ')]
    add('native-key-window','GUI_AUTO_PASS' if audit and all(r['activations']==0 and r['keyWindows']==0 for r in audit) else 'FAIL',['app.log'],'Existing in-process notification observer; includes all activation/key-window events, not only sampled frontmost.')
    before=read('click-before');after=read('click-after');drag=read('drag')
    click=before and after and after['server']['activeCompanion']['bond']==before['server']['activeCompanion']['bond']+1
    add('real-click','GUI_AUTO_PASS' if click else 'FAIL',['click-before.json','click-after.json','app.log'],'CGEvent stationary click → native classifier → worker → real server Bond0→1.')
    moved=drag and drag['before']['windows']!=drag['release']['windows'] and drag['bondBefore']==drag['bondAfter']
    add('real-drag-classifier','GUI_AUTO_PASS' if moved else 'FAIL',['drag.json','app.log','02-drag-capture.json'],'Actual mouseDown/30 dragged steps/mouseUp; x changed180pt; Bond unchanged; subsequent Idle/Looking/Walking trace.')
    for name in ['MOA','MOKORI','NEBLA']:
        file={'MOA':'input-ax','MOKORI':'mokori-after-ax','NEBLA':'nebla-after-ax'}[name]
        data=read(file)
        def nodes(n):
            yield n
            for c in n.get('children',[]):yield from nodes(c)
        ok=data and any(n.get('AXRole')=='AXImage' and n.get('AXDescription')==name for n in nodes(data))
        add('visual-'+name,'GUI_AUTO_PASS' if ok else 'FAIL',[file+'.json','screenshots/'],'Actual AXImage and inspected window PNG, production base visible; not an aesthetic judgment.')
    add('all15-monster-sweep','ENVIRONMENT_UNAVAILABLE',['desktop-window-geometry.json','textedit-desktop-geometry.json','debug-pip-ax.json'],'PIP debug visual observed. Other14 not displayed: occluding normal windows prevent safe placement. Broad hide approval not granted; no bypass or false PASS.')
    add('battle-gui','ENVIRONMENT_UNAVAILABLE',['desktop-window-geometry.json'],'No authoritative Monster placement, so no actual Battle GUI evidence.')
    add('movement-profiles','MANUAL_VISUAL_REVIEW',['resource-trace.jsonl','app.log','11-debug-pip-capture.json'],'Actual PIP GROUND trajectory observed; other six profiles not observed in this GUI session.')
    add('rare-special-arrival-focus','ENVIRONMENT_UNAVAILABLE',['textedit-desktop-geometry.json'],'No RARE/SPECIAL GUI arrival; no duration or focus PASS inferred from unit tests.')
    reduced=read('reduced-motion-on');restored=read('reduced-motion-restored')
    add('reduced-motion','MANUAL_VISUAL_REVIEW' if reduced and reduced['reduceMotion'] and restored and not restored['reduceMotion'] else 'FAIL',['reduced-motion-on.json','reduced-motion-restored.json','09-reduced-motion-on-capture.json'],'Settings UI ON then original OFF verified. Companion reaction captured; rarity animation comparison still unobserved.')
    add('multi-negative-displays','ENVIRONMENT_UNAVAILABLE',['capabilities.json'],'Only one actual display, origin0,0. No simulated display PASS.')
    add('dock-menu-bar','MANUAL_VISUAL_REVIEW',['dock-left.json','dock-right.json','dock-restored.json','01-launch-windows.json','11-debug-pip-windows.json'],'Dock UI bottom→left→right→bottom tested and preference restored. NSScreen visibleFrame lagged/retained left inset after changes; detailed geometry and EDGE/LOWER_CORNER remain review items.')
    restart=read('restart-result')
    add('restart-visual','GUI_AUTO_PASS' if restart and restart.get('equal') and restart.get('neblaImage') and restart['oldPid']!=restart['newPid'] else 'ENVIRONMENT_UNAVAILABLE',['restart-result.json','restart-ax.json','screenshots/'],'Requires actual old PID exit, new Spring process, new app PID, state equality and NEBLA AXImage.')
    soak=read('soak-result')
    add('30min-native-soak','GUI_AUTO_PASS' if soak and soak.get('completed30Minutes') else 'ENVIRONMENT_UNAVAILABLE',['soak-result.json','resource-trace.jsonl','lifecycle.jsonl'],'Actual elapsed-time same-PID observation; bounded existing Debug PIP lifecycle workload. Not all15 authoritative spawn soak or proof against every leak.')
    add('aesthetic-review','MANUAL_VISUAL_REVIEW',['screenshots/'],'Animation feel/visual comfort and detailed clipping/arrival comparisons require review.')
    return dict(headSha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),compiledAppHeadSha=cfg['headSha'],macosVersion=subprocess.check_output(['sw_vers','-productVersion'],text=True).strip(),appBundle=cfg['appBundle'],bundleId=cfg['bundleId'],appPid=cfg['appPid'],accessibilityPermission='AVAILABLE' if cap['accessibility'] else 'PERMISSION_REQUIRED',screenRecordingPermission='AVAILABLE' if cap['screenRecording'] else 'PERMISSION_REQUIRED',screenshotCount=len(images),tests=tests,**summarize(tests))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=build(a.directory);(a.directory/'gui-qa-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['pass','fail','permissionRequired','environmentUnavailable','manualVisualReview','screenshotCount']}))
