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


def png_errors(path, require_transparency=False):
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
                    previous = row
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
            try:
                m = json.loads(manifest_path.read_text())
                if (m['species'], m['stage'], m['canvas'], m['anchor']) != (species, int(stage), {'width':256,'height':256}, {'x':.5,'y':1}):
                    raise ValueError('identity/canvas/anchor mismatch')
                if type(m['display']['width']) not in (int,float) or not 0 < m['display']['width'] <= 256:
                    raise ValueError('invalid display width')
                if set(m['animations']) != set(COUNTS):
                    raise ValueError('required animation keys mismatch')
                for clip, count in COUNTS.items():
                    c = m['animations'][clip]
                    if c['frames'] != count or type(c['frameDuration']) not in (int,float) or not 0 < c['frameDuration'] < float('inf') or c['loop'] is not (clip != 'react'):
                        raise ValueError(f'{clip}: invalid frame count/timing/loop')
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f'{prefix}: manifest: {exc}')
                continue
            for clip, count in COUNTS.items():
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
    return errors, pending


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-missing', action='store_true')
    parser.add_argument('--strict-base', action='store_true', help='require MOA and PIP base delivery; frame policy unchanged')
    parser.add_argument('--strict-alpha', action='store_true', help='require all fifteen Monster bases; independent of Companion delivery')
    parser.add_argument('--alpha-only', action='store_true', help='validate only optional Alpha Monster delivery')
    parser.add_argument('--root', type=Path, default=ROOT, help='repository/delivery staging root')
    args = parser.parse_args()
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
