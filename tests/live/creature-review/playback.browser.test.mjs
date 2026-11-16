import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,channel:process.env.LUMA_BROWSER_CHANNEL});
try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5198/tests/live/creature-review/');
 await page.selectOption('#creature','M061');
 const sleep=page.locator('article[data-action="sleep"]').filter({has:page.getByRole('button',{name:'Wake',exact:true})});
 await sleep.waitFor();await page.waitForTimeout(2200);assert.match(await sleep.innerText(),/hold/);
 await page.click('#pause');const src=await sleep.locator('figure').nth(1).locator('img').getAttribute('src');await page.waitForTimeout(400);assert.equal(await sleep.locator('figure').nth(1).locator('img').getAttribute('src'),src);
 await page.click('#pause');await page.click('#reduced');const frozen=await sleep.locator('figure').nth(1).locator('img').getAttribute('src');await page.waitForTimeout(400);assert.equal(await sleep.locator('figure').nth(1).locator('img').getAttribute('src'),frozen);await page.click('#reduced');
 await sleep.getByRole('slider').fill('3');await page.waitForTimeout(50);assert.match(await sleep.innerText(),/Frame 4\/12/);await sleep.getByRole('button',{name:'자동 재생'}).click();await sleep.getByRole('button',{name:'Wake',exact:true}).click();await page.waitForTimeout(5200);assert.match(await sleep.innerText(),/BASE · Frame/);
 const attack=page.locator('article[data-action="attack"]').filter({has:page.getByRole('button',{name:'다시 재생',exact:true})});assert.match(await attack.innerText(),/BASE · Frame/);
 const defeat=page.locator('article[data-action="defeat"]').filter({has:page.getByRole('button',{name:'다시 재생',exact:true})});assert.match(await defeat.innerText(),/held · Frame 12/);
 for (const [id,action] of [['M088','interact'],['M090','hit'],['M092','hit'],['M096','cursor_react']]) {
  await page.selectOption('#creature',id);
  const card=page.locator('article[data-action="'+action+'"]').filter({has:page.getByRole('button',{name:'다시 재생',exact:true})});
  const base=card.locator('img[alt$=" BASE"]');
  const img=card.locator('img[alt$=" candidate"]');
  const restart=card.getByRole('button',{name:'다시 재생',exact:true});
  await restart.waitFor();
  await page.click('#pause');
  await restart.click();
  await card.getByText(/one-shot · Frame 1\/8/).waitFor();
  await page.click('#reduced');
  await page.click('#pause');
  await card.getByText(/one-shot · Frame 1\/8 .*reduced=true/).waitFor();
  await card.getByRole('slider').fill('7');
  await card.getByText(/selected · Frame 8\/8/).waitFor();
  await card.getByRole('button',{name:'자동 재생'}).click();
  await page.click('#reduced');
  await card.getByText(/BASE · Frame 8\/8/).waitFor();
  assert.equal(await img.getAttribute('src'),await base.getAttribute('src'));
  await page.click('#pause');
  await restart.click();
  await card.getByText(/one-shot · Frame 1\/8/).waitFor();
  await page.click('#pause');
 }
 assert.deepEqual(errors,[]);console.log('PASS: common Review sleep, terminal, one-shot, pause, reduced and frame selection');
}finally{await browser.close();}
