"""Read-only eight-neighbor component and inverse-sampling diagnosis; no repair."""
import json
import math
from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path('design/production-batches/luma-asset-16/M062/move-candidate')

def main():
    spec = json.loads((ROOT/'candidate-clip.json').read_text())
    frame = Image.open(ROOT/'rigged/move/move_06.png').convert('RGBA')
    base = Image.open(spec['sourceBase']).convert('RGBA')
    remaining = {(x,y) for y in range(256) for x in range(256) if frame.getpixel((x,y))[3]}
    components = []
    while remaining:
        component = [remaining.pop()]
        pending = deque(component)
        while pending:
            x,y = pending.popleft()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    point = x+dx,y+dy
                    if point in remaining:
                        remaining.remove(point)
                        component.append(point)
                        pending.append(point)
        components.append(component)
    components.sort(key=len,reverse=True)
    rows = []
    for component in components[1:]:
        for x,y in sorted(component):
            sx,sy = x,y
            iterations = []
            for _ in range(4):
                dx=dy=0
                left,top,right,bottom=spec['movableRect']
                if left<sx<right and top<sy<bottom:
                    for p in spec['parts']:
                        r=((sx-p['x'])/p['rx'])**2+((sy-p['y'])/p['ry'])**2
                        if r<1:
                            weight=(1-r)**3*p['samples'][6]
                            dx+=p['dx']*weight
                            dy+=p['dy']*weight
                sx,sy=x-dx,y-dy
                iterations.append([sx,sy])
            x0,y0=math.floor(sx),math.floor(sy)
            fx,fy=sx-x0,sy-y0
            samples=[]
            for oy in (0,1):
                for ox in (0,1):
                    point=x0+ox,y0+oy
                    weight=(fx if ox else 1-fx)*(fy if oy else 1-fy)
                    samples.append(dict(coordinate=point,rgba=base.getpixel(point),weight=weight))
            alpha=sum(s['rgba'][3]*s['weight'] for s in samples)
            rows.append(dict(coordinate=[x,y],frameRgba=frame.getpixel((x,y)),
                baseRgba=base.getpixel((x,y)),inverseIterations=iterations,samples=samples,
                interpolatedAlpha=alpha,roundedAlpha=math.floor(alpha+.5),
                neighbors=[dict(coordinate=[x+dx,y+dy],alpha=frame.getpixel((x+dx,y+dy))[3],baseAlpha=base.getpixel((x+dx,y+dy))[3])
                    for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy]))
    print(json.dumps(dict(frame=6,componentSizes=list(map(len,components)),detached=rows,
        cause='The BASE alpha=1 pixel survives inverse bilinear resampling, while its connecting neighbors round to zero; connectivity is lost at the low-alpha boundary. No alpha threshold or pixel deletion applied.',
        status='BLOCKED_REPAIR_LIMIT; HUMAN_REVIEW_REQUIRED',repairIterations=3,repairLimit=3),indent=2))

if __name__=='__main__':
    main()
