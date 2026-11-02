import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true});
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
 assert.deepEqual(errors,[]);console.log('PASS: common Review sleep, terminal, one-shot, pause, reduced and frame selection');
}finally{await browser.close();}
