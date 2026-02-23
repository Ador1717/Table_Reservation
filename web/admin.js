const loginForm = document.getElementById('admin-login-form');
const filterForm = document.getElementById('admin-filter-form');
const staffCreateForm = document.getElementById('staff-create-form');

const tableBody = document.getElementById('admin-table-body');
const waitlistTableBody = document.getElementById('waitlist-table-body');
const analyticsGrid = document.getElementById('analytics-grid');
const staffUsersBody = document.getElementById('staff-users-body');

const resultEl = document.getElementById('admin-result');
const authStatusEl = document.getElementById('auth-status');

let accessToken = null;

filterForm.elements.date.value = new Date().toISOString().slice(0, 10);

function setResult(data) {
  resultEl.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

function authHeaders(withJson = false) {
  const headers = {};
  if (withJson) headers['Content-Type'] = 'application/json';

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  } else {
    headers['X-Admin-Key'] = filterForm.elements.adminKey.value;
  }

  return headers;
}

function statusActions(reservation) {
  const transitions = ['confirmed', 'seated', 'completed', 'cancelled', 'no_show'];
  return transitions
    .filter((status) => status !== reservation.status)
    .map((status) => `<button data-id="${reservation.id}" data-status="${status}">${status}</button>`)
    .join(' ');
}

function renderRows(reservations) {
  tableBody.innerHTML = '';
  reservations.forEach((reservation) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${reservation.id}</td>
      <td>${new Date(reservation.reservationAt).toLocaleString()}</td>
      <td>${reservation.guestName}</td>
      <td>${reservation.partySize}</td>
      <td><span class="status-badge status-${reservation.status}">${reservation.status}</span></td>
      <td class="admin-actions">${statusActions(reservation)}</td>
    `;
    tableBody.appendChild(tr);
  });
}

function renderWaitlistRows(entries) {
  waitlistTableBody.innerHTML = '';
  entries.forEach((entry) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${entry.id}</td>
      <td>${new Date(entry.desiredAt).toLocaleString()}</td>
      <td>${entry.guestName}</td>
      <td>${entry.partySize}</td>
      <td><span class="status-badge status-${entry.status}">${entry.status}</span></td>
    `;
    waitlistTableBody.appendChild(tr);
  });
}

function renderAnalytics(analytics) {
  analyticsGrid.innerHTML = '';
  const cards = [
    ['Total Reservations', analytics.totalReservations],
    ['Total Covers', analytics.totalCovers],
    ['Completed', analytics.completedReservations],
    ['Cancelled', analytics.cancelledReservations],
    ['No Shows', analytics.noShowReservations],
    ['Cancellation Rate', `${(analytics.cancellationRate * 100).toFixed(1)}%`],
    ['No-show Rate', `${(analytics.noShowRate * 100).toFixed(1)}%`],
    ['Waitlist Waiting', analytics.waitlistWaiting],
    ['Waitlist Promoted', analytics.waitlistPromoted],
  ];

  cards.forEach(([label, value]) => {
    const card = document.createElement('div');
    card.className = 'analytics-card';
    card.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    analyticsGrid.appendChild(card);
  });
}

function renderStaffUsers(users) {
  staffUsersBody.innerHTML = '';
  users.forEach((user) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${user.username}</td>
      <td>${user.role}</td>
      <td>${new Date(user.createdAt).toLocaleString()}</td>
    `;
    staffUsersBody.appendChild(tr);
  });
}

function buildAdminQuery() {
  const fd = new FormData(filterForm);
  fd.delete('adminKey');
  return new URLSearchParams(fd).toString();
}

async function loadReservations() {
  const response = await fetch(`/reservations?${buildAdminQuery()}`, { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    setResult(data);
    tableBody.innerHTML = '';
    return { ok: false };
  }
  renderRows(data.reservations);
  return { ok: true, data };
}

async function loadWaitlist() {
  const response = await fetch(`/waitlist?${buildAdminQuery()}`, { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    setResult(data);
    waitlistTableBody.innerHTML = '';
    return { ok: false };
  }
  renderWaitlistRows(data.entries);
  return { ok: true, data };
}

async function loadAnalytics() {
  const response = await fetch(`/analytics?${buildAdminQuery()}`, { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    setResult(data);
    analyticsGrid.innerHTML = '';
    return { ok: false };
  }
  renderAnalytics(data);
  return { ok: true, data };
}

async function loadStaffUsers() {
  const response = await fetch('/admin/users', { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    setResult(data);
    staffUsersBody.innerHTML = '';
    return { ok: false };
  }
  renderStaffUsers(data.users);
  return { ok: true, data };
}

async function loadOperationsView() {
  const reservationResult = await loadReservations();
  if (!reservationResult.ok) return;

  const waitlistResult = await loadWaitlist();
  if (!waitlistResult.ok) return;

  const analyticsResult = await loadAnalytics();
  if (!analyticsResult.ok) return;

  const staffResult = await loadStaffUsers();
  if (!staffResult.ok) return;

  setResult({
    reservations: reservationResult.data.reservations,
    waitlist: waitlistResult.data.entries,
    analytics: analyticsResult.data,
    users: staffResult.data.users,
  });
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = Object.fromEntries(new FormData(loginForm).entries());

  const response = await fetch('/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  setResult(data);

  if (!response.ok) {
    accessToken = null;
    authStatusEl.textContent = 'Login failed. Using API key fallback.';
    return;
  }

  accessToken = data.accessToken;
  authStatusEl.textContent = `Logged in as ${data.user.username}`;
  await loadOperationsView();
});

staffCreateForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = Object.fromEntries(new FormData(staffCreateForm).entries());

  const response = await fetch('/admin/users', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  setResult(data);
  if (response.ok) {
    staffCreateForm.reset();
    await loadStaffUsers();
  }
});

filterForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  await loadOperationsView();
});

tableBody.addEventListener('click', async (e) => {
  const button = e.target.closest('button[data-id][data-status]');
  if (!button) return;

  const reservationId = button.dataset.id;
  const status = button.dataset.status;

  const response = await fetch(`/reservations/${reservationId}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify({ status }),
  });

  const data = await response.json();
  setResult(data);
  if (response.ok) {
    await loadOperationsView();
  }
});

loadOperationsView();
