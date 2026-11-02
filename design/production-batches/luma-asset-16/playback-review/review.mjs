import {CandidatePlayback, recipe} from './playback.mjs';
const $ = id => document.getElementById(id);
let rows, row, player, originalElapsed = 0, paused = false, last = performance.now();
let generation = 0, ready = false;
const url = path => '/'+path;
async function start() {
  const current = ++generation;
  ready = false;
  $('error').textContent = '';
  row = rows.find(r => r.id === $('candidate').value);
  try {
    await Promise.all([row.base, ...row.files].map(path => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => image.naturalWidth === 256 && image.naturalHeight === 256 ? resolve() : reject(Error('256px 이미지가 아닙니다'));
      image.onerror = () => reject(Error('이미지를 불러오지 못했습니다: '+path));
      image.src = url(path);
    })));
    if (current !== generation) return;
    player = new CandidatePlayback(recipe(row.monster, row.action));
    originalElapsed = 0; last = performance.now(); paused = false;
    $('pause').textContent = '일시정지'; $('wake').disabled = row.action !== 'SLEEP';
    $('base').src = url(row.base); ready = true; render();
  } catch (error) {
    if (current === generation) $('error').textContent = error.message;
  }
}
function render() {
  const index = Math.floor(originalElapsed / row.frameDuration);
  const originalIndex = row.loop ? index % row.files.length : Math.min(index, row.files.length-1);
  $('original').src = url(row.files[originalIndex]);
  $('revised').src = url(row.files[player.sample()]);
  $('status').textContent = `${row.id} · ${player.phase} · 프레임 ${player.sample()+1}/${row.files.length} · ${paused?'정지':'재생'} · HUMAN_REVIEW_REQUIRED`;
}
function tick(now) {
  // Do not skip action phases after a hidden tab resumes.
  const delta = Math.min(100, Math.max(0, now-last)); last = now;
  if (ready && !paused && !document.hidden) {originalElapsed += delta; player.advance(delta); render();}
  requestAnimationFrame(tick);
}
try {
  const response = await fetch('./review-data.json');
  if (!response.ok) throw Error('후보 목록 로딩 실패');
  rows = (await response.json()).clips;
  $('candidate').replaceChildren(...rows.map(row => new Option(row.id, row.id)));
  $('candidate').onchange = start; $('restart').onclick = start;
  $('pause').onclick = () => {paused=!paused; $('pause').textContent=paused?'계속 재생':'일시정지'; if(ready)render();};
  $('wake').onclick = () => {if(ready)player.wake();};
  await start(); requestAnimationFrame(tick);
} catch (error) {$('error').textContent=error.message;}
