const availabilityForm = document.getElementById('availability-form');
const reservationForm = document.getElementById('reservation-form');
const waitlistForm = document.getElementById('waitlist-form');
const slotsEl = document.getElementById('slots');
const reservationAtEl = document.getElementById('reservationAt');
const desiredAtEl = document.getElementById('desiredAt');
const resultEl = document.getElementById('result');

const params = new URLSearchParams(window.location.search);
const today = new Date().toISOString().slice(0, 10);

availabilityForm.elements.restaurantId.value = params.get('restaurantId') || availabilityForm.elements.restaurantId.value;
availabilityForm.elements.partySize.value = params.get('partySize') || availabilityForm.elements.partySize.value;
availabilityForm.elements.date.value = params.get('date') || today;
reservationForm.elements.restaurantId.value = availabilityForm.elements.restaurantId.value;
reservationForm.elements.partySize.value = availabilityForm.elements.partySize.value;
waitlistForm.elements.restaurantId.value = availabilityForm.elements.restaurantId.value;
waitlistForm.elements.partySize.value = availabilityForm.elements.partySize.value;

function setResult(data) {
  resultEl.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

availabilityForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(availabilityForm);
  const query = new URLSearchParams(fd).toString();

  const response = await fetch(`/availability?${query}`);
  const data = await response.json();

  slotsEl.innerHTML = '';
  data.slots.forEach((slot) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `slot-btn ${slot.available ? '' : 'slot-unavailable'}`.trim();
    btn.textContent = new Date(slot.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    btn.addEventListener('click', () => {
      document.querySelectorAll('.slot-btn').forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');
      desiredAtEl.value = slot.startTime;
      waitlistForm.elements.restaurantId.value = fd.get('restaurantId');
      waitlistForm.elements.partySize.value = fd.get('partySize');

      if (slot.available) {
        reservationAtEl.value = slot.startTime;
        reservationForm.elements.restaurantId.value = fd.get('restaurantId');
        reservationForm.elements.partySize.value = fd.get('partySize');
      } else {
        reservationAtEl.value = '';
      }
    });
    slotsEl.appendChild(btn);
  });

  setResult(data);
});

reservationForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(reservationForm);
  const payload = Object.fromEntries(fd.entries());
  payload.partySize = Number(payload.partySize);

  const response = await fetch('/reservations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  setResult(data);
});

waitlistForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(waitlistForm);
  const payload = Object.fromEntries(fd.entries());
  payload.partySize = Number(payload.partySize);

  const response = await fetch('/waitlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  setResult(data);
});
