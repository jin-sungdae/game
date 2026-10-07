"""Production asset gate. No third-party dependencies; no PNG generation.
Default is strict; --allow-missing permits only wholly empty frame directories.
"""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = dict(idle=6, walk=8, sit=4, look=4, sleep=6, react=6)


def png_errors(path, require_transparency=False, bounds=None):
    errors = []
    try:
        data = path.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('invalid PNG signature')
        offset, chunks, compressed = 8, [], bytearray()
        while offset < len(data):
            length = struct.unpack('>I', data[offset:offset+4])[0]
            kind = data[offset+4:offset+8]
            payload = data[offset+8:offset+8+length]
            crc = struct.unpack('>I', data[offset+8+length:offset+12+length])[0]
            if zlib.crc32(kind+payload) & 0xffffffff != crc:
                raise ValueError('PNG CRC mismatch')
            chunks.append(kind)
            if kind == b'IHDR':
                if len(chunks) != 1 or length != 13:
                    raise ValueError('invalid IHDR')
                width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
                if (width, height) != (256, 256):
                    errors.append('dimensions must be 256x256')
                if color != 6:
                    errors.append('RGBA alpha channel required (PNG color type 6)')
                if depth != 8 or compression or filtering or interlace:
                    errors.append('require 8-bit non-interlaced PNG RGBA')
            if kind == b'IDAT':
                compressed.extend(payload)
            offset += length+12
            if kind == b'IEND':
                if length or offset != len(data):
                    raise ValueError('invalid IEND/trailing data')
                break
        if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or chunks.count(b'IHDR') != 1 or not compressed:
            raise ValueError('missing/duplicate PNG chunks')
        if not errors:
            # Bound decompression to one fixed canvas, rejecting corrupt/truncated data.
            decoder = zlib.decompressobj()
            raw = decoder.decompress(compressed, 256*(256*4+1)+1)
            if len(raw) != 256*(256*4+1) or not decoder.eof or decoder.unused_data:
                raise ValueError('invalid PNG pixel data length')
            if any(raw[i] > 4 for i in range(0, len(raw), 1025)):
                raise ValueError('invalid PNG row filter')
            if require_transparency:
                previous = bytearray(1024)
                transparent = False
                ink = []
                for start in range(0, len(raw), 1025):
                    filtering = raw[start]
                    row = bytearray(raw[start+1:start+1025])
                    for i in range(1024):
                        left = row[i-4] if i >= 4 else 0
                        above = previous[i]
                        upper_left = previous[i-4] if i >= 4 else 0
                        if filtering == 1:
                            predictor = left
                        elif filtering == 2:
                            predictor = above
                        elif filtering == 3:
                            predictor = (left+above)//2
                        elif filtering == 4:
                            p = left+above-upper_left
                            distances = (abs(p-left),abs(p-above),abs(p-upper_left))
                            predictor = (left,above,upper_left)[distances.index(min(distances))]
                        else:
                            predictor = 0
                        row[i] = (row[i]+predictor) & 255
                    transparent |= any(alpha < 255 for alpha in row[3::4])
                    if bounds is not None:
                        ink.extend((x, start//1025) for x, alpha in enumerate(row[3::4]) if alpha)
                    previous = row
                if bounds is not None:
                    if not ink:
                        errors.append('empty alpha content')
                    else:
                        bounds.extend([min(x for x,y in ink), min(y for x,y in ink), max(x for x,y in ink), max(y for x,y in ink)])
                if not transparent:
                    errors.append('transparent pixels required; fully opaque RGBA is invalid')
    except (OSError, ValueError, struct.error, zlib.error) as exc:
        errors.append(str(exc))
    return errors


def validate(root=ROOT, allow_missing=False):
    errors, pending = [], []
    registry = json.loads((root/'src/entities/companions.json').read_text())
    for species, definition in registry.items():
        for stage, url in definition['stages'].items():
            manifest_path = root/'public'/url.lstrip('/')
            prefix = f'{species}/stage{int(stage):02}'
            if not manifest_path.exists() and definition.get('stageAnimationStatus', definition.get('stageAssetStatus', {})).get(stage) == 'NOT_SUPPLIED':
                (pending if allow_missing else errors).append(f'{prefix}: asset not supplied')
                continue
            try:
                m = json.loads(manifest_path.read_text())
                if (m['species'], m['stage'], m['canvas'], m['anchor']) != (species, int(stage), {'width':256,'height':256}, {'x':.5,'y':1}):
                    raise ValueError('identity/canvas/anchor mismatch')
                if type(m['display']['width']) not in (int,float) or not 0 < m['display']['width'] <= 256:
                    raise ValueError('invalid display width')
                counts=dict(COUNTS)
                if species=='moa' and int(stage)==1 and 'idleSequences' in m:
                    if m['idleSequences']!={'breath':'breath','blink':'blink','blinkIntervalMs':[3000,7000]}:raise ValueError('invalid idle sequences')
                    counts.update(breath=4,blink=3)
                if set(m['animations']) != set(counts):
                    raise ValueError('required animation keys mismatch')
                for clip, count in counts.items():
                    c = m['animations'][clip]
                    if c['frames'] != count or type(c['frameDuration']) not in (int,float) or not 0 < c['frameDuration'] < float('inf') or c['loop'] is not (clip not in ('react','blink')):
                        raise ValueError(f'{clip}: invalid frame count/timing/loop')
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f'{prefix}: manifest: {exc}')
                continue
            for clip, count in counts.items():
                directory = manifest_path.parent/clip
                if not directory.is_dir():
                    errors.append(f'{prefix}/{clip}: missing directory')
                    continue
                files = [p for p in directory.iterdir() if p.name not in ('.gitkeep', '.DS_Store')]
                expected = {f'{clip}_{i:02}.png' for i in range(count)}
                if not files and allow_missing:
                    pending.append(f'{prefix}/{clip}: {count} frames NOT_SUPPLIED')
                    continue
                names = {p.name for p in files}
                for name in sorted(expected-names):
                    errors.append(f'{prefix}/{clip}: missing frame {name}')
                for name in sorted(names-expected):
                    errors.append(f'{prefix}/{clip}: invalid filename/numbering/extension {name}')
                if len(files) != count:
                    errors.append(f'{prefix}/{clip}: frame count {len(files)}, expected {count}')
                indices = set()
                for p in files:
                    match = re.fullmatch(rf'{clip}_(\d+)\.png', p.name, re.IGNORECASE)
                    if match:
                        index = int(match[1])
                        if index in indices:
                            errors.append(f'{prefix}/{clip}: duplicate frame index {index}')
                        indices.add(index)
                    if p.suffix.lower() == '.png':
                        errors.extend(f'{prefix}/{clip}/{p.name}: {e}' for e in png_errors(p))
    pip_errors, pip_pending = validate_pip_animation(root, allow_missing)
    return errors + pip_errors, pending + pip_pending



def validate_chirp_flying(root=ROOT):
    return validate_profile_delivery(root,'CHIRP','FLYING',{'hover':(4,400),'fly':(6,90),'glide':(2,300)}, {'hover':{'frames':4,'cycle_ms':1600},'fly':{'frames':6,'frame_ms':90,'cycle_ms':540},'glide':{'frames':2,'cycle_ms':600}})

def validate_ember_free2d(root=ROOT):
    import hashlib
    errors=[];d=root/'public/assets/monsters/ember'
    try:
        source=json.loads((d/'delivery/manifest.json').read_text());m=json.loads((d/'manifest.json').read_text())
        clips={'flicker':(5,360),'flow':(6,160),'intense':(4,120)}
        expected={'species':'ember','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':True,'firstFrame':1} for n,(c,t) in clips.items()}}
        if m!=expected or source['character']!='EMBER' or source['movement_profile']!='FREE_2D' or source['canvas']!=[256,256] or source['source_facing']!='RIGHT':errors.append('EMBER metadata')
        if source['profile']!={'flicker':{'frames':5,'candidate_cycle_ms':1800},'flow':{'frames':6,'candidate_frame_ms':160,'candidate_cycle_ms':960},'intense':{'frames':4,'candidate_frame_ms':120,'candidate_cycle_ms':480,'runtime_status':'NOT_YET_APPLICABLE'}}:errors.append('EMBER timing')
        names=[f'{n}/{n}_{i:02}.png' for n,(c,t) in clips.items() for i in range(1,c+1)]
        if [f['file'] for f in source['frames']]!=names:errors.append('EMBER manifest files')
        for n,(c,t) in clips.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{n}_{i:02}.png' for i in range(1,c+1)]:errors.append('EMBER filename/count')
        centers=[]
        for f in source['frames']:
            if f['file'] not in names:errors.append('EMBER path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append('EMBER SHA')
            if len(b)!=4:errors.append('EMBER bounds');continue
            actual=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1);centers.append(actual)
            if actual!=(f['center_x'],f['center_y'],f['bottom']):errors.append('EMBER registration metadata')
        if len(centers)!=15 or any(abs(x-129.5)>3 or abs(y-138)>.5 or bottom!=252 for x,y,bottom in centers):errors.append('EMBER registration deviation')
        if source['registration']!={'max_center_x_delta_px':3,'max_center_y_delta_px':.5,'max_bottom_delta_px':0}:errors.append('EMBER registration contract')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append('EMBER FREE_2D: '+str(e))
    return errors

def validate_noct_edge(root=ROOT):
    import hashlib
    errors=[];d=root/'public/assets/monsters/noct'
    try:
        source=json.loads((d/'delivery/manifest.json').read_text());m=json.loads((d/'manifest.json').read_text())
        clips={'idle':(5,440,'idle'),'edge_move':(6,180,'edge')}
        expected={'species':'noct','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':True,'firstFrame':1,**({'filePrefix':prefix} if n!=prefix else {})} for n,(c,t,prefix) in clips.items()}}
        if m!=expected or source['batch']!='EDGE_ALPHA_NOCT_V1' or source['character']!='NOCT' or source['movement_profile']!='EDGE' or source['contract_source']!='SHADE':errors.append('NOCT metadata')
        if source['profile']!={'idle':{'frames':5,'cycle_ms':2200},'edge_move':{'frames':6,'frame_ms':180,'cycle_ms':1080,'cadence':'fixed-1x'},'turn':{'runtime_status':'NOT_APPLICABLE'}}:errors.append('NOCT timing/state')
        names=[f'{n}/{prefix}_{i:02}.png' for n,(c,t,prefix) in clips.items() for i in range(1,c+1)]
        if [f['file'] for f in source['frames']]!=names:errors.append('NOCT manifest files')
        for n,(c,t,prefix) in clips.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{prefix}_{i:02}.png' for i in range(1,c+1)]:errors.append('NOCT filename/count')
        centers=[]
        for f in source['frames']:
            if f['file'] not in names:errors.append('NOCT path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append('NOCT SHA')
            if len(b)!=4:errors.append('NOCT bounds');continue
            actual=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1);centers.append(actual)
            if actual!=(f['cx'],f['cy'],f['bottom']):errors.append('NOCT registration metadata')
        # Delivery max delta is relative to the first frame, not peak-to-peak.
        if len(centers)!=11 or any(abs(x-128)>.5 or abs(y-139.5)>.5 or bottom!=244 for x,y,bottom in centers):errors.append('NOCT registration deviation')
        if source['registration']!={'max_center_x_delta_px':.5,'max_center_y_delta_px':.5,'max_bottom_delta_px':0}:errors.append('NOCT registration contract')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append('NOCT EDGE: '+str(e))
    return errors

def validate_shade_edge(root=ROOT):
    import hashlib
    errors=[];d=root/'public/assets/monsters/shade'
    try:
        source=json.loads((d/'delivery/manifest.json').read_text());m=json.loads((d/'manifest.json').read_text())
        clips={'idle':(5,440,True,'idle'),'edge_move':(6,180,True,'edge'),'turn':(3,120,False,'turn')}
        expected={'species':'shade','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':loop,'firstFrame':1,**({'filePrefix':prefix} if n!=prefix else {})} for n,(c,t,loop,prefix) in clips.items()}}
        if m!=expected or source['character']!='SHADE' or source['movement_profile']!='EDGE' or source['canvas']!=[256,256] or source['source_facing']!='RIGHT':errors.append('SHADE metadata')
        if source['profile']!={'idle':{'frames':5,'cycle_ms':2200},'edge_move':{'frames':6,'frame_ms':180,'cycle_ms':1080},'turn':{'frames':3,'cycle_ms':360,'runtime_status':'NOT_YET_APPLICABLE'}}:errors.append('SHADE timing')
        names=[f'{n}/{prefix}_{i:02}.png' for n,(c,t,loop,prefix) in clips.items() for i in range(1,c+1)]
        if [f['file'] for f in source['frames']]!=names:errors.append('SHADE manifest files')
        for n,(c,t,loop,prefix) in clips.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{prefix}_{i:02}.png' for i in range(1,c+1)]:errors.append('SHADE filename/count')
        centers=[]
        for f in source['frames']:
            if f['file'] not in names:errors.append('SHADE path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append('SHADE SHA')
            if len(b)!=4:errors.append('SHADE bounds');continue
            actual=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1);centers.append(actual)
            if actual!=(f['center_x'],f['center_y'],f['bottom']):errors.append('SHADE registration metadata')
        if len(centers)!=14 or any(abs(x-132)>.5 or y!=136 or bottom!=243 for x,y,bottom in centers):errors.append('SHADE registration deviation')
        if source['registration']!={'max_center_x_delta_px':.5,'max_center_y_delta_px':0,'max_bottom_delta_px':0}:errors.append('SHADE registration contract')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append('SHADE EDGE: '+str(e))
    return errors

def validate_mimi_static(root=ROOT):
    import hashlib
    errors=[];d=root/'public/assets/monsters/mimi'
    try:
        source=json.loads((d/'delivery/manifest.json').read_text());m=json.loads((d/'manifest.json').read_text())
        expected={'species':'mimi','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{'idle':{'frames':5,'frameDuration':500,'loop':True,'firstFrame':1},'peek':{'frames':5,'frameDuration':120,'loop':False,'firstFrame':1}}}
        if m!=expected or source['character']!='MIMI' or source['movement_profile']!='STATIC' or source['canvas']!=[256,256] or source['anchor']!='fixed-object / visual-center': errors.append('MIMI metadata contract')
        if source['profile']!={'idle':{'frames':5,'cycle_ms':2500},'peek':{'frames':5,'frame_ms':120,'cycle_ms':600,'runtime_status':'NOT_YET_APPLICABLE'}}: errors.append('MIMI candidate timings')
        names=[f'{n}/{n}_{i:02}.png' for n in ('idle','peek') for i in range(1,6)]
        if [f['file'] for f in source['frames']]!=names: errors.append('MIMI manifest files')
        for n in ('idle','peek'):
            if sorted(p.name for p in (d/n).iterdir())!=[f'{n}_{i:02}.png' for i in range(1,6)]: errors.append('MIMI filenames')
        bounds=[]
        for f in source['frames']:
            if f['file'] not in names: errors.append('MIMI noncanonical path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b));bounds.append(b)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']: errors.append('MIMI SHA mismatch')
            if len(b)==4 and ((b[0]+b[2]+1)/2!=f['center_x'] or (b[1]+b[3]+1)/2!=f['center_y'] or b[3]+1!=f['bottom']): errors.append('MIMI registration metadata')
        if len(bounds)!=10 or any(len(b)!=4 for b in bounds) or len({tuple(b) for b in bounds})!=1: errors.append('MIMI registration drift')
    except (OSError,ValueError,KeyError,TypeError) as e: errors.append('MIMI STATIC: '+str(e))
    return errors

def validate_ground_batch(root=ROOT, code='MOSSY'):
    """Validate original batch bytes and canonical metadata; no runtime policy."""
    import hashlib
    errors=[]
    try:
        source=json.loads((root/'docs/evidence/ground-alpha-batch-v1/delivery-manifest.json').read_text())
        if code not in ('MOSSY','PEBB','TIKKI') or source['batch']!='GROUND_ALPHA_MOSSY_PEBB_TIKKI_V1' or source['profile']!='GROUND' or source['contract_source']!='PIP' or set(source['characters'])!={'MOSSY','PEBB','TIKKI'}:
            raise ValueError('batch identity')
        delivery=source['characters'][code];d=root/'public/assets/monsters'/code.lower()
        counts={'idle':(4,450),'move':(8,80)}
        expected={'species':code.lower(),'stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':True,'firstFrame':1} for n,(c,t) in counts.items()}}
        if json.loads((d/'manifest.json').read_text())!=expected:errors.append(code+' metadata contract')
        if delivery['idle']!={'frames':4,'cycle_ms':1800} or delivery['move']!={'frames':8,'frame_ms':80,'cycle_ms_at_1x':640}:errors.append(code+' timing contract')
        if delivery['registration']!={'max_center_x_delta_px':0,'max_center_y_delta_px':0,'max_bottom_delta_px':0}:errors.append(code+' registration contract')
        names=[f'{code.lower()}/{n}/{n}_{i:02}.png' for n,(c,t) in counts.items() for i in range(1,c+1)]
        if [f['file'] for f in delivery['frames']]!=names:errors.append(code+' manifest files')
        for n,(c,t) in counts.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{n}_{i:02}.png' for i in range(1,c+1)]:errors.append(code+' filenames '+n)
        measurements=[]
        for f in delivery['frames']:
            if f['file'] not in names:errors.append(code+' noncanonical path');continue
            p=root/'public/assets/monsters'/f['file'];b=[]
            errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append(code+' SHA mismatch')
            if len(b)==4:
                measured=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1)
                measurements.append(measured)
                if measured!=(f['cx'],f['cy'],f['bottom']):errors.append(code+' registration metadata')
        if len(measurements)!=12 or len(set(measurements))!=1:errors.append(code+' registration drift')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append(code+' GROUND batch: '+str(e))
    return errors


def validate_floating_batch(root=ROOT, code='WISP'):
    """Validate original batch bytes and canonical metadata; no runtime policy."""
    import hashlib
    errors=[]
    try:
        source=json.loads((root/'docs/evidence/floating-alpha-batch-v1/delivery-manifest.json').read_text())
        if code not in ('WISP','LUNET') or source['batch']!='FLOATING_ALPHA_WISP_LUNET_V1' or source['profile']!='FLOATING' or set(source['characters'])!={'WISP','LUNET'}:
            raise ValueError('batch identity')
        delivery=source['characters'][code];d=root/'public/assets/monsters'/code.lower()
        counts={'hover':(4,500),'float':(6,200)}
        expected={'species':code.lower(),'stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':True} for n,(c,t) in counts.items()}}
        if json.loads((d/'manifest.json').read_text())!=expected:errors.append(code+' metadata contract')
        if delivery['hover']!={'frames':4,'cycle_ms':2000} or delivery['float']!={'frames':6,'frame_ms':200,'cycle_ms':1200}:errors.append(code+' timing contract')
        if delivery['registration']!={'max_center_x_delta_px':0,'max_center_y_delta_px':0,'max_bottom_delta_px':0}:errors.append(code+' registration contract')
        names=[f'{code.lower()}/{n}/{n}_{i:02}.png' for n,(c,t) in counts.items() for i in range(1,c+1)]
        if [f['file'] for f in delivery['frames']]!=names:errors.append(code+' manifest files')
        for n,(c,t) in counts.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{n}_{i:02}.png' for i in range(1,c+1)]:errors.append(code+' filenames '+n)
        measurements=[]
        for f in delivery['frames']:
            if f['file'] not in names:errors.append(code+' noncanonical path');continue
            p=root/'public/assets/monsters'/f['file'];b=[]
            errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append(code+' SHA mismatch')
            if len(b)==4:
                measured=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1)
                measurements.append(measured)
                if measured!=(f['cx'],f['cy'],f['bottom']):errors.append(code+' registration metadata')
        if len(measurements)!=10 or len(set(measurements))!=1:errors.append(code+' registration drift')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append(code+' FLOATING batch: '+str(e))
    return errors


def validate_puff_floating(root=ROOT):
    return validate_profile_delivery(root,'PUFF','FLOATING',{'hover':(4,500),'float':(6,200),'settle':(2,200)}, {'hover':{'frames':4,'cycle_ms':2000},'float':{'frames':6,'frame_ms':200,'cycle_ms':1200},'settle':{'frames':2,'cycle_ms':400,'runtime_status':'NOT_YET_APPLICABLE'}},True)

def validate_profile_delivery(root, code, profile, counts, profile_contract, center_y=False):
    import hashlib
    errors=[];d=root/'public/assets/monsters'/code.lower()
    try:
        source=json.loads((d/'delivery/manifest.json').read_text());m=json.loads((d/'manifest.json').read_text())
        expected={'species':code.lower(),'stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{n:{'frames':c,'frameDuration':t,'loop':True} for n,(c,t) in counts.items()}}
        if m!=expected or source['character']!=code or source['movement_profile']!=profile or source['canvas']!=[256,256] or source['source_facing']!='RIGHT' or (not center_y and source.get('anchor')!='bottom-center'):errors.append(code+' metadata contract')
        if source['profile']!=profile_contract:errors.append(code+' candidate timings')
        names=[f'{n}/{n}_{i:02}.png' for n,(c,t) in counts.items() for i in range(1,c+1)]
        if [f['file'] for f in source['frames']]!=names:errors.append(code+' manifest files')
        for n,(c,t) in counts.items():
            if sorted(p.name for p in (d/n).iterdir())!=[f'{n}_{i:02}.png' for i in range(1,c+1)]:errors.append(code+' filenames '+n)
        bounds=[]
        for f in source['frames']:
            if f['file'] not in names:errors.append(code+' noncanonical path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b));bounds.append(b)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append(code+' SHA mismatch')
            if len(b)==4 and ((b[0]+b[2]+1)/2!=f['center_x'] or b[3]+1!=f['bottom'] or (center_y and (b[1]+b[3]+1)/2!=f['center_y'])):errors.append(code+' registration metadata')
        if len(bounds)!=12 or any(len(b)!=4 for b in bounds) or len({(b[0]+b[2],b[1]+b[3] if center_y else 0,b[3]) for b in bounds if len(b)==4})!=1:errors.append(code+' registration drift')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append(code+' FLYING: '+str(e))
    return errors

def validate_bubu_jump(root=ROOT):
    import hashlib
    errors=[];directory=root/'public/assets/monsters/bubu';d=directory/'jump'
    phases=['NEUTRAL','CROUCH','LAUNCH','ASCEND','APEX','DESCEND','LAND','SETTLE']
    slots=['NEUTRAL','CROUCH_SLOT','LAUNCH','ASCEND','APEX','DESCEND','LAND','SETTLE_SLOT']
    try:
        m=json.loads((directory/'manifest.json').read_text());source=json.loads((d/'manifest.json').read_text())
        expected={'species':'bubu','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{'jump':{'frames':8,'frameDuration':80,'loop':False}},'jumpPhases':phases}
        if m!=expected or source['batch']!='JUMP_ALPHA_BUBU_V1' or source['character']!='BUBU' or source['movement_profile']!='JUMP' or source['contract_source']!='MELLO':errors.append('BUBU metadata contract')
        if source['profile']!={'frames':8,'production_phases':phases[2:7],'not_applicable_slots':['CROUCH_SLOT','SETTLE_SLOT']}:errors.append('BUBU phase contract')
        if source['registration']!={'max_center_x_delta_px':0,'max_center_y_delta_px':0,'max_bottom_delta_px':0,'jump08_equals_jump01':True}:errors.append('BUBU registration contract')
        names=[f'jump_{i:02}.png' for i in range(1,9)]
        if sorted(p.name for p in d.iterdir())!=sorted(names+['manifest.json']):errors.append('BUBU filenames')
        if [f['file'] for f in source['frames']]!=names:errors.append('BUBU phase files')
        centers=[]
        for f,phase in zip(source['frames'],slots):
            if f['file'] not in names:errors.append('BUBU noncanonical path');continue
            p=d/f['file'];b=[];errors.extend(png_errors(p,True,b))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256'] or f['phase']!=phase:errors.append('BUBU source hash/phase')
            if len(b)==4:
                actual=((b[0]+b[2]+1)/2,(b[1]+b[3]+1)/2,b[3]+1);centers.append(actual)
                if actual!=(f['center_x'],f['center_y'],f['bottom']):errors.append('BUBU registration metadata')
        if len(centers)!=8 or len(set(centers))!=1:errors.append('BUBU registration drift')
        if (d/names[0]).read_bytes()!=(d/names[-1]).read_bytes():errors.append('BUBU neutral/settle bytes')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append('BUBU JUMP: '+str(e))
    return errors

def validate_mello_jump(root=ROOT):
    import hashlib
    errors=[];directory=root/'public/assets/monsters/mello';d=directory/'jump'
    phases=['NEUTRAL','CROUCH','LAUNCH','ASCEND','APEX','DESCEND','LAND','SETTLE']
    try:
        m=json.loads((directory/'manifest.json').read_text());source=json.loads((d/'manifest.json').read_text())
        expected={'species':'mello','stage':1,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{'jump':{'frames':8,'frameDuration':80,'loop':False}},'jumpPhases':phases}
        if m!=expected or source['character']!='MELLO' or source['movement_profile']!='JUMP' or source['phase_contract']!=phases or source['canvas']!=[256,256] or source['source_facing']!='RIGHT' or source['anchor']!='bottom-center': errors.append('MELLO JUMP metadata contract')
        names=[f'jump_{i:02}.png' for i in range(1,9)]
        if sorted(p.name for p in d.iterdir())!=sorted(names+['manifest.json']):errors.append('MELLO JUMP filenames')
        if [f['file'] for f in source['frames']]!=names:errors.append('MELLO phase files')
        bounds=[]
        for f,phase in zip(source['frames'],phases):
            p=d/f['file'];b=[];errors.extend(png_errors(p,require_transparency=True,bounds=b));bounds.append(b)
            if len(b)==4 and ((b[0]+b[2]+1)/2!=f['center_x'] or b[3]+1!=f['bottom']):errors.append('MELLO manifest registration bounds')
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256'] or f['phase']!=phase:errors.append('MELLO source hash/phase '+f['file'])
        if any(len(b)!=4 for b in bounds) or len({(b[0]+b[2],b[3]) for b in bounds if len(b)==4})!=1:errors.append('MELLO registration drift')
        if (d/names[0]).read_bytes()!=(d/names[-1]).read_bytes():errors.append('MELLO loop registration')
    except (OSError,ValueError,KeyError,TypeError) as e:errors.append('MELLO JUMP: '+str(e))
    return errors

def validate_pip_animation(root=ROOT, allow_missing=False):
    """PIP pilot delivery extends the existing PNG validator; Blink is unsupplied."""
    errors, pending = [], []
    directory = root/'public/assets/monsters/pip'
    for clip, count in [('idle',4),('walk',8),('react',6)]:
        folder = directory/clip
        if not folder.is_dir():
            (pending if allow_missing else errors).append(f'PIP/{clip}: NOT_SUPPLIED')
            continue
        files = [p for p in folder.iterdir() if p.name not in ('.gitkeep','.DS_Store')]
        if not files and allow_missing:
            pending.append(f'PIP/{clip}: NOT_SUPPLIED');continue
        expected = {f'{clip}_{i:02}.png' for i in range(count)}
        if {p.name for p in files} != expected or len(files) != count:
            errors.append(f'PIP/{clip}: filename/count/case mismatch')
        for p in files:
            errors.extend(f'PIP/{clip}/{p.name}: {e}' for e in png_errors(p,True))
    return errors,pending


def validate_bases(root=ROOT, strict=False):
    """Independent optional contract; strict delivery requires MOA and PIP only."""
    errors, pending = [], []
    companions = json.loads((root/'src/entities/companions.json').read_text())
    monsters = json.loads((root/'src/entities/monsters.json').read_text())
    paths = [(root/'public'/url.lstrip('/')).parent/'base.png'
             for definition in companions.values() for url in definition['stages'].values()]
    required = {root/'public/assets/creatures/moa/stage01/base.png'}
    for definition in monsters.values():
        if definition.get("alphaDelivery") is True and definition["baseAsset"] != "/assets/monsters/pip/base.png":
            continue  # Optional/strict alpha gate owns these deliveries, not Companion strict-base.
        path = root/'public'/definition['baseAsset'].lstrip('/')
        paths.append(path)
        if definition.get("alphaDelivery") is not True or path == root/"public/assets/monsters/pip/base.png":
            required.add(path)
    for path in paths:
        if path.name != 'base.png':
            errors.append(f'{path}: filename must be base.png')
        if path.parent.is_dir():
            for entry in path.parent.iterdir():
                if entry.stem.lower() == 'base' and entry.name != 'base.png':
                    errors.append(f'{entry}: filename must be base.png')
        if not path.is_file():
            message = f'{path.relative_to(root)}: base NOT_SUPPLIED'
            (errors if strict and path in required else pending).append(message)
        else:
            errors.extend(f'{path.relative_to(root)}: {error}' for error in png_errors(path))
    return errors, pending


ALPHA_CODES = 'pip mello mossy chirp bubu pebb puff tikki mimi wisp shade ember lunet nova noct'.split()


def validate_alpha(root=ROOT, strict=False):
    """Monster-only delivery gate; does not require Companion frames or bases."""
    errors, pending = [], []
    registry_path = root/'src/entities/monsters.json'
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate registry key: {key}')
            result[key] = value
        return result
    try:
        registry = json.loads(registry_path.read_text(), object_pairs_hook=unique)
        alpha = {code: value for code, value in registry.items() if value.get('alphaDelivery') is True}
        if set(alpha) != {code.upper() for code in ALPHA_CODES}:
            errors.append('alpha delivery must define exactly the fifteen canonical codes')
        parent = root/'public/assets/monsters'
        for slug in ALPHA_CODES:
            code = slug.upper()
            definition = registry.get(code, {})
            url = f'/assets/monsters/{slug}/base.png'
            scale = definition.get('visualScale')
            if definition.get('assetRoot') != f'/assets/monsters/{slug}' or definition.get('baseAsset') != url:
                errors.append(f'{code}: canonical asset path mismatch')
            if type(scale) not in (int, float) or not .5 <= scale <= 1.5:
                errors.append(f'{code}: visualScale must be within 0.5..1.5')
            if code == 'PIP' and scale != .8:
                errors.append('PIP: preserve legacy visualScale 0.8')
            if parent.is_dir():
                for entry in parent.iterdir():
                    if entry.name.casefold() == slug and entry.name != slug:
                        errors.append(f'{entry}: duplicate/case mismatch monster directory')
            directory = parent/slug
            entries = list(directory.iterdir()) if directory.is_dir() else []
            for entry in entries:
                # Future animation directories are independent. Every root delivery file must be canonical.
                if entry.name in ('.gitkeep', '.DS_Store', 'README.md'):
                    continue
                if entry.is_dir():
                    if entry.name.casefold().startswith('base.'):
                        errors.append(f'{entry}: base must be a regular PNG file')
                    continue
                if code in ('MOSSY', 'PEBB', 'TIKKI') and entry.name == 'manifest.json':
                    errors.extend(validate_ground_batch(root, code))
                    continue
                if code in ('WISP', 'LUNET') and entry.name == 'manifest.json':
                    errors.extend(validate_floating_batch(root, code))
                    continue
                if code == 'EMBER' and entry.name == 'manifest.json':
                    errors.extend(validate_ember_free2d(root))
                    continue
                if code == 'NOCT' and entry.name == 'manifest.json':
                    errors.extend(validate_noct_edge(root))
                    continue
                if code == 'SHADE' and entry.name == 'manifest.json':
                    errors.extend(validate_shade_edge(root))
                    continue
                if code == 'MIMI' and entry.name == 'manifest.json':
                    errors.extend(validate_mimi_static(root))
                    continue
                if code == 'PUFF' and entry.name == 'manifest.json':
                    errors.extend(validate_puff_floating(root))
                    continue
                if code == 'CHIRP' and entry.name == 'manifest.json':
                    errors.extend(validate_chirp_flying(root))
                    continue
                if code == 'BUBU' and entry.name == 'manifest.json':
                    errors.extend(validate_bubu_jump(root))
                    continue
                if code == 'MELLO' and entry.name == 'manifest.json':
                    errors.extend(validate_mello_jump(root))
                    continue
                if code == 'PIP' and entry.name == 'manifest.json':
                    try:
                        m = json.loads(entry.read_text())
                        expected = {'species':'pip','stage':1,'canvas':{'width':256,'height':256},
                            'anchor':{'x':.5,'y':1},'display':{'width':82},'animations':{
                                'idle':{'frames':4,'frameDuration':450,'loop':True},
                                'walk':{'frames':8,'frameDuration':80,'loop':True},
                                'react':{'frames':6,'frameDuration':80,'loop':False}}}
                        if m != expected:
                            errors.append(f'{entry}: invalid PIP pilot animation contract')
                    except (OSError, ValueError) as exc:
                        errors.append(f'{entry}: invalid PIP pilot manifest: {exc}')
                    continue
                if entry.name != 'base.png':
                    errors.append(f'{entry}: invalid filename/duplicate/case mismatch; expected base.png')
            canonical = next((entry for entry in entries if entry.name == 'base.png' and entry.is_file()), None)
            if canonical is None:
                (errors if strict else pending).append(f'{url}: alpha base NOT_SUPPLIED')
            else:
                errors.extend(f'{url}: {error}' for error in png_errors(canonical, require_transparency=True))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors.append(f'alpha registry: {exc}')
    return errors, pending


def validate_release(root=ROOT):
    """Required Alpha bases only; optional animation remains the existing allow-missing gate."""
    errors, _ = validate_alpha(root, strict=True)
    registry = json.loads((root/'src/entities/companions.json').read_text())
    rows = []
    required = []
    for stage, name in [(1, 'MOA'), (2, 'MOKORI'), (3, 'NEBLA')]:
        url = f'/assets/creatures/moa/stage{stage:02}/base.png'
        moa = registry.get('moa', {})
        if moa.get('stages', {}).get(str(stage)) != url.replace('base.png', 'manifest.json') or moa.get('stageNames', {}).get(str(stage), moa.get('name')) != name:
            errors.append(f'{name}: companion registry identity mismatch')
        required.append((name, url))
    required.extend((code.upper(), f'/assets/monsters/{code}/base.png') for code in ALPHA_CODES)
    for name, url in required:
        bounds = []
        failures = png_errors(root/'public'/url.lstrip('/'), True, bounds)
        errors.extend(f'{name}: {e}' for e in failures)
        rows.append({'identity': name, 'url': url, 'bounds': bounds, 'status': 'FAIL' if failures else 'PASS'})
    return errors, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', action='store_true', help='audit all eighteen required production bases')
    parser.add_argument('--allow-missing', action='store_true')
    parser.add_argument('--strict-base', action='store_true', help='require MOA and PIP base delivery; frame policy unchanged')
    parser.add_argument('--strict-alpha', action='store_true', help='require all fifteen Monster bases; independent of Companion delivery')
    parser.add_argument('--alpha-only', action='store_true', help='validate only optional Alpha Monster delivery')
    parser.add_argument('--root', type=Path, default=ROOT, help='repository/delivery staging root')
    args = parser.parse_args()
    if args.release:
        failures, rows = validate_release(args.root)
        print(json.dumps({'requiredBases': rows, 'errors': failures}, indent=2))
        raise SystemExit(bool(failures))
    failures, pending = validate_alpha(args.root, strict=args.strict_alpha)
    if not (args.alpha_only or args.strict_alpha):
        frame_failures, frame_pending = validate(args.root, allow_missing=args.allow_missing)
        base_failures, base_pending = validate_bases(args.root, strict=args.strict_base)
        failures.extend(frame_failures + base_failures)
        pending.extend(frame_pending + base_pending)
    for line in failures:
        print('FAIL:', line)
    for line in pending:
        print('PENDING:', line)
    print(f'{len(failures)} errors; {len(pending)} unprovided assets')
    raise SystemExit(bool(failures))
