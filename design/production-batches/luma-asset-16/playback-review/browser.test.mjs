// Run against the existing loopback Vite server; does not launch native LUMA.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1100,height:720}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.clock.install();
 await page.goto((process.env.LUMA_REVIEW_URL||'http://127.0.0.1:5199')+'/design/production-batches/luma-asset-16/playback-review/index.html');
 await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('enter'));
 assert.equal(await page.locator('#candidate option').count(),7);
 await page.clock.runFor(6000);
 assert.match(await page.locator('#status').textContent(),/hold/);
 await page.getByRole('button',{name:'일시정지',exact:true}).click();
 const frozen=await page.locator('#revised').getAttribute('src');
 await page.clock.runFor(1000);assert.equal(await page.locator('#revised').getAttribute('src'),frozen);
 await page.getByRole('button',{name:'계속 재생',exact:true}).click();
 await page.getByRole('button',{name:'깨우기 요청'}).click();await page.clock.runFor(6000);
 assert.match(await page.locator('#status').textContent(),/done/);
 assert.match(await page.locator('#revised').getAttribute('src'),/sleep_11.png$/);
 for(const id of ['M061 DEFEAT','M062 DEFEAT','M064 DEFEAT','M061 ATTACK','M062 ATTACK','M061 MOVE']){
  await page.locator('#candidate').selectOption(id);
  await page.waitForFunction(value=>document.querySelector('#status').textContent.startsWith(value),id);
  await page.clock.runFor(7000);
  assert.equal(await page.locator('#wake').isDisabled(),true);
  if(id.includes('DEFEAT'))assert.match(await page.locator('#status').textContent(),/held/);
  if(id.includes('ATTACK'))assert.match(await page.locator('#status').textContent(),/done/);
  assert.equal(await page.locator('img').evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth===256)),true);
 }
 assert.equal(await page.locator('#error').textContent(),'');assert.deepEqual(errors,[]);
 if(process.env.LUMA_REVIEW_SCREENSHOT)await page.screenshot({path:process.env.LUMA_REVIEW_SCREENSHOT});
 console.log('Browser PASS: 7 recipes, 256px loading, sleep hold/wake, pause, terminal defeat, one-shot attack; NOT native GUI');
} finally {await browser.close();}
