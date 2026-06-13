import { login, handleCallback, getAccessToken, isTokenValid, refreshTokens, logout } from './auth.js';

const API = 'https://<TRACKER_API_ID>.execute-api.ca-central-1.amazonaws.com';

async function apiRequest(method, path, body) {
  if (!isTokenValid()) {
    const ok = await refreshTokens();
    if (!ok) { login(); return null; }
  }
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
      'Content-Type':  'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) { login(); return null; }
  if (!res.ok) throw new Error(`API error ${res.status} on ${method} ${path}`);
  return res.json();
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function computeStreak(days) {
  const todayStr = todayISO();
  const active = days
    .filter(d => d.is_active_day && d.date <= todayStr)
    .sort((a, b) => b.date.localeCompare(a.date));
  let streak = 0;
  for (const d of active) {
    if (d.completed) streak++;
    else break;
  }
  return streak;
}

function weekDaysFor(days, weekNumber) {
  return days.filter(d => d.week_number === weekNumber);
}

function currentWeekNumber(days) {
  const todayStr = todayISO();
  const match = days.find(d => d.date === todayStr);
  if (match) return match.week_number;
  if (todayStr < days[0].date) return 1;
  return days[days.length - 1].week_number;
}

function renderTodayCard(day) {
  const el = document.getElementById('today-card');
  const todayStr = todayISO();

  if (!day) {
    const planStart = '2026-06-15';
    if (todayStr < planStart) {
      el.innerHTML = `<p class="pre-plan">Training begins June 15, 2026. You are ready.</p>`;
    } else {
      el.innerHTML = `<p class="pre-plan">Training plan complete.</p>`;
    }
    return;
  }

  const ratioLine = day.run_walk_ratio
    ? `<span class="detail-chip">${day.run_walk_ratio} run:walk</span>` : '';
  const minutesLine = day.session_minutes_target
    ? `<span class="detail-chip">${day.session_minutes_target} min</span>` : '';

  if (!day.is_active_day) {
    el.innerHTML = `
      <div class="card rest-card">
        <div class="card-type">Rest day</div>
        <p class="card-detail">${day.session_detail}</p>
        <p class="card-meta">Day ${day.day_of_plan} of 105 &mdash; Week ${day.week_number}</p>
      </div>`;
    return;
  }

  el.innerHTML = `
    <div class="card active-card">
      <div class="card-type">${day.session_type}</div>
      <div class="card-chips">${minutesLine}${ratioLine}</div>
      <p class="card-detail">${day.session_detail}</p>
      <p class="card-focus">${day.coaching_focus}</p>
      <p class="card-meta">Day ${day.day_of_plan} of 105 &mdash; Week ${day.week_number} &mdash; ${day.phase}</p>
      <label class="check-row">
        <input type="checkbox" id="today-check" ${day.completed ? 'checked' : ''}>
        <span>Mark complete</span>
      </label>
      <div class="notes-row">
        <textarea id="today-notes" placeholder="Notes...">${day.notes || ''}</textarea>
        <button id="save-notes-btn">Save</button>
      </div>
    </div>`;

  document.getElementById('today-check').addEventListener('change', async e => {
    e.target.disabled = true;
    await apiRequest('PATCH', `/days/${day.date}`, { completed: e.target.checked });
    e.target.disabled = false;
  });

  document.getElementById('save-notes-btn').addEventListener('click', async () => {
    const btn   = document.getElementById('save-notes-btn');
    const notes = document.getElementById('today-notes').value;
    btn.disabled = true;
    btn.textContent = 'Saving...';
    await apiRequest('PATCH', `/days/${day.date}`, { notes });
    btn.textContent = 'Saved';
    setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1500);
  });
}

function renderStats(days) {
  const streak  = computeStreak(days);
  const done    = days.filter(d => d.is_active_day && d.completed).length;
  const pct     = Math.round(done / 75 * 100);

  document.getElementById('streak-count').textContent = streak;
  document.getElementById('progress-fraction').textContent = `${done} / 75`;
  document.getElementById('progress-pct').textContent = `${pct}%`;
  document.getElementById('progress-bar-fill').style.width = `${pct}%`;
}

function renderWeeklyRow(days) {
  const weekNum  = currentWeekNumber(days);
  const weekDays = weekDaysFor(days, weekNum);
  const todayStr = todayISO();
  const el       = document.getElementById('weekly-row');

  if (!weekDays.length) { el.innerHTML = ''; return; }

  const done   = weekDays.filter(d => d.is_active_day && d.completed).length;
  const active = weekDays.filter(d => d.is_active_day).length;
  const focus  = weekDays[0].weekly_focus || '';

  el.innerHTML = `
    <div class="week-meta">
      <span class="week-label">Week ${weekNum}</span>
      <span class="week-focus">${focus}</span>
      <span class="week-adherence">${done} / ${active} active days</span>
    </div>
    <div class="week-grid">
      ${weekDays.map(d => {
        const isToday = d.date === todayStr;
        const cls = [
          'week-cell',
          d.is_active_day ? 'active' : 'rest',
          d.completed ? 'done' : '',
          isToday ? 'today' : '',
        ].filter(Boolean).join(' ');
        const typeShort = d.session_type.split(' ')[0];
        const checkMark = d.is_active_day
          ? `<span class="cell-check">${d.completed ? '[x]' : '[ ]'}</span>`
          : `<span class="cell-check">--</span>`;
        return `
          <div class="${cls}">
            <span class="cell-dow">${d.day_of_week.slice(0, 3)}</span>
            <span class="cell-date">${d.date.slice(5)}</span>
            <span class="cell-type">${typeShort}</span>
            ${checkMark}
          </div>`;
      }).join('')}
    </div>`;
}

function renderWeekSchedule(days) {
  const weekNum  = currentWeekNumber(days);
  const weekDays = weekDaysFor(days, weekNum);
  const todayStr = todayISO();
  const el       = document.getElementById('week-schedule');

  el.innerHTML = weekDays.map(d => {
    const isToday = d.date === todayStr;
    const cls = ['sched-item', isToday ? 'sched-today' : '', !d.is_active_day ? 'sched-rest' : ''].filter(Boolean).join(' ');

    if (!d.is_active_day) {
      return `
        <div class="${cls}">
          <div class="sched-header">
            <span class="sched-dow">${d.day_of_week}</span>
            <span class="sched-date">${d.date.slice(5)}</span>
            <span class="sched-type">Rest</span>
          </div>
          <p class="sched-detail">${d.session_detail}</p>
        </div>`;
    }

    const chips = [
      d.session_minutes_target ? `${d.session_minutes_target} min` : '',
      d.run_walk_ratio         ? `${d.run_walk_ratio} run:walk`    : '',
    ].filter(Boolean).join('  |  ');

    return `
      <div class="${cls}">
        <div class="sched-header">
          <span class="sched-dow">${d.day_of_week}</span>
          <span class="sched-date">${d.date.slice(5)}</span>
          <span class="sched-type">${d.session_type}</span>
          ${d.completed ? '<span class="sched-done">[x]</span>' : ''}
        </div>
        ${chips ? `<p class="sched-chips">${chips}</p>` : ''}
        <p class="sched-detail">${d.session_detail}</p>
        <p class="sched-focus">${d.coaching_focus}</p>
      </div>`;
  }).join('');
}

async function showDashboard(days) {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('dashboard').style.display    = '';
  document.getElementById('logout-btn').addEventListener('click', logout);

  const todayStr = todayISO();
  const todayDay = days.find(d => d.date === todayStr) ?? null;

  renderTodayCard(todayDay);
  renderStats(days);
  renderWeeklyRow(days);
  renderWeekSchedule(days);
}

async function init() {
  const params = new URLSearchParams(window.location.search);

  if (params.has('error')) {
    const desc = params.get('error_description') || params.get('error') || 'Unknown error';
    document.getElementById('app-error').textContent = decodeURIComponent(desc.replace(/\+/g, ' '));
    document.getElementById('app-error').style.display = '';
    return;
  }

  if (params.has('code')) {
    try {
      await handleCallback();
    } catch {
      document.getElementById('app-error').textContent = 'Login failed. Please try again.';
      document.getElementById('app-error').style.display = '';
      return;
    }
  }

  if (!isTokenValid()) {
    const ok = await refreshTokens();
    if (!ok) {
      document.getElementById('login-btn').addEventListener('click', login);
      return;
    }
  }

  const days = await apiRequest('GET', '/days');
  if (!days) return;

  await showDashboard(days);
}

init();
