"""Normalize actual AX observations without inventing unavailable native telemetry."""
import json
import math
import re

FIELDS = ('timestamp','entityId','entityType','world','vx','vy','speed','movementState','animationState','animationFrame','nativeFacing','rendererFlip','panelBounds','canvasBounds','displayId')


def number(v):
    return v if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) else None


def normalize(raw, profile, environment):
    if not isinstance(raw.get('label'),str): return None
    m=re.fullmatch(re.escape(profile['label'])+r' (\w+) frame (\d+) (animation|base)(?: trace (.*))?',raw.get('label',''))
    if not m: return None
    t=number(raw.get('after')); start=number(raw.get('before'))
    if t is None or start is None or t<start: return None
    telemetry={}
    if m[4]:
        try: telemetry=json.loads(m[4]) or {}
        except ValueError: pass
    if not isinstance(telemetry,dict): telemetry={}
    panels=raw.get('panels',[]); panel=panels[0] if len(panels)==1 else None
    image=raw.get('image',{}); pos=image.get('AXPosition'); size=image.get('AXSize')
    canvas={'x':pos[0],'y':pos[1],'w':size[0],'h':size[1]} if pos and size else None
    b={k:panel[n] for k,n in [('x','X'),('y','Y'),('w','Width'),('h','Height')]} if panel else None
    vx=number(telemetry.get('vx')); vy=number(telemetry.get('vy'))
    # Native telemetry is used only when actually exposed, never inferred from rounded panels.
    return dict(version=1,timestamp=(t+start)/2,observationDuration=t-start,
        entityId=profile['entityId'],entityType=profile['entityType'],
        world={'x':telemetry['x'],'y':telemetry['y']} if number(telemetry.get('x')) is not None and number(telemetry.get('y')) is not None else None,vx=vx,vy=vy,
        speed=number(telemetry.get('speed')),movementState=telemetry.get('state'),
        excursionActive=telemetry.get('active'),animationState=m[1],animationFrame=int(m[2]),
        nativeFacing=number(telemetry.get('facing')),rendererFlip=number(telemetry.get('rendererFlip')),
        panelBounds=b,canvasBounds=canvas,displayId=environment['screenId'],source=m[3],
        missingNativeFields=[k for k in ('world','vx','vy','speed','movementState','nativeFacing') if (k=='world' and (number(telemetry.get('x')) is None or number(telemetry.get('y')) is None)) or (k!='world' and telemetry.get({'movementState':'state','nativeFacing':'facing'}.get(k,k)) is None)])
