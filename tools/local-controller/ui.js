const token = location.hash.slice(1);
history.replaceState(null, '', '/');
const labels = { evidenceDirectory:'로컬 실행 증거', phase:'현재 단계', github:'GitHub 연결', chatgpt:'ChatGPT', codex:'Codex 로그인', pr:'현재 PR', head:'HEAD', ci:'CI', analysis:'AI 분석', codexRun:'Codex 실행', tests:'테스트', merge:'Merge Gate', nextTask:'다음 작업' };
const show = value => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
async function refresh() {
  try {
    const r = await fetch('/state', {headers:{'X-Luma-Token':token}});
    if (!r.ok) throw Error('로컬 인증 실패');
    const s = await r.json();
    document.querySelector('#status').replaceChildren(...Object.entries(labels).map(([key, label]) => {
      const card = document.createElement('article'); const title = document.createElement('strong'); const body = document.createElement('pre');
      title.textContent = label; body.textContent = show(s[key]); card.append(title,body); return card;
    }));
    for (const [id,key] of [['logs','logs'],['prs','prs'],['repair','repairPrompt']]) document.getElementById(id).textContent = key === 'logs' ? s[key].join('\n') : show(s[key]);
    document.getElementById('prompt').value = s.prompt;
  } catch (e) { document.getElementById('logs').textContent = String(e); }
}
document.querySelectorAll('button').forEach(button => button.addEventListener('click', async () => {
  const value = document.getElementById('pr').value;
  const payload = {automatic:document.getElementById('automatic').checked, pr: value ? Number(value) : null, response:document.getElementById('response').value, expectedHead:document.getElementById('merge-head').value, approval:document.getElementById('approval').checked};
  const r = await fetch('/'+button.dataset.action, {method:'POST', headers:{'Content-Type':'application/json','X-Luma-Token':token}, body:JSON.stringify(payload)});
  if (!r.ok) alert((await r.json()).error);
  await refresh();
}));
void refresh(); setInterval(refresh, 1500);
