const app = document.getElementById('app');
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = m => m < 60 ? `${m} min` : `${m / 60} hr`;
const pct = q => Math.round(100 * q.checked.length / q.checklist.length);

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'show';
  clearTimeout(toast.h); toast.h = setTimeout(() => t.className = '', 3500);
}
async function api(path, opts = {}) {
  const r = await fetch('/api' + path, {
    method: opts.method || 'GET', headers: {'Content-Type': 'application/json'},
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Request failed'); }
  return r.json();
}
function notify(r) {
  if (r.xp_gained) toast(`Quest completed. You earned ${r.xp_gained} XP.`);
  if (r.new_badges.length) setTimeout(() => toast('Badge unlocked: ' + r.new_badges.join(', ')), r.xp_gained ? 3700 : 0);
}
const tags = q => `<div class="tags"><span class="tag ${q.difficulty}">${q.difficulty}</span><span class="tag">${esc(q.category)}</span>${q.status ? `<span class="tag st-${q.status}">${q.status}</span>` : ''}</div>`;
const card = q => `<a class="card" href="#/quest/${q.id}">${tags(q)}<h3>${esc(q.title)}</h3><p>${esc(q.description)}</p><div class="meta">${fmt(q.minutes)} | ${q.xp} XP</div></a>`;
const empty = (msg, link, label) => `<div class="panel"><p>${msg}</p><a class="btn" href="${link}">${label}</a></div>`;

/* ---------- 1. Landing ---------- */
async function landing() {
  app.innerHTML = `
  <section class="hero"><h1>SideQuest</h1><p class="lead">Your next coding adventure starts here.</p>
    <p>Pick a small project that fits your level and your time. Finish it, earn XP and keep your streak alive.</p>
    <a class="btn" href="#/discover">Find a quest</a><a class="btn alt" href="#/dashboard">View my progress</a></section>
  <div class="grid">
    <div class="panel"><h3>Choose</h3><p class="muted">Filter projects by difficulty, category and the time you have.</p></div>
    <div class="panel"><h3>Build</h3><p class="muted">Follow each quest's checklist from first folder to final commit.</p></div>
    <div class="panel"><h3>Level up</h3><p class="muted">Earn XP, unlock badges and track your daily streak.</p></div>
  </div>`;
}

/* ---------- 2. Discovery ---------- */
async function discover() {
  app.innerHTML = `<h1>Quest discovery</h1>
  <form class="filters panel" id="f">
    <label>Difficulty<select name="difficulty"><option value="">Any</option><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label>
    <label>Category<select name="category"><option value="">Any</option><option>Web Development</option><option>Python</option><option>General Programming</option></select></label>
    <label>Time available<select name="max_minutes"><option value="">Any</option><option value="30">Up to 30 min</option><option value="60">Up to 1 hr</option><option value="120">Up to 2 hr</option><option value="240">Up to 4 hr</option></select></label>
    <button type="button" class="btn alt" id="rnd">Surprise me</button>
  </form><p id="count" class="muted"></p><div id="list" class="grid"></div>`;
  const f = document.getElementById('f'); let items = [];
  const load = async () => {
    const p = new URLSearchParams(new FormData(f));
    [...p.keys()].forEach(k => { if (!p.get(k)) p.delete(k); });
    items = await api('/quests?' + p);
    document.getElementById('count').textContent = `${items.length} quest${items.length === 1 ? '' : 's'} found`;
    document.getElementById('list').innerHTML = items.map(card).join('') ||
      '<div class="panel">No quests match these filters. Try a longer time or a different category.</div>';
  };
  f.addEventListener('change', load);
  document.getElementById('rnd').onclick = () => items.length
    ? location.hash = '#/quest/' + items[Math.floor(Math.random() * items.length)].id
    : toast('No quests match your filters.');
  await load();
}

/* ---------- 3. Quest details ---------- */
async function questPage(id) {
  const q = await api('/quests/' + id);
  const n = q.checklist.length, all = q.checked.length === n, done = q.status === 'completed';
  const btns = done ? '<p><b>Completed. Well done.</b></p>' : `
    ${q.status === 'saved' ? `<button class="btn alt" onclick="setStatus(${q.id},'none')">Remove from saved</button>` : ''}
    ${!q.status ? `<button class="btn alt" onclick="setStatus(${q.id},'saved')">Save quest</button>` : ''}
    ${!q.status || q.status === 'saved' ? `<button class="btn" onclick="setStatus(${q.id},'started')">Start quest</button>` : ''}
    ${q.status === 'started' ? `<button class="btn" ${all ? '' : 'disabled'} onclick="setStatus(${q.id},'completed')">Complete quest (+${q.xp} XP)</button>` : ''}`;
  app.innerHTML = `<a href="#/discover">Back to all quests</a>
  <div class="panel" style="margin-top:12px">${tags(q)}<h1>${esc(q.title)}</h1><p class="lead">${esc(q.description)}</p>
    <div class="meta">Estimated time: ${fmt(q.minutes)} | Reward: ${q.xp} XP</div></div>
  <div class="cols"><div>
    <h2>The problem</h2><p>${esc(q.problem)}</p>
    <h2>Required features</h2><ul>${q.features.map(f => `<li>${esc(f)}</li>`).join('')}</ul>
    <h2>Suggested technologies</h2><div class="tags">${q.tech.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
  </div><div class="panel"><h2 style="margin-top:0">Completion checklist</h2>
    <div class="prog"><span style="width:${pct(q)}%"></span></div><p class="meta">${q.checked.length} of ${n} done</p>
    ${q.checklist.map((t, i) => `<label class="chk"><input type="checkbox" ${q.checked.includes(i) ? 'checked' : ''} ${done ? 'disabled' : ''} onchange="toggleItem(${q.id},${i},this.checked)"> <span>${esc(t)}</span></label>`).join('')}
    <div class="actions">${btns}</div></div></div>`;
}
window.setStatus = async (id, s) => {
  try { notify(await api(`/quests/${id}/status`, {method: 'POST', body: {status: s}})); await questPage(id); }
  catch (e) { toast(e.message); }
};
window.toggleItem = async (id, i, d) => {
  try { await api(`/quests/${id}/checklist`, {method: 'POST', body: {index: i, done: d}}); await questPage(id); }
  catch (e) { toast(e.message); }
};

/* ---------- 4. My quests ---------- */
async function myQuests() {
  const all = await api('/my-quests'); let tab = 'all';
  app.innerHTML = `<h1>My quests</h1><div class="tabs" id="tabs"></div><div id="rows" class="list"></div>`;
  const draw = () => {
    document.getElementById('tabs').innerHTML = ['all', 'saved', 'started', 'completed'].map(t =>
      `<button class="btn ${t === tab ? '' : 'alt'}" data-t="${t}">${t[0].toUpperCase() + t.slice(1)} (${all.filter(q => t === 'all' || q.status === t).length})</button>`).join('');
    document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => { tab = b.dataset.t; draw(); });
    const rows = all.filter(q => tab === 'all' || q.status === tab);
    document.getElementById('rows').innerHTML = rows.map(q => `<div class="panel"><div class="row">
      <div><a href="#/quest/${q.id}"><b>${esc(q.title)}</b></a><div class="meta">${q.difficulty} | ${esc(q.category)} | ${q.xp} XP</div></div>
      <span class="tag st-${q.status}">${q.status}</span></div>
      <div class="prog"><span style="width:${q.status === 'completed' ? 100 : pct(q)}%"></span></div></div>`).join('') ||
      empty('Nothing here yet. Save or start a quest to see it listed.', '#/discover', 'Browse quests');
  };
  draw();
}

/* ---------- 5. Dashboard ---------- */
async function dashboard() {
  const d = await api('/dashboard');
  app.innerHTML = `<h1>Progress dashboard</h1>
  <div class="stats">
    <div class="panel stat"><b>${d.level}</b>Level</div><div class="panel stat"><b>${d.xp}</b>Total XP</div>
    <div class="panel stat"><b>${d.streak}</b>Day streak</div><div class="panel stat"><b>${d.started}</b>Started</div>
    <div class="panel stat"><b>${d.completed}</b>Completed</div><div class="panel stat"><b>${d.overall_pct}%</b>Overall completion</div>
  </div>
  <div class="panel"><div class="row"><b>Level ${d.level} progress</b><span class="meta">${d.xp_in_level} / ${d.xp_per_level} XP to level ${d.level + 1}</span></div>
    <div class="prog"><span style="width:${d.xp_in_level}%"></span></div></div>
  <div class="cols"><div><h2>Active quests</h2><div class="list">${d.active.map(q => `<div class="panel"><a href="#/quest/${q.id}"><b>${esc(q.title)}</b></a>
    <div class="prog"><span style="width:${pct(q)}%"></span></div><span class="meta">${pct(q)}% complete</span></div>`).join('') ||
    empty('No active quests. Start one to begin earning XP.', '#/discover', 'Find a quest')}</div></div>
  <div><h2>Recent activity</h2><div class="panel"><ul class="plain">${d.recent.map(a => `<li>${esc(a.text)}<div class="meta">${a.ts.replace('T', ' ')}</div></li>`).join('') ||
    '<li class="muted">No activity yet.</li>'}</ul></div>
  <p><button class="btn alt" id="reset">Reset demo data</button></p></div></div>`;
  document.getElementById('reset').onclick = async () => {
    if (confirm('Clear all progress, XP and activity?')) { await api('/reset', {method: 'POST'}); toast('Progress reset.'); dashboard(); }
  };
}

/* ---------- 6. Achievements ---------- */
async function achievements() {
  const a = await api('/achievements');
  app.innerHTML = `<h1>Achievements</h1><p class="muted">${a.unlocked} of ${a.badges.length} badges unlocked</p><div class="grid">
    ${a.badges.map(b => `<div class="panel badge ${b.unlocked ? '' : 'locked'}"><h3>${esc(b.name)}</h3><p class="muted">${esc(b.desc)}</p>
    <span class="tag ${b.unlocked ? 'st-completed' : ''}">${b.unlocked ? 'Unlocked' : 'Locked'}</span></div>`).join('')}</div>`;
}

/* ---------- Router ---------- */
const routes = {'': landing, discover, quest: questPage, 'my-quests': myQuests, dashboard, achievements};
async function route() {
  const [name = '', arg] = location.hash.replace(/^#\/?/, '').split('/');
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.dataset.r === (name === 'quest' ? 'discover' : name)));
  document.getElementById('nav').classList.remove('open');
  try { await (routes[name] || landing)(arg); }
  catch (e) { app.innerHTML = `<div class="panel"><h2>Something went wrong</h2><p>${esc(e.message)}</p><a class="btn" href="#/">Go home</a></div>`; }
  window.scrollTo(0, 0);
}
document.getElementById('menu').onclick = () => document.getElementById('nav').classList.toggle('open');
window.addEventListener('hashchange', route);
route();
