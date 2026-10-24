/* SideQuest v2 frontend: quests, roadmaps, goals, garden, proof of work, profiles and friends. */
const app = document.getElementById('app');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = minutes => minutes < 60 ? `${minutes} min` : `${minutes / 60} hr`;
const pct = q => q.checklist.length ? Math.round(100 * q.checked.length / q.checklist.length) : 0;
let sessionToken = localStorage.getItem('sidequestToken') || '';
let currentProfile = null;

function toast(message) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.className = 'show';
  clearTimeout(toast.handle);
  toast.handle = setTimeout(() => { el.className = ''; }, 3600);
}

async function api(path, opts = {}) {
  const headers = {};
  let body;
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  const response = await fetch('/api' + path, {method: opts.method || 'GET', headers, body});
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

async function startGuestSession() {
  const response = await fetch('/api/auth/guest', {method: 'POST'});
  if (!response.ok) throw new Error('Could not start a guest session. Refresh the page to try again.');
  const data = await response.json();
  sessionToken = data.token;
  localStorage.setItem('sidequestToken', sessionToken);
  return data.user;
}

async function initAuth() {
  if (sessionToken) {
    try { currentProfile = await api('/auth/me'); }
    catch (_) { sessionToken = ''; localStorage.removeItem('sidequestToken'); }
  }
  if (!sessionToken) currentProfile = await startGuestSession();
  currentProfile = await api('/profile');
  applyTheme(currentProfile.theme);
  updateHeader();
}

function applyTheme(theme) {
  const allowed = ['light', 'dark', 'anime', 'cute'];
  document.documentElement.dataset.theme = allowed.includes(theme) ? theme : 'light';
}
function updateHeader() {
  if (!currentProfile) return;
  const suffix = currentProfile.is_guest ? 'Guest mode' : currentProfile.rank;
  document.getElementById('header-user').textContent = `${currentProfile.display_name} · ${suffix}`;
}
function navActive(name) {
  document.querySelectorAll('nav a').forEach(link => link.classList.toggle('on', link.dataset.r === name));
}
function notify(result) {
  if (result.xp_gained) toast(`Quest completed! +${result.xp_gained} XP `);
  if (result.new_badges?.length) setTimeout(() => toast(`Achievement unlocked: ${result.new_badges.join(', ')}`), result.xp_gained ? 3600 : 0);
}
const tags = q => `<div class="tags"><span class="tag ${esc(q.difficulty)}">${esc(q.difficulty)}</span><span class="tag">${esc(q.category)}</span>${q.status ? `<span class="tag st-${esc(q.status)}">${esc(q.status)}</span>` : ''}</div>`;
const card = q => `<a class="card" href="#/quest/${q.id}">${tags(q)}<h3>${esc(q.title)}</h3><p class="muted">${esc(q.description)}</p><div class="meta">${fmt(q.minutes)} · ${q.xp} XP</div></a>`;
const empty = (message, link = '#/discover', label = 'Explore quests') => `<div class="empty"><p>${esc(message)}</p><a class="btn" href="${link}">${esc(label)}</a></div>`;
const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {month:'short', day:'numeric'});

/* Home / adventure board */
async function landing() {
  const [d, goal, topic, roadmaps] = await Promise.all([api('/dashboard'), api('/weekly-goal'), api('/trending'), api('/roadmaps')]);
  app.innerHTML = `
    <section class="hero">
      <div class="topic-date">YOUR NEXT ADVENTURE STARTS HERE</div>
      <h1>Small quests.<br><span class="highlight">Real skills.</span></h1>
      <p class="lead">Learn by building, submit proof of your work, and watch your Skill Garden grow one quest at a time.</p>
      <div class="actions"><a class="btn" href="#/discover"> Find a quest</a><a class="btn alt" href="#/roadmaps"> Choose a roadmap</a><a class="btn ghost" href="#/garden"> View Skill Garden</a></div>
    </section>
    <div class="stats">
      <div class="panel stat"><div class="stat-label">LEVEL</div><strong>${d.level}</strong><span>Level · ${esc(d.rank)}</span></div>
      <div class="panel stat"><div class="stat-label">TOTAL XP</div><strong>${d.xp}</strong><span>Total XP</span></div>
      <div class="panel stat"><div class="stat-label">STREAK</div><strong>${d.streak}</strong><span>Current day streak</span></div>
      <div class="panel stat"><div class="stat-label">COMPLETED</div><strong>${d.completed}</strong><span>Quests completed</span></div>
    </div>
    <div class="grid two">
      <section class="panel">
        <div class="row"><h2 style="margin:0">This week's mission</h2><a class="small-link" href="#/goals">Edit goals →</a></div>
        <p class="muted">${goal.completed_quests} of ${goal.target_quests} quests · ${goal.earned_xp} of ${goal.target_xp} XP</p>
        <div class="row"><b>Quest goal</b><span class="meta">${goal.quests_pct}%</span></div><div class="prog"><span style="width:${goal.quests_pct}%"></span></div>
        <div class="row"><b>XP goal</b><span class="meta">${goal.xp_pct}%</span></div><div class="prog"><span style="width:${goal.xp_pct}%"></span></div>
        <div class="actions"><a class="btn alt" href="#/goals">View weekly goals</a></div>
      </section>
      <section class="panel topic-card">
        <div class="topic-date"> TOPIC SPOTLIGHT · ${esc(topic.date)}</div><h2 style="margin-top:10px">${esc(topic.title)}</h2>
        <span class="tag">${esc(topic.category)}</span><p>${esc(topic.why)}</p><div class="status-line"><b>Mini challenge:</b> ${esc(topic.challenge)}</div>
        <div class="actions"><a class="btn" href="#/trending">Explore today's topic →</a></div><p class="meta">${esc(topic.source_label)}</p>
      </section>
    </div>
    <div class="section-head"><h2>Pick a learning path</h2><a href="#/roadmaps">All roadmaps →</a></div>
    <div class="grid">${roadmaps.map(r => `<a class="card" href="#/roadmaps"><div class="icon-tile">${r.icon}</div><h3>${esc(r.title)}</h3><p class="muted">${esc(r.description)}</p><div class="prog"><span style="width:${r.progress_pct}%"></span></div><div class="meta">${r.completed_steps}/${r.total_steps} steps complete</div></a>`).join('')}</div>
    <div class="section-head"><h2>Continue your adventure</h2><a href="#/discover">Browse every quest →</a></div>
    <div class="grid">${d.active.slice(0,3).map(card).join('') || empty('No active quests yet. Start with something small and get moving.')}</div>`;
}

/* Discover quests */
async function discover() {
  app.innerHTML = `<div class="section-head"><div><h1>Quest board</h1><p class="lead">Pick a challenge that fits your time and level.</p></div></div>
    <form class="filters panel" id="quest-filters">
      <label>Difficulty<select name="difficulty"><option value="">Any level</option><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label>
      <label>Category<select name="category"><option value="">Any skill</option><option>Web Development</option><option>Python</option><option>General Programming</option></select></label>
      <label>Time available<select name="max_minutes"><option value="">Any duration</option><option value="30">Up to 30 min</option><option value="60">Up to 1 hr</option><option value="120">Up to 2 hr</option><option value="240">Up to 4 hr</option></select></label>
      <button type="button" class="btn alt" id="random-quest"> Surprise me</button>
    </form><p id="quest-count" class="meta"></p><div id="quest-list" class="grid"></div>`;
  const form = document.getElementById('quest-filters'); let items = [];
  const load = async () => {
    const params = new URLSearchParams(new FormData(form));
    [...params.keys()].forEach(key => { if (!params.get(key)) params.delete(key); });
    items = await api('/quests?' + params.toString());
    document.getElementById('quest-count').textContent = `${items.length} quest${items.length === 1 ? '' : 's'} available`;
    document.getElementById('quest-list').innerHTML = items.map(card).join('') || '<div class="empty">No quests match. Try a different filter.</div>';
  };
  form.addEventListener('change', load);
  document.getElementById('random-quest').onclick = () => items.length ? location.hash = `#/quest/${items[Math.floor(Math.random()*items.length)].id}` : toast('No quests match those filters.');
  await load();
}

/* Quest detail and final submission */
async function questPage(id) {
  if (!id || !/^\d+$/.test(id)) { location.hash = '#/discover'; return; }
  const [q, submissions] = await Promise.all([api('/quests/' + id), api('/submissions?quest_id=' + id)]);
  const total = q.checklist.length, allChecked = q.checked.length === total, done = q.status === 'completed';
  const hasSubmission = submissions.length > 0;
  let actions = '';
  if (done) actions = `<div class="status-line"> Quest complete. Your latest submission is saved and XP has been awarded.</div>`;
  else actions = `${q.status === 'saved' ? `<button class="btn alt" id="remove-saved">Remove saved quest</button>` : ''}
    ${!q.status ? `<button class="btn alt" id="save-quest">Save quest</button>` : ''}
    ${!q.status || q.status === 'saved' ? `<button class="btn" id="start-quest">Start quest</button>` : ''}
    <button class="btn" id="complete-quest" ${allChecked && hasSubmission ? '' : 'disabled'}>Complete quest · +${q.xp} XP</button>`;
  app.innerHTML = `<a href="#/discover" class="small-link">← Back to quest board</a>
    <div class="panel" style="margin-top:14px">${tags(q)}<div class="row"><div><h1>${esc(q.title)}</h1><p class="lead">${esc(q.description)}</p></div><div class="status-line"> ${q.xp} XP<br> ${fmt(q.minutes)}</div></div></div>
    <div class="cols"><section>
      <h2>The problem to solve</h2><p>${esc(q.problem)}</p><h2>Required features</h2><ul>${q.features.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
      <h2>Suggested technologies</h2><div class="tags">${q.tech.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div>
      <section class="panel"><div class="row"><h2 style="margin:0">Final submission</h2><span class="tag ${hasSubmission?'submitted':''}">${hasSubmission ? `${submissions.length} submission${submissions.length === 1?'':'s'}` : 'Required to complete'}</span></div>
        <p class="muted">Submit your code or GitHub repository and prove the program works with output text, a screenshot, or a live demo.</p>
        ${submissions.slice(0,1).map(s=>`<div class="status-line"><b>Latest submission:</b> ${esc(s.status)} · ${esc(s.created_at.replace('T',' '))}${s.github_url?` · <a href="${esc(s.github_url)}" target="_blank" rel="noopener noreferrer">Repository</a>`:''}</div>`).join('')}
        ${done ? '' : `<form id="submission-form" class="stack" enctype="multipart/form-data">
          <div class="field"><label for="code_text">Source code</label><textarea id="code_text" name="code_text" rows="8" maxlength="200000" placeholder="Paste your code here, or add a GitHub link below..."></textarea><small>Maximum 200,000 characters. Do not paste API keys or passwords.</small></div>
          <div class="form-grid"><div class="field"><label for="github_url">GitHub repository URL</label><input id="github_url" name="github_url" type="url" placeholder="https://github.com/you/project"></div>
            <div class="field"><label for="demo_url">Live demo URL (optional)</label><input id="demo_url" name="demo_url" type="url" placeholder="https://your-demo.example"></div>
            <div class="field full"><label for="output_text">Program output / test result</label><textarea id="output_text" name="output_text" rows="4" maxlength="20000" placeholder="Paste the output you saw in VS Code or describe your test result..."></textarea></div>
            <div class="field full"><label for="screenshot">Output screenshot (optional, max 3 MB)</label><input id="screenshot" name="screenshot" type="file" accept="image/png,image/jpeg,image/webp"></div>
            <div class="field full"><label for="notes">What did you learn? (optional)</label><textarea id="notes" name="notes" rows="2" maxlength="2000" placeholder="One or two things you learned while building it."></textarea></div>
          </div><button class="btn" type="submit">Submit project</button><p class="meta">Uploads are stored as files and are not executed by SideQuest.</p>
        </form>`}
      </section>
    </section><aside class="panel"><h2 style="margin-top:0">Quest checklist</h2><div class="row"><span class="meta">${q.checked.length} of ${total} complete</span><b>${pct(q)}%</b></div><div class="prog"><span style="width:${pct(q)}%"></span></div>
      ${q.checklist.map((item,i)=>`<label class="chk"><input type="checkbox" data-check="${i}" ${q.checked.includes(i)?'checked':''} ${done?'disabled':''}><span>${esc(item)}</span></label>`).join('')}
      <div class="actions">${actions}</div>
      ${!hasSubmission && !done ? `<p class="meta">Complete the checklist and submit your code plus an output proof to finish this quest.</p>`:''}
    </aside></div>`;
  document.querySelectorAll('[data-check]').forEach(input => input.addEventListener('change', async () => {
    try { await api(`/quests/${id}/checklist`, {method:'POST', body:{index:Number(input.dataset.check), done:input.checked}}); await questPage(id); }
    catch (e) { toast(e.message); await questPage(id); }
  }));
  const remove = document.getElementById('remove-saved'); if (remove) remove.onclick = () => setStatus(id,'none');
  const save = document.getElementById('save-quest'); if (save) save.onclick = () => setStatus(id,'saved');
  const start = document.getElementById('start-quest'); if (start) start.onclick = () => setStatus(id,'started');
  const complete = document.getElementById('complete-quest'); if (complete) complete.onclick = () => setStatus(id,'completed');
  const submitForm = document.getElementById('submission-form');
  if (submitForm) submitForm.onsubmit = async event => {
    event.preventDefault();
    const formData = new FormData(submitForm); formData.append('quest_id', id);
    const button = submitForm.querySelector('button[type="submit"]'); button.disabled = true; button.textContent = 'Submitting…';
    try { await api('/submissions', {method:'POST', body:formData}); toast('Submission saved. Finish the checklist to complete the quest.'); await questPage(id); }
    catch (e) { toast(e.message); button.disabled = false; button.textContent = 'Submit project'; }
  };
}
window.setStatus = async (id, status) => {
  try { notify(await api(`/quests/${id}/status`, {method:'POST',body:{status}})); currentProfile = await api('/profile'); updateHeader(); await questPage(id); }
  catch (e) { toast(e.message); }
};

/* My quests */
async function myQuests() {
  const items = await api('/my-quests');
  let tab = 'all';
  app.innerHTML = `<h1>My quests</h1><p class="lead">Everything you've saved, started, and completed.</p><div class="tabs" id="my-tabs"></div><div id="my-rows" class="list"></div>`;
  const draw = () => {
    document.getElementById('my-tabs').innerHTML = ['all','saved','started','completed'].map(t=>`<button class="btn ${t===tab?'':'alt'}" data-tab="${t}">${t[0].toUpperCase()+t.slice(1)} (${items.filter(q=>t==='all'||q.status===t).length})</button>`).join('');
    document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;draw();});
    const shown=items.filter(q=>tab==='all'||q.status===tab);
    document.getElementById('my-rows').innerHTML=shown.map(q=>`<div class="panel"><div class="row"><div><a href="#/quest/${q.id}"><b>${esc(q.title)}</b></a><div class="meta">${esc(q.difficulty)} · ${esc(q.category)} · ${q.xp} XP</div></div><span class="tag st-${esc(q.status)}">${esc(q.status)}</span></div><div class="prog"><span style="width:${q.status==='completed'?100:pct(q)}%"></span></div></div>`).join('')||empty('Nothing here yet. Pick a quest and begin.');
  }; draw();
}

/* Statistics dashboard */
async function statsPage() {
  const [d, s, goal] = await Promise.all([api('/dashboard'),api('/stats'),api('/weekly-goal')]);
  app.innerHTML = `<div class="row"><div><h1>Learning statistics</h1><p class="lead">Progress you can measure, not vibes you have to guess.</p></div><a href="#/achievements" class="btn alt"> Achievements</a></div>
    <div class="stats"><div class="panel stat"><strong>${d.level}</strong><span>Level · ${esc(d.rank)}</span></div><div class="panel stat"><strong>${d.xp}</strong><span>Total XP</span></div><div class="panel stat"><strong>${d.streak} </strong><span>Current streak</span></div><div class="panel stat"><strong>${d.best}</strong><span>Best streak</span></div><div class="panel stat"><strong>${d.completed}</strong><span>Quests completed</span></div><div class="panel stat"><strong>${Math.round(s.minutes_estimated/60*10)/10}h</strong><span>Estimated learning time</span></div></div>
    <section class="panel"><div class="row"><h2 style="margin:0">Level ${d.level} progress</h2><span class="meta">${d.xp_in_level} / ${d.xp_per_level} XP to next level</span></div><div class="prog"><span style="width:${d.xp_in_level}%"></span></div></section>
    <div class="cols"><section class="panel"><h2 style="margin-top:0">Learning activity · last 35 days</h2><div class="heatmap">${s.heatmap.map(day=>`<div class="heat" data-level="${day.count===0?0:day.count===1?1:day.count<=3?2:day.count<=5?3:4}" title="${day.date}: ${day.count} learning actions"></div>`).join('')}</div><p class="meta">A square lights up when you work on a quest, submit a project, or update your profile. Streaks reward consecutive calendar days.</p></section>
    <section class="panel"><h2 style="margin-top:0">Completed quests by skill</h2>${s.completed_by_category.map(x=>`<div class="row"><span>${esc(x.category)}</span><b>${x.done} · ${x.xp} XP</b></div><div class="prog"><span style="width:${Math.min(100,100*x.done/Math.max(1,d.completed))}%"></span></div>`).join('')||'<p class="muted">Your first completed quest will appear here.</p>'}<div class="status-line">This week: ${goal.completed_quests}/${goal.target_quests} quests and ${goal.earned_xp}/${goal.target_xp} XP</div></section></div>
    <div class="section-head"><h2>Recent activity</h2><button class="btn alt" id="reset-data">Reset my practice data</button></div><div class="panel"><ul class="plain">${d.recent.map(x=>`<li>${esc(x.text)}<div class="meta">${esc(x.ts.replace('T',' '))}</div></li>`).join('')||'<li class="muted">No activity yet.</li>'}</ul></div>`;
  document.getElementById('reset-data').onclick=async()=>{if(confirm('Delete your quest progress, submissions, XP, and learning activity? Your account and friends will remain.')){try{await api('/reset',{method:'POST'});currentProfile=await api('/profile');updateHeader();toast('Your practice data was reset.');await statsPage();}catch(e){toast(e.message);}}};
}

/* Weekly goals */
async function goalsPage() {
  const g=await api('/weekly-goal');
  app.innerHTML=`<h1>Weekly goals</h1><p class="lead">Pick a target that stretches you without turning learning into unpaid overtime.</p>
    <div class="stats"><div class="panel stat"><strong>${g.completed_quests}/${g.target_quests}</strong><span>Quests completed</span><div class="prog"><span style="width:${g.quests_pct}%"></span></div></div><div class="panel stat"><strong>${g.earned_xp}/${g.target_xp}</strong><span>XP earned</span><div class="prog"><span style="width:${g.xp_pct}%"></span></div></div></div>
    <section class="panel"><div class="topic-date">WEEK STARTING ${esc(g.week_start)}</div><h2>Adjust your mission</h2><form id="goal-form" class="form-grid"><div class="field"><label for="target_quests">Quests per week (1–30)</label><input id="target_quests" name="target_quests" type="number" min="1" max="30" value="${g.target_quests}" required></div><div class="field"><label for="target_xp">XP per week (50–5000)</label><input id="target_xp" name="target_xp" type="number" min="50" max="5000" step="50" value="${g.target_xp}" required></div><div class="field full"><button class="btn" type="submit">Save weekly goals</button></div></form><p class="meta">Progress counts completed quests and their XP from the current Monday through Sunday. Goal targets carry over when the week changes.</p></section>`;
  document.getElementById('goal-form').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await api('/weekly-goal',{method:'PUT',body:{target_quests:Number(f.get('target_quests')),target_xp:Number(f.get('target_xp'))}});toast('Weekly goals updated.');await goalsPage();}catch(err){toast(err.message);}};
}

/* Roadmaps */
async function roadmapsPage() {
  const roadmaps=await api('/roadmaps');
  app.innerHTML=`<h1>Learning roadmaps</h1><p class="lead">Follow a path instead of collecting random tutorials like browser tabs are a personality trait.</p><div class="grid two">${roadmaps.map(r=>`<section class="panel"><div class="row"><div class="icon-tile">${r.icon}</div><span class="tag">${esc(r.level)}</span></div><h2 style="margin-top:0">${esc(r.title)}</h2><p class="muted">${esc(r.description)}</p><div class="row"><b>${r.completed_steps}/${r.total_steps} steps</b><span class="meta">${r.progress_pct}% complete</span></div><div class="prog"><span style="width:${r.progress_pct}%"></span></div><div class="roadmap-steps">${r.steps.map((s,i)=>`<div class="roadmap-step"><div class="step-check ${s.completed?'done':''}">${s.completed?'OK':i+1}</div><div><a href="#/quest/${s.id}"><b>${esc(s.title)}</b></a><div class="meta">${esc(s.difficulty)} · ${fmt(s.minutes)} · ${s.xp} XP</div></div></div>`).join('')}</div><div class="actions">${r.enrolled?'<span class="tag accepted">Roadmap joined</span>':`<button class="btn" data-enroll="${esc(r.id)}">Join roadmap</button>`}<a href="#/discover" class="btn alt">Browse quests</a></div></section>`).join('')}</div>`;
  document.querySelectorAll('[data-enroll]').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await api(`/roadmaps/${button.dataset.enroll}/enroll`,{method:'POST'});toast('Roadmap added to your learning paths.');await roadmapsPage();}catch(e){toast(e.message);button.disabled=false;}});
}

/* Skill garden */
async function gardenPage() {
  const g=await api('/garden');
  app.innerHTML=`<section class="hero"><div class="topic-date">YOUR PERSONAL SKILL GARDEN</div><h1>Grow what you know.</h1><p class="lead">Every completed quest helps a skill plant grow. Different skills, different plants. No watering can required.</p><div class="status-line">${esc(g.message)}</div></section>
    <div class="stats"><div class="panel stat"><strong>${g.completed_quests}</strong><span>Quests nourishing the garden</span></div><div class="panel stat"><strong>${g.plants.length}</strong><span>Skill plots</span></div></div>
    <div class="grid">${g.plants.map(p=>`<section class="panel plant"><div class="row"><span class="tag">${esc(p.stage)}</span><span class="level">Level ${p.level}/5</span></div><div class="plant-visual" aria-label="Skill growth marker"><span class="plant-core">${esc(p.label)}</span></div><h2 style="margin-top:0">${esc(p.name)}</h2><p class="muted">${esc(p.description)}</p><div class="row"><span>Completed quests</span><b>${p.completed}</b></div><div class="prog"><span style="width:${p.progress_pct}%"></span></div><div class="row"><span class="meta">${p.xp} XP earned in this skill</span><span class="meta">${p.level===5?'Max growth':'Keep building'}</span></div></section>`).join('')}</div>
    <div class="actions"><a class="btn" href="#/discover">Plant another seed</a><a class="btn alt" href="#/roadmaps">Follow a roadmap</a></div>`;
}

/* Daily curated tech topic */
async function trendingPage() {
  const t=await api('/trending');
  app.innerHTML=`<section class="hero topic-card"><div class="topic-date"> TOPIC OF THE DAY · ${esc(t.date)}</div><h1>${esc(t.title)}</h1><span class="tag">${esc(t.category)}</span><p class="lead">${esc(t.why)}</p><div class="status-line"><b>Your mini quest:</b> ${esc(t.challenge)}</div><div class="actions"><a class="btn" href="${esc(t.resource)}" target="_blank" rel="noopener noreferrer">Open learning resource ↗</a><a href="#/submissions" class="btn alt">Submit your work</a></div></section>
    <section class="panel"><h2>How this section works</h2><p>This version rotates through a curated list of development topics based on the date, so the section works without an external API key. It is <b>not yet a live global trend feed</b>. The resource link opens documentation or a learning reference for the topic.</p><p class="meta">Source mode: ${esc(t.source_label)}</p></section>`;
}

/* Submission history */
async function submissionsPage() {
  const items=await api('/submissions');
  app.innerHTML=`<h1>Project submissions</h1><p class="lead">Your source code, output proof, repository links, and learning notes in one place.</p><div class="actions"><a class="btn" href="#/discover">Choose a quest to submit</a></div><div class="list" style="margin-top:18px">${items.map(s=>`<section class="panel"><div class="row"><div><h2 style="margin:0"><a href="#/quest/${s.quest_id}">${esc(s.quest_title)}</a></h2><div class="meta">Submitted ${esc(s.created_at.replace('T',' '))}</div></div><span class="tag ${esc(s.status)}">${esc(s.status)}</span></div>${s.github_url?`<p><a href="${esc(s.github_url)}" target="_blank" rel="noopener noreferrer">GitHub repository ↗</a></p>`:''}${s.demo_url?`<p><a href="${esc(s.demo_url)}" target="_blank" rel="noopener noreferrer">Live demo ↗</a></p>`:''}${s.output_text?`<details><summary>View submitted output</summary><pre class="code-preview">${esc(s.output_text)}</pre></details>`:''}${s.code_text?`<details><summary>View submitted source code</summary><pre class="code-preview">${esc(s.code_text)}</pre></details>`:''}${s.notes?`<p><b>Learning notes:</b> ${esc(s.notes)}</p>`:''}${s.screenshot_url?`<div><span class="meta">Output screenshot</span><img class="screenshot-preview" data-screenshot="${esc(s.screenshot_url)}" alt="Submitted output screenshot" loading="lazy"></div>`:''}${s.feedback?`<div class="status-line"><b>Feedback:</b> ${esc(s.feedback)}</div>`:''}</section>`).join('')||empty('You have not submitted a project yet. Choose a quest, build it in your editor, then submit the code and output proof.','#/discover','Find your first quest')}</div>`;
  await loadPrivateImages();
}
async function loadPrivateImages() {
  const images=document.querySelectorAll('img[data-screenshot]');
  for (const img of images) {
    try { const r=await fetch(img.dataset.screenshot,{headers:sessionToken?{Authorization:`Bearer ${sessionToken}`}:{}}); if(r.ok){const blob=await r.blob();img.src=URL.createObjectURL(blob);}else img.alt='Screenshot unavailable'; }
    catch(_){img.alt='Screenshot unavailable';}
  }
}

/* Achievements */
async function achievementsPage() {
  const a=await api('/achievements');
  app.innerHTML=`<h1>Guild achievements</h1><p class="lead">${a.unlocked} of ${a.badges.length} badges unlocked. Every badge is tied to real learning activity.</p><div class="grid">${a.badges.map(b=>`<section class="panel badge ${b.unlocked?'':'locked'}"><div class="icon-tile">${b.unlocked?'EARNED':'LOCKED'}</div><h3>${esc(b.name)}</h3><p class="muted">${esc(b.desc)}</p><span class="tag ${b.unlocked?'accepted':''}">${b.unlocked?'Unlocked':'Locked'}</span></section>`).join('')}</div>`;
}

/* Friends-only social layer */
async function friendsPage() {
  const [f, board]=await Promise.all([api('/friends'),api('/leaderboard')]);
  app.innerHTML=`<div class="row"><div><h1>Friends guild </h1><p class="lead">Your leaderboard contains only you and people whose friend requests were accepted.</p></div></div>
    ${currentProfile.is_guest?'<div class="status-line">Guest mode has a temporary name. Create a profile first to make friend requests that your friends can find.</div>':''}
    <section class="panel"><h2 style="margin-top:0">Add a friend</h2><form id="friend-form" class="inline-form"><div class="field"><label for="friend-username">Friend's exact SideQuest username</label><input id="friend-username" name="username" minlength="3" maxlength="20" required placeholder="their_username"></div><button class="btn" type="submit" ${currentProfile.is_guest?'disabled':''}>Send request</button></form></section>
    ${f.incoming.length?`<div class="section-head"><h2>Incoming requests</h2></div><div class="grid">${f.incoming.map(p=>`<section class="panel"><div class="icon-tile">${esc(p.avatar)}</div><h3>${esc(p.display_name)}</h3><p class="meta">@${esc(p.username)} · ${esc(p.rank)}</p><button class="btn" data-accept="${p.request_id}">Accept request</button></section>`).join('')}</div>`:''}
    ${f.outgoing.length?`<div class="section-head"><h2>Pending requests sent</h2></div><div class="grid">${f.outgoing.map(p=>`<section class="panel"><h3>${esc(p.display_name)}</h3><p class="meta">@${esc(p.username)}</p><span class="tag">Pending</span></section>`).join('')}</div>`:''}
    <div class="section-head"><h2>My friends (${f.friends.length})</h2></div><div class="grid">${f.friends.map(p=>`<section class="panel"><div class="row"><div class="icon-tile">${esc(p.avatar)}</div><span class="tag">Level ${p.level}</span></div><h3>${esc(p.display_name)}</h3><p class="meta">@${esc(p.username)} · ${esc(p.rank)}</p><div class="row"><span>XP</span><b>${p.xp}</b></div><div class="row"><span>Current streak</span><b>${p.streak}</b></div><div class="actions"><button class="btn alt" data-remove-friend="${p.id}">Remove friend</button></div></section>`).join('')||'<div class="empty">No friends yet. Search by username above or accept an incoming request.</div>'}</div>
    <div class="section-head"><h2>Friends-only leaderboard</h2><span class="tag">${esc(board.scope)}</span></div><section class="panel"><div class="list">${board.entries.map(p=>`<div class="row"><div class="row" style="justify-content:flex-start"><strong style="min-width:36px">#${p.position}</strong><span class="icon-tile" style="font-size:1.7rem;margin:0">${esc(p.avatar)}</span><div><b>${esc(p.display_name)} ${p.status==='you'?'(you)':''}</b><div class="meta">@${esc(p.username)} · ${esc(p.rank)}</div></div></div><div style="text-align:right"><b>${p.xp} XP</b><div class="meta">Level ${p.level}</div></div></div>`).join('')}</div></section>`;
  const form=document.getElementById('friend-form');
  form.onsubmit=async e=>{e.preventDefault();try{await api('/friends/requests',{method:'POST',body:{username:new FormData(form).get('username')}});toast('Friend request sent.');await friendsPage();}catch(err){toast(err.message);}};
  document.querySelectorAll('[data-accept]').forEach(b=>b.onclick=async()=>{try{await api(`/friends/requests/${b.dataset.accept}/accept`,{method:'POST'});toast('Friend added to your guild.');await friendsPage();}catch(e){toast(e.message);}});
  document.querySelectorAll('[data-remove-friend]').forEach(b=>b.onclick=async()=>{if(!confirm('Remove this friend from your leaderboard?'))return;try{await api(`/friends/${b.dataset.removeFriend}`,{method:'DELETE'});toast('Friend removed.');await friendsPage();}catch(e){toast(e.message);}});
}

/* Profile, theme and account management */
async function profilePage() {
  currentProfile=await api('/profile'); updateHeader();
  const themes=[['light','Blue & Gold','Light'],['dark','Deep Blue','Dark'],['anime','Anime Edition','Anime'],['cute','Soft Blue','Cute']];
  const avatars=['SQ','PY','WEB','AI','DSA','DATA','UI','LAB','DEV','CODE'];
  app.innerHTML=`<div class="row"><div><h1>Profile</h1><p class="lead">Your identity, visual style, and the progress attached to this account.</p></div><section class="panel rank-card"><div class="icon-tile">${esc(currentProfile.avatar)}</div><b>${esc(currentProfile.rank)}</b><div class="meta">Level ${currentProfile.level} · ${currentProfile.xp} XP</div></section></div>
    <div class="cols"><section class="panel"><h2 style="margin-top:0">Profile details</h2><form id="profile-form" class="form-grid"><div class="field"><label for="display_name">Display name</label><input id="display_name" name="display_name" maxlength="30" required value="${esc(currentProfile.display_name)}"></div><div class="field"><label for="avatar">Avatar</label><select id="avatar" name="avatar">${avatars.map(a=>`<option value="${a}" ${a===currentProfile.avatar?'selected':''}>${a}</option>`).join('')}</select></div><div class="field full"><label for="bio">Bio</label><textarea id="bio" name="bio" rows="3" maxlength="180" placeholder="What are you learning right now?">${esc(currentProfile.bio)}</textarea></div><div class="field full"><button class="btn" type="submit">Save profile</button></div></form><hr><div class="row"><div><b>@${esc(currentProfile.username)}</b><div class="meta">${currentProfile.is_guest?'Temporary guest account':'Registered account'} · joined ${esc(currentProfile.joined_at.slice(0,10))}</div></div>${currentProfile.is_guest?'<span class="tag">Guest</span>':'<span class="tag accepted">Registered</span>'}</div>
    <div class="stats"><div class="panel stat"><strong>${currentProfile.completed}</strong><span>Quests completed</span></div><div class="panel stat"><strong>${currentProfile.best_streak}</strong><span>Best streak</span></div></div></section>
    <section class="panel"><h2 style="margin-top:0">Choose your world</h2><p class="muted">Your choice is saved to your profile and follows you between visits.</p><div class="grid">${themes.map(([key,description,name])=>`<button class="card theme-choice" data-theme-choice="${key}" style="text-align:left;cursor:pointer;border-color:${currentProfile.theme===key?'var(--accent)':'var(--line)'}"><div class="theme-swatch ${key}"></div><h3>${name}</h3><p class="muted">${key==='light'?'The original slate-blue and gold palette':key==='dark'?'A deeper blue variation with gold accents':key==='anime'?'Anime-inspired styling in the same palette':'A softer blue variation with white surfaces'}</p>${currentProfile.theme===key?'<span class="tag accepted">Current theme</span>':''}</button>`).join('')}</div><hr><h3>Account access</h3>${currentProfile.is_guest?`<p class="muted">Register to keep your progress under a username and to add friends. Registration preserves the quests and XP from this browser session.</p><form id="register-form" class="stack"><div class="field"><label for="new_username">Choose a username (3–20 letters, numbers or _)</label><input id="new_username" name="username" minlength="3" maxlength="20" pattern="[A-Za-z0-9_]{3,20}" required></div><div class="field"><label for="new_password">Password (at least 8 characters)</label><input id="new_password" name="password" type="password" minlength="8" maxlength="128" required autocomplete="new-password"></div><button class="btn" type="submit">Create account</button></form><hr><h3>Already have an account?</h3><form id="login-form" class="stack"><div class="field"><label for="login_username">Username</label><input id="login_username" name="username" required></div><div class="field"><label for="login_password">Password</label><input id="login_password" name="password" type="password" required autocomplete="current-password"></div><button class="btn alt" type="submit">Sign in</button></form>`:`<p class="muted">Signed in as <b>@${esc(currentProfile.username)}</b>. Your progress is saved to this account.</p><button class="btn alt" id="logout">Sign out and switch account</button>`}</section></div>`;
  document.getElementById('profile-form').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{currentProfile=await api('/profile',{method:'PUT',body:{display_name:f.get('display_name'),bio:f.get('bio'),avatar:f.get('avatar'),theme:document.documentElement.dataset.theme}});applyTheme(currentProfile.theme);updateHeader();toast('Profile saved.');await profilePage();}catch(err){toast(err.message);}};
  document.querySelectorAll('[data-theme-choice]').forEach(b=>b.onclick=async()=>{try{const f=new FormData(document.getElementById('profile-form'));currentProfile=await api('/profile',{method:'PUT',body:{display_name:f.get('display_name')||currentProfile.display_name,bio:f.get('bio')??currentProfile.bio,avatar:f.get('avatar')||currentProfile.avatar,theme:b.dataset.themeChoice}});applyTheme(currentProfile.theme);updateHeader();toast(`${b.dataset.themeChoice[0].toUpperCase()+b.dataset.themeChoice.slice(1)} theme applied.`);await profilePage();}catch(e){toast(e.message);}});
  const registration=document.getElementById('register-form'); if(registration) registration.onsubmit=async e=>{e.preventDefault();const f=new FormData(registration);try{const r=await api('/auth/register',{method:'POST',body:{username:f.get('username'),password:f.get('password'),display_name:currentProfile.display_name}});sessionToken=r.token;localStorage.setItem('sidequestToken',sessionToken);currentProfile=await api('/profile');applyTheme(currentProfile.theme);updateHeader();toast('Account created. Your guest progress came with you.');await profilePage();}catch(err){toast(err.message);}};
  const loginForm=document.getElementById('login-form'); if(loginForm) loginForm.onsubmit=async e=>{e.preventDefault();const f=new FormData(loginForm);try{const r=await api('/auth/login',{method:'POST',body:{username:f.get('username'),password:f.get('password')}});sessionToken=r.token;localStorage.setItem('sidequestToken',sessionToken);currentProfile=await api('/profile');applyTheme(currentProfile.theme);updateHeader();toast(`Welcome back, ${currentProfile.display_name}.`);location.hash='#/';await landing();}catch(err){toast(err.message);}};
  const logout=document.getElementById('logout'); if(logout) logout.onclick=async()=>{try{await api('/auth/logout',{method:'POST'});}catch(_){}sessionToken='';localStorage.removeItem('sidequestToken');currentProfile=await startGuestSession();currentProfile=await api('/profile');applyTheme(currentProfile.theme);updateHeader();toast('Switched to a fresh guest session.');location.hash='#/profile';await profilePage();};
}

const routes={'':landing,discover,quest:questPage,'my-quests':myQuests,dashboard:statsPage,stats:statsPage,goals:goalsPage,roadmaps:roadmapsPage,garden:gardenPage,trending:trendingPage,submissions:submissionsPage,achievements:achievementsPage,friends:friendsPage,profile:profilePage};
async function route() {
  try {
    await authReady;
    const [name='',arg]=location.hash.replace(/^#\/?/,'').split('/');
    navActive(name==='quest'?'discover':name==='dashboard'?'stats':name);
    document.getElementById('nav').classList.remove('open');
    document.getElementById('menu').setAttribute('aria-expanded','false');
    await (routes[name]||landing)(arg);
  } catch (error) {
    app.innerHTML=`<section class="panel"><h2>Something went wrong</h2><p>${esc(error.message)}</p><button class="btn" id="retry">Try again</button></section>`;
    const retry=document.getElementById('retry'); if(retry) retry.onclick=()=>route();
  }
  window.scrollTo(0,0);
}
const authReady=initAuth();
document.getElementById('menu').onclick=()=>{const nav=document.getElementById('nav');nav.classList.toggle('open');document.getElementById('menu').setAttribute('aria-expanded',String(nav.classList.contains('open')));};
window.addEventListener('hashchange',route);
route();
