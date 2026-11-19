// fetch() sends JSON to Flask endpoints; same-origin credentials carry the signed session cookie.
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = {
  me: null, students: [], allSkills: [], selected: new Set(), classOnly: false,
  authMode: 'login', inviteTab: 'received', mailto: '',
  builders: { register: [], profile: [] }
};
const CONTACT_FIELDS = ['email', 'whatsapp', 'instagram', 'linkedin', 'discord', 'github'];

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin', ...options,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) }
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
  return data;
}
const json = (method, body) => ({ method, body: JSON.stringify(body) });
function esc(value = '') {
  return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
function toast(message) {
  const box = $('#toast'); box.textContent = message; box.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => box.classList.remove('show'), 2400);
}
function showModal(id) {
  closePanels(); $('#scrim').classList.add('show'); $(id).classList.add('show'); $(id).setAttribute('aria-hidden', 'false');
  setTimeout(() => $('input:not([type="hidden"]),button', $(id))?.focus(), 50);
}
function closePanels() {
  $('#scrim').classList.remove('show');
  $$('.dialog').forEach(dialog => { dialog.classList.remove('show'); dialog.setAttribute('aria-hidden', 'true'); });
  $('#inviteDrawer').classList.remove('show'); $('#inviteDrawer').setAttribute('aria-hidden', 'true');
}
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === 'dark';
  $('#themeToggle').innerHTML = `<i class="ph ${dark ? 'ph-sun' : 'ph-moon'}"></i>`;
  $('#themeToggle').setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
  document.querySelector('meta[name="theme-color"]').content = dark ? '#111827' : '#FDFDFD';
  try { localStorage.setItem('skillsync-theme', theme); } catch (_) { /* Theme still applies for this visit. */ }
}
function syncNav() {
  $('#authButton').classList.toggle('hidden', !!state.me);
  $('#logoutButton').classList.toggle('hidden', !state.me);
  $('#editButton').classList.toggle('hidden', !state.me);
  $('#classToggle').disabled = !state.me;
  $('#classToggle').setAttribute('aria-pressed', String(state.classOnly));
}
function normalizeSkillName(value) { return value.trim().replace(/\s+/g, ' '); }

function renderBuilder(which) {
  const chips = $(`#${which}SkillChips`);
  const list = state.builders[which];
  chips.innerHTML = list.map((skill, index) => `<span class="skill-chip"><i class="ph ph-sparkle" aria-hidden="true"></i><span>${esc(skill.skill_name)}</span><em>• ${esc(skill.proficiency)}</em><button type="button" data-remove-skill="${which}" data-index="${index}" aria-label="Remove ${esc(skill.skill_name)}"><i class="ph ph-x"></i></button></span>`).join('');
  $(`[data-count="${which}"]`).textContent = `${list.length} / 20`;
}
function renderSkillSuggestions(which, forceOpen = false) {
  const input = $(`#${which}SkillInput`), menu = $(`#${which}SkillSuggestions`);
  const typed = normalizeSkillName(input.value), query = typed.toLocaleLowerCase();
  const added = new Set(state.builders[which].map(item => item.skill_name.toLocaleLowerCase()));
  const matches = state.allSkills.filter(skill => !added.has(skill.toLocaleLowerCase()) && (!query || skill.toLocaleLowerCase().includes(query))).slice(0, 5);
  const addTyped = typed && !added.has(query)
    ? `<button class="suggestion-add" type="button" role="option" data-suggestion="${esc(typed)}" data-builder="${which}"><i class="ph ph-plus"></i><span>Add “${esc(typed)}”</span><small>Custom interest</small></button>` : '';
  const options = matches.map(skill => `<button class="suggestion-option" type="button" role="option" data-suggestion="${esc(skill)}" data-builder="${which}"><i class="ph ph-sparkle"></i><span>${esc(skill)}</span></button>`).join('');
  menu.innerHTML = options + addTyped;
  menu.hidden = !(forceOpen || document.activeElement === input) || (!options && !addTyped);
}
function addSkill(which, customName = null) {
  const input = $(`#${which}SkillInput`), name = normalizeSkillName(customName ?? input.value), level = $(`#${which}SkillLevel`).value;
  if (!name) { input.focus(); return; }
  if (name.length > 64) { toast('Interest names can be up to 64 characters.'); return; }
  if (state.builders[which].length >= 20) { toast('You can add up to 20 interests.'); return; }
  if (state.builders[which].some(item => item.skill_name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    toast('That interest is already on your list.'); input.select(); return;
  }
  state.builders[which].push({ skill_name: name, proficiency: level });
  if (!state.allSkills.some(skill => skill.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    state.allSkills.push(name); state.allSkills.sort((a, b) => a.localeCompare(b));
  }
  input.value = ''; renderBuilder(which); renderSkillSuggestions(which); input.focus();
}
function buildCard(student) {
  const initials = student.name.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase();
  const selected = state.selected.has(student.id);
  const skills = student.skills.map(skill => `<span class="skill-badge" data-level="${esc(skill.proficiency)}"><i class="ph ph-sparkle" aria-hidden="true"></i><span>${esc(skill.skill_name)}</span><em>• ${esc(skill.proficiency)}</em></span>`).join('');
  const methods = [
    { kind: 'Email', icon: 'ph-envelope-simple', value: student.email },
    { kind: 'Instagram', icon: 'ph-instagram-logo', value: student.instagram ? `@${student.instagram.replace(/^@+/, '')}` : '' },
    { kind: 'WhatsApp', icon: 'ph-whatsapp-logo', value: student.whatsapp },
    { kind: 'LinkedIn', icon: 'ph-linkedin-logo', value: student.linkedin },
    { kind: 'Discord', icon: 'ph-discord-logo', value: student.discord },
    { kind: 'GitHub', icon: 'ph-github-logo', value: student.github }
  ].filter(method => method.value);
  const contactButtons = methods.map(method => `<button class="contact-button" type="button" data-copy-value="${esc(method.value)}" data-copy-kind="${method.kind}" aria-label="Copy ${method.kind}: ${esc(method.value)}" title="Copy ${method.kind}: ${esc(method.value)}"><i class="ph ${method.icon}" aria-hidden="true"></i></button>`).join('');
  const match = Number.isFinite(student.match_score) ? `<span class="match"><i class="ph ph-sparkle"></i> ${student.match_score}%</span>` : '';
  return `<article class="student-card">
    <div class="card-top"><div class="avatar">${esc(initials)}</div><div class="student-identity"><h3 class="student-name">${esc(student.name)}</h3><div class="roll">${esc(student.roll_no)}</div></div><span class="year-pill">YEAR ${student.year} · ${esc(student.section)}</span></div>
    <span class="intent" data-intent="${esc(student.intent)}">${esc(student.intent)}</span><p class="bio">${esc(student.bio || 'This student has not added a bio yet.')}</p>
    <div class="badges">${skills || '<span class="skill-badge"><i class="ph ph-sparkle"></i><span>No interests listed</span></span>'}</div>
    <div class="card-bottom"><div class="contact-actions">${contactButtons}</div>${match}<button class="select-peer ${selected ? 'selected' : ''}" type="button" data-select="${student.id}" aria-pressed="${selected}" aria-label="${selected ? 'Remove' : 'Select'} ${esc(student.name)} for study group"><i class="ph ${selected ? 'ph-check' : 'ph-plus'}"></i><span>${selected ? 'Selected' : 'Select'}</span></button></div>
  </article>`;
}
function updateSections() {
  const branch = $('#branchFilter').value, current = $('#sectionFilter').value;
  // The filter stays limited to the two official sections even if old or malformed data appears.
  const branches = branch ? [branch] : ['CSE', 'IT', 'ECE', 'EE', 'ME'];
  const sections = branches.flatMap(name => [`${name}-1`, `${name}-2`]);
  $('#sectionFilter').innerHTML = '<option value="">All sections</option>' + sections.map(section => `<option value="${esc(section)}">${esc(section)}</option>`).join('');
  if (sections.includes(current)) $('#sectionFilter').value = current;
}
function renderStudents() {
  let peers = [...state.students];
  if (state.classOnly && state.me) peers = peers.filter(peer => peer.branch === state.me.branch && peer.section === state.me.section);
  const term = $('#search').value.trim().toLocaleLowerCase();
  if (term) peers = peers.filter(peer => `${peer.name} ${peer.roll_no} ${peer.bio} ${peer.skills.map(skill => skill.skill_name).join(' ')}`.toLocaleLowerCase().includes(term));
  const year = $('#yearFilter').value, branch = $('#branchFilter').value, section = $('#sectionFilter').value;
  const skillName = $('#skillFilter').value.trim().toLocaleLowerCase(), level = $('#levelFilter').value, intent = $('#intentFilter').value;
  peers = peers.filter(peer => (!year || String(peer.year) === year) && (!branch || peer.branch === branch) && (!section || peer.section === section) &&
    (!intent || peer.intent === intent) && (!skillName || peer.skills.some(skill => skill.skill_name.toLocaleLowerCase() === skillName && (!level || skill.proficiency === level))) &&
    (!level || skillName || peer.skills.some(skill => skill.proficiency === level)));
  if ($('#sortMatch').checked) peers.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
  $('#resultSummary').textContent = `${peers.length} ${peers.length === 1 ? 'student' : 'students'} found`;
  $('#studentCount').textContent = state.students.length;
  $('#grid').innerHTML = peers.length ? peers.map(buildCard).join('') : '<div class="empty"><span class="empty-icon"><i class="ph ph-magnifying-glass"></i></span><strong>No students match these filters</strong><span>Clear a filter or try another interest.</span></div>';
}
async function loadDirectory() {
  try {
    const [students, skills] = await Promise.all([api('/api/students'), api('/api/skills')]);
  state.students = students; state.allSkills = skills; updateSections(); renderStudents();
  } catch (error) {
    $('#grid').innerHTML = `<div class="empty"><span class="empty-icon"><i class="ph ph-warning-circle"></i></span><strong>Could not load students</strong><span>${esc(error.message)}</span></div>`;
  }
}
function syncSquad() {
  const count = state.selected.size;
  $('#selectedCount').textContent = `${count} ${count === 1 ? 'peer' : 'peers'} selected`;
  $('#squadBar').classList.toggle('show', count > 0); document.body.classList.toggle('has-squad', count > 0);
  $('#sendInvite').disabled = count < 1 || count > 10;
}
async function refreshInviteCount() {
  if (!state.me) { $('#inviteCount').textContent = '0'; return; }
  try { const invites = await api('/api/invites'); $('#inviteCount').textContent = invites.received.filter(invite => invite.status === 'Pending').length; }
  catch (_) { $('#inviteCount').textContent = '0'; }
}
async function loadSession() {
  state.me = await api('/api/me'); syncNav(); await loadDirectory(); syncSquad(); await refreshInviteCount();
}
function setAuthMode(mode) {
  state.authMode = mode;
  $$('.tab[data-mode]').forEach(tab => tab.classList.toggle('active', tab.dataset.mode === mode));
  $('#registerFields').classList.toggle('hidden', mode !== 'register');
  $('#authTitle').textContent = mode === 'login' ? 'Welcome to SkillSync' : 'Create your student profile';
  $('#authHint').textContent = mode === 'login' ? 'Demo profiles use PIN 1234.' : 'Your year and branch come from your roll number.';
  $('#authSubmit').innerHTML = mode === 'login' ? '<i class="ph ph-sign-in"></i> Log in' : '<i class="ph ph-user-plus"></i> Create profile';
  $('#authError').textContent = '';
  ['name', 'email', 'section'].forEach(name => { $('#authForm').elements[name].required = mode === 'register'; });
  $('#authForm').elements.pin.autocomplete = mode === 'login' ? 'current-password' : 'new-password';
}
function updateRegistrationSections() {
  const input = $('#authForm').elements.roll_no;
  const match = input.value.trim().toUpperCase().match(/^202[3-6]U(CS|IT|EC|EE|ME)\d{4}$/);
  const select = $('#registerSection');
  const branch = match ? ({ CS: 'CSE', EC: 'ECE', IT: 'IT', EE: 'EE', ME: 'ME' })[match[1]] : '';
  const current = select.value;
  select.innerHTML = branch
    ? `<option value="">Choose ${branch} section</option><option>${branch}-1</option><option>${branch}-2</option>`
    : '<option value="">Enter a valid roll number first</option>';
  select.disabled = !branch;
  const badge = $('#registerDetected');
  badge.hidden = !branch;
  if (branch) badge.textContent = `Year ${2026 - Number(input.value.slice(0, 4)) + 1} • ${branch}`;
  if (branch && [ `${branch}-1`, `${branch}-2` ].includes(current)) select.value = current;
}
function formDataObject(form) { return Object.fromEntries(new FormData(form).entries()); }
async function submitAuth(event) {
  event.preventDefault(); $('#authError').textContent = '';
  const values = formDataObject(event.currentTarget);
  if (state.authMode === 'login') {
    try {
      state.me = await api('/api/login', json('POST', { roll_no: values.roll_no, pin: values.pin }));
      closePanels(); syncNav(); state.selected.clear(); await loadDirectory(); syncSquad(); await refreshInviteCount(); toast('You are signed in.');
    } catch (error) { $('#authError').textContent = error.message; }
    return;
  }
  const data = { ...values, skills: state.builders.register };
  try {
    state.me = await api('/api/register', json('POST', data));
    state.builders.register = []; renderBuilder('register'); closePanels(); syncNav(); await loadDirectory(); syncSquad(); await refreshInviteCount(); toast('Your profile is ready.');
  } catch (error) { $('#authError').textContent = error.message; }
}
function openProfile() {
  if (!state.me) return;
  const form = $('#profileForm');
  form.elements.intent.value = state.me.intent;
  CONTACT_FIELDS.forEach(field => { form.elements[field].value = state.me[field] || ''; });
  form.elements.bio.value = state.me.bio || '';
  state.builders.profile = (state.me.skills || []).map(skill => ({ ...skill })); renderBuilder('profile'); showModal('#profileDialog');
}
async function saveProfile(event) {
  event.preventDefault(); $('#profileError').textContent = '';
  const data = { ...formDataObject(event.currentTarget), skills: state.builders.profile };
  try {
    state.me = await api('/api/profile', json('PUT', data)); closePanels(); await loadDirectory(); toast('Profile saved.');
  } catch (error) { $('#profileError').textContent = error.message; }
}
async function openInvites() {
  if (!state.me) { setAuthMode('login'); showModal('#authDialog'); return; }
  closePanels(); $('#scrim').classList.add('show'); $('#inviteDrawer').classList.add('show'); $('#inviteDrawer').setAttribute('aria-hidden', 'false'); await renderInvites();
}
async function renderInvites() {
  const container = $('#inviteList'); container.innerHTML = '<p class="invite-meta">Loading invites…</p>';
  try {
    const data = await api('/api/invites'), rows = data[state.inviteTab];
    container.innerHTML = rows.length ? rows.map(invite => {
      const received = state.inviteTab === 'received';
      const other = received ? `${invite.sender_name} · ${invite.sender_roll}` : `${invite.recipient_name} · ${invite.recipient_roll}`;
      const actions = received && invite.status === 'Pending'
        ? `<div class="invite-actions"><button class="button button-primary" data-response="Accepted" data-id="${invite.id}" type="button"><i class="ph ph-check"></i> Accept</button><button class="button button-secondary" data-response="Declined" data-id="${invite.id}" type="button">Decline</button></div>`
        : `<span class="status ${esc(invite.status)}">${esc(invite.status)}</span>`;
      return `<article class="invite-card"><h3>${esc(invite.group_topic)}</h3><div class="invite-meta">${received ? 'From' : 'To'} ${esc(other)} · ${esc(invite.created_at)}</div>${invite.message ? `<p>${esc(invite.message)}</p>` : ''}${actions}</article>`;
    }).join('') : '<div class="empty"><span class="empty-icon"><i class="ph ph-paper-plane-tilt"></i></span><strong>No invites yet</strong><span>New study invites will appear here.</span></div>';
  } catch (error) { container.innerHTML = `<div class="empty"><strong>Could not load invites</strong><span>${esc(error.message)}</span></div>`; }
}
async function sendInvites() {
  if (!state.me) { setAuthMode('login'); showModal('#authDialog'); return; }
  const topic = $('#groupTopic').value.trim(), message = $('#groupMessage').value.trim();
  if (!topic) { toast('Add a study or project topic first.'); $('#groupTopic').focus(); return; }
  if (!state.selected.size || state.selected.size > 10) { toast('Select between 1 and 10 peers.'); return; }
  try {
    const result = await api('/api/invites', json('POST', { recipient_ids: [...state.selected], group_topic: topic, message }));
    const subject = encodeURIComponent(`SkillSync invite: ${topic}`);
    const body = encodeURIComponent(`Hi! ${state.me.name} invited you to join a study or project group about ${topic}.${message ? `\n\n${message}` : ''}\n\nSent via NSUT SkillSync.`);
    state.mailto = `mailto:${result.recipients.map(peer => peer.email).join(',')}?subject=${subject}&body=${body}`;
    $('#emailLink').classList.remove('hidden'); $('#groupTopic').value = ''; $('#groupMessage').value = '';
    toast(`Invite sent to ${result.recipients.length} ${result.recipients.length === 1 ? 'peer' : 'peers'}.`);
    await refreshInviteCount();
  } catch (error) { toast(error.message); }
}
async function copyText(value, kind) {
  try { await navigator.clipboard.writeText(value); }
  catch (_) {
    const input = document.createElement('textarea'); input.value = value; input.style.position = 'fixed'; input.style.opacity = '0';
    document.body.append(input); input.select(); document.execCommand('copy'); input.remove();
  }
  toast(`Copied ${kind} (${value})`);
}

document.addEventListener('click', async event => {
  const button = event.target.closest('button'); if (!button) return;
  if (button.hasAttribute('data-close')) { closePanels(); return; }
  if (button.dataset.mode) { setAuthMode(button.dataset.mode); return; }
  if (button.dataset.addSkill) { addSkill(button.dataset.addSkill); return; }
  if (button.dataset.suggestion) {
    const which = button.dataset.builder;
    const input = $(`#${which}SkillInput`);
    input.value = button.dataset.suggestion;
    $(`#${which}SkillSuggestions`).hidden = true;
    return;
  }
  if (button.dataset.removeSkill) {
    state.builders[button.dataset.removeSkill].splice(Number(button.dataset.index), 1); renderBuilder(button.dataset.removeSkill); return;
  }
  if (button.id === 'authButton') { setAuthMode('login'); showModal('#authDialog'); }
  if (button.id === 'themeToggle') setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  if (button.id === 'logoutButton') {
    try { await api('/api/logout', { method: 'POST' }); state.me = null; state.classOnly = false; state.selected.clear(); syncNav(); closePanels(); syncSquad(); await loadDirectory(); await refreshInviteCount(); toast('You are signed out.'); }
    catch (error) { toast(error.message); }
  }
  if (button.id === 'editButton') openProfile();
  if (button.id === 'invitesButton') openInvites();
  if (button.id === 'classToggle' && state.me) { state.classOnly = !state.classOnly; syncNav(); renderStudents(); }
  if (button.id === 'clearFilters') {
    ['search', 'yearFilter', 'branchFilter', 'sectionFilter', 'skillFilter', 'levelFilter', 'intentFilter'].forEach(id => { $(`#${id}`).value = ''; });
    $('#sortMatch').checked = false; state.classOnly = false; syncNav(); updateSections(); renderStudents();
  }
  if (button.id === 'sendInvite') sendInvites();
  if (button.id === 'emailLink' && state.mailto) window.location.href = state.mailto;
  if (button.dataset.copyValue) copyText(button.dataset.copyValue, button.dataset.copyKind);
  if (button.dataset.select) {
    const id = Number(button.dataset.select);
    if (!state.selected.has(id) && state.selected.size >= 10) { toast('You can select up to 10 peers.'); return; }
    state.selected.has(id) ? state.selected.delete(id) : state.selected.add(id);
    renderStudents(); syncSquad();
  }
  if (button.dataset.inviteTab) {
    state.inviteTab = button.dataset.inviteTab;
    $$('[data-invite-tab]').forEach(tab => tab.classList.toggle('active', tab === button)); await renderInvites();
  }
  if (button.dataset.response) {
    try { await api(`/api/invites/${button.dataset.id}`, json('PUT', { status: button.dataset.response })); await renderInvites(); await refreshInviteCount(); }
    catch (error) { toast(error.message); }
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closePanels();
  if (event.key === 'Enter' && ['registerSkillInput', 'profileSkillInput'].includes(event.target.id)) {
    event.preventDefault(); addSkill(event.target.id.startsWith('register') ? 'register' : 'profile');
  }
  if (event.key === 'Escape' && ['registerSkillInput', 'profileSkillInput'].includes(event.target.id)) {
    const which = event.target.id.startsWith('register') ? 'register' : 'profile'; renderSkillSuggestions(which, false);
  }
});
['register', 'profile'].forEach(which => {
  const input = $(`#${which}SkillInput`);
  input.addEventListener('focus', () => renderSkillSuggestions(which, true));
  input.addEventListener('input', () => renderSkillSuggestions(which, true));
  input.addEventListener('blur', () => setTimeout(() => renderSkillSuggestions(which, false), 120));
  $(`#${which}SkillSuggestions`).addEventListener('mousedown', event => event.preventDefault());
});
document.addEventListener('change', event => {
  if (['yearFilter', 'branchFilter', 'sectionFilter', 'skillFilter', 'levelFilter', 'intentFilter', 'sortMatch'].includes(event.target.id)) {
    if (event.target.id === 'branchFilter') updateSections();
    renderStudents();
  }
});
$('#search').addEventListener('input', renderStudents);
$('#scrim').addEventListener('click', closePanels);
$('#authForm').addEventListener('submit', submitAuth);
$('#profileForm').addEventListener('submit', saveProfile);
$('#authForm').elements.roll_no.addEventListener('input', updateRegistrationSections);
$('#clearSelection').addEventListener('click', () => { state.selected.clear(); renderStudents(); syncSquad(); $('#emailLink').classList.add('hidden'); state.mailto = ''; });
try { setTheme(localStorage.getItem('skillsync-theme') || 'light'); } catch (_) { setTheme('light'); }
renderBuilder('register'); renderBuilder('profile'); updateRegistrationSections(); setAuthMode('login');
loadSession().catch(async () => { syncNav(); await loadDirectory(); syncSquad(); });
