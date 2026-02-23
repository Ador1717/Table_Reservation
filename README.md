# Restaurant Reservation Platform (Fork-style Architecture)

This repository includes a working **MVP reservation system**:

- A backend API for availability + reservation lifecycle.
- A website widget demo customers can use to reserve.
- A reusable embeddable plugin script for integrating on any site.
- Local SQLite persistence for bookings and waitlist.

## Run locally

```bash
python -m unittest discover -s tests
export ADMIN_API_KEY="change-me-admin-key"  # optional fallback key
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="change-me-admin-password"
export WHATSAPP_WEBHOOK_URL="https://your-whatsapp-relay.example.com/send"  # required to send WhatsApp summary
export WHATSAPP_RECIPIENT="+971500000000"  # optional metadata passed to your relay
python3 -m app.server
```

Then open:

- `http://localhost:8000/web/` (standalone widget demo)
- `http://localhost:8000/web/embed-example.html` (plugin embed demo)
- `http://localhost:8000/web/admin.html` (admin dashboard demo with reservations, waitlist, analytics)

## Embedding plugin on your website

```html
<div id="reservation-plugin-root"></div>
<script src="https://your-reservation-domain.com/web/plugin.js"></script>
<script>
  ReservationWidget.mount({
    target: '#reservation-plugin-root',
    apiBaseUrl: 'https://your-reservation-domain.com',
    restaurantId: 'resto-main',
    partySize: 2,
    height: 820
  });
</script>
```

Direct booking link option (no embed):

```text
https://your-reservation-domain.com/web/?restaurantId=resto-main&partySize=2&date=2026-03-15
```

## Admin authentication

Admin endpoints require either:

- `Authorization: Bearer <token>` from `POST /admin/login`, or
- fallback header `X-Admin-Key` matching `ADMIN_API_KEY`.

Admin endpoints:

- `GET /reservations`
- `PATCH /reservations/{reservationId}`
- `DELETE /reservations/{reservationId}`
- `GET /waitlist`
- `GET /analytics`
- `GET /notifications/whatsapp/config`
- `POST /notifications/whatsapp/daily-summary`
- `POST /admin/login` (creates admin session token)
- `GET /admin/users`
- `POST /admin/users`

Public booking endpoints remain open for customer flows (`/availability`, `POST /reservations`, `POST /waitlist`). The admin dashboard supports login and then uses bearer tokens automatically.

## Implemented API endpoints

- `GET /availability?restaurantId=...&date=YYYY-MM-DD&partySize=...`
- `GET /reservations?restaurantId=...&date=YYYY-MM-DD`
- `POST /reservations`
- `PATCH /reservations/{reservationId}`
- `DELETE /reservations/{reservationId}`
- `POST /waitlist`
- `GET /waitlist?restaurantId=...&date=YYYY-MM-DD`
- `GET /analytics?restaurantId=...&date=YYYY-MM-DD`
- `GET /notifications/whatsapp/config`
- `POST /notifications/whatsapp/daily-summary`
- `POST /admin/login`
- `GET /admin/users`
- `POST /admin/users`

## Waitlist auto-promotion

If a slot is full, guests can join the waitlist for a desired time. When an active reservation is cancelled or moved out of service flow (`pending`/`confirmed`/`seated`), the earliest matching waitlist entry is automatically promoted to a new pending reservation.

## Project structure

- `app/server.py` — HTTP server + REST endpoints.
- `app/reservation_store.py` — reservation + waitlist logic with SQLite persistence.
- `web/index.html` — standalone widget page.
- `web/plugin.js` — embeddable plugin SDK.
- `web/embed-example.html` — host-site embed example.
- `web/widget.js` — client-side booking + waitlist flow.
- `web/admin.html` and `web/admin.js` — admin reservations + waitlist dashboard.
- `tests/test_store.py` — core booking and waitlist promotion tests.

## Next steps

1. Add additional notification channels (email/SMS) if needed; WhatsApp daily summary is now available.
2. Keep auth simple for now; expand to advanced role/permissions later.
3. Build mobile app using the same API.
