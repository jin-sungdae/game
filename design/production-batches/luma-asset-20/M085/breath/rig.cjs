const sharp = require(process.env.LUMA_SHARP_MODULE || 'sharp');
const fs = require('node:fs/promises');
const crypto = require('node:crypto');
const contract = require('./candidate-clip.json');

// Like the IDLE rig, sample the source with a compact, part-weighted inverse
// displacement. This cycle expands the trunk below the eyes around its centerline.
// Keep the alpha silhouette and the hood, eyes, and tentacle tips fixed.
const center = { x: 147, y: 152, rx: 23, ry: 15 };
const samples = [0, 0.25, 0.53, 0.86, 1, 0.73, 0.40, 0.17];

function hash(pixels) {
  return crypto.createHash('sha256').update(pixels).digest('hex');
}

function difference(a, b) {
  let changedPixels = 0;
  let channelDifference = 0;
  for (let i = 0; i < a.length; i += 4) {
    let difference = 0;
    for (let channel = 0; channel < 3; channel++) {
      difference += Math.abs(a[i + channel] - b[i + channel]);
    }
    changedPixels += Number(difference > 0);
    channelDifference += difference;
  }
  return { changedPixels, meanChannelDifference: channelDifference / (256 * 256 * 3) };
}

async function main() {
  const { data, info } = await sharp(contract.sourceBase).raw().toBuffer({ resolveWithObject: true });
  if (info.width !== 256 || info.height !== 256 || info.channels !== 4) throw Error('Unexpected BASE format');
  await fs.mkdir(contract.framesDirectory, { recursive: true });
  const frames = [];
  for (const amount of samples) {
    const output = Buffer.from(data);
    for (let y = center.y - center.ry; y <= center.y + center.ry; y++) {
      for (let x = center.x - center.rx; x <= center.x + center.rx; x++) {
        const across = (x - center.x) / center.rx;
        const down = (y - center.y) / center.ry;
        const radius = across ** 2 + down ** 2;
        const offset = (y * 256 + x) * 4;
        if (radius >= 1 || data[offset + 3] < 160) continue;
        const weight = amount * (1 - radius) ** 3;
        const sx = x - across * 19 * weight;
        const sy = y - down * 7 * weight;
        const x0 = Math.floor(sx);
        const y0 = Math.floor(sy);
        const source = (y0 * 256 + x0) * 4;
        const neighbors = [source, source + 4, source + 1024, source + 1028];
        if (neighbors.some(i => data[i + 3] < 160)) continue;
        const fx = sx - x0;
        const fy = sy - y0;
        for (let channel = 0; channel < 3; channel++) {
          const [topLeft, topRight, bottomLeft, bottomRight] = neighbors.map(i => data[i + channel]);
          output[offset + channel] = Math.round(
            (topLeft * (1 - fx) + topRight * fx) * (1 - fy) +
            (bottomLeft * (1 - fx) + bottomRight * fx) * fy
          );
        }
      }
    }
    const index = frames.length;
    const file = 'breath_' + String(index).padStart(2, '0') + '.png';
    await sharp(output, { raw: { width: 256, height: 256, channels: 4 } })
      .png().toFile(contract.framesDirectory + '/' + file);
    frames.push(output);
  }
  const hashes = frames.map(hash);
  if (new Set(hashes).size !== frames.length) throw Error('Duplicate BREATH frame');
  const idleHashes = [];
  for (let frame = 0; frame < frames.length; frame++) {
    const idle = 'idle_' + String(frame).padStart(2, '0') + '.png';
    idleHashes.push(hash(await sharp(__dirname + '/../idle/rigged/idle/' + idle).raw().toBuffer()));
  }
  if (hashes.some(digest => idleHashes.includes(digest))) throw Error('BREATH repeats an IDLE frame');
  const evidence = {
    sourceBase: contract.sourceBase,
    basePixelSha256: hash(data),
    center,
    samples,
    idleHashes,
    frames: frames.map((pixels, index) => ({
      pixelSha256: hashes[index],
      fromBase: difference(data, pixels),
      toNext: difference(pixels, frames[(index + 1) % frames.length]),
    })),
  };
  await fs.writeFile(__dirname + '/rig-evidence.json', JSON.stringify(evidence, null, 2) + '\n');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
