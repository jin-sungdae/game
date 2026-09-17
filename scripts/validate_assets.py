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


def png_errors(path):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-missing', action='store_true')
    args = parser.parse_args()
    failures, pending = validate(allow_missing=args.allow_missing)
    for line in failures:
        print('FAIL:', line)
    for line in pending:
        print('PENDING:', line)
    print(f'{len(failures)} errors; {len(pending)} unprovided clips')
    raise SystemExit(bool(failures))
