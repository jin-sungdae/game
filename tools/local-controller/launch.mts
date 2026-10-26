import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

// Ephemeral context: never export cookies, storage state or login tokens.
const child = spawn('python3', ['-u', resolve('tools/local-controller/server.py')], {
  stdio: ['ignore', 'pipe', 'inherit'], env: process.env,
});
let browser: Awaited<ReturnType<typeof chromium.launch>> | undefined;
let stopping = false;
async function stop() {
  if (stopping) return;
  stopping = true;
  child.kill('SIGTERM');
  await browser?.close();
}
process.on('SIGINT', () => void stop());
process.on('SIGTERM', () => void stop());
child.on('exit', () => { void stop(); });
for await (const line of createInterface({ input: child.stdout! })) {
  console.log(line);
  if (!line.startsWith('LUMA_CONTROLLER_URL=')) continue;
  try {
    browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.goto(line.slice('LUMA_CONTROLLER_URL='.length));
    if (process.argv.includes('--smoke')) {
      await page.locator('#pr').fill(process.env.LUMA_SMOKE_PR || '110');
      await page.getByRole('button', {name:'실행', exact:true}).click();
      await page.waitForFunction(() => ['WATCHING','PAUSED_ERROR'].some(s => document.querySelector('#status')?.textContent?.includes(s)), null, { timeout: 180000 });
      await page.screenshot({path:'/tmp/luma-controller-smoke.png',fullPage:true});
      await writeFile('/tmp/luma-controller-smoke.txt', await page.locator('#status').innerText() + '\n' + await page.locator('#logs').innerText());
      if (process.argv.includes('--analyze')) {
        await page.getByRole('button', {name:'Codex 구독 분석',exact:true}).click();
        await page.waitForFunction(() => ['REVIEWED','PAUSED_ERROR'].some(s => document.querySelector('#status')?.textContent?.includes(s)), null, { timeout: 900000 });
        await writeFile('/tmp/luma-controller-analysis.txt',await page.locator('#status').innerText()+'\n'+await page.locator('#logs').innerText());
        await page.screenshot({path:'/tmp/luma-controller-analysis.png',fullPage:true});
      }
      await page.getByRole('button', {name:'일시 정지',exact:true}).click();
      await page.waitForTimeout(1600);
      await writeFile('/tmp/luma-controller-pause.txt',await page.locator('#status').innerText());
      console.log('LOCAL_UI_SMOKE_FINISHED');
      await stop();
    }
    browser.on('disconnected', () => { void stop(); });
    // Browser automation is limited to our own local UI. ChatGPT is a manual link only.
  } catch (error) {
    await stop();
    throw error;
  }
}
