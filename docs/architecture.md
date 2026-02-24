# Architecture Blueprint: Restaurant Reservation Platform

## 1) Product goals

Build a reservation system similar in flow to TheFork, but tailored for your restaurant:

- Website visitors can find available times and reserve instantly.
- Staff can manage floor capacity, shifts, and customer requests.
- Backend is API-first so a mobile app can be added later with minimal rework.

---

## 2) High-level architecture

```text
Customer Website
  └─ Reservation Plugin (JS widget / iframe)
      └─ API Gateway
          ├─ Auth Service
          ├─ Reservation Service
          ├─ Availability Engine
          ├─ Notification Service
          ├─ CRM / Guest Profile Service
          └─ Reporting Service
                └─ Database (PostgreSQL)

Future Mobile App (iOS/Android)
  └─ Uses same API Gateway + services

Admin Dashboard (Web)
  └─ Uses same API Gateway + services
```

### Why this is important

If both website plugin and future mobile app use the same APIs, you avoid building two separate systems.

---

## 3) Domain model (core entities)

- **Restaurant**: venue details, timezone, opening hours.
- **Table**: size/capacity, section, merge rules.
- **Shift**: lunch/dinner windows and booking policy.
- **Reservation**: customer, party size, datetime, status.
- **Guest**: contact info, preferences, visit history.
- **Availability Rule**: lead time, slot interval, max covers.
- **Notification**: confirmations, reminders, updates.

### Reservation statuses

- `pending`
- `confirmed`
- `seated`
- `completed`
- `cancelled`
- `no_show`

---

## 4) Recommended backend modules

## 4.1 Reservation Service

Responsibilities:

- Create/update/cancel reservation.
- Validate business rules.
- Emit events (`reservation.created`, `reservation.cancelled`).

## 4.2 Availability Engine

Responsibilities:

- Calculate available slots from capacity + existing bookings + rules.
- Support “next best available times” suggestions.

## 4.3 Notification Service

Responsibilities:

- Send confirmation/reminder via email/SMS/WhatsApp.
- Retry + delivery tracking.

## 4.4 Guest/CRM Service

Responsibilities:

- Maintain guest profile and tags (VIP, allergy notes, no-show risk).
- Attach notes to reservations.

## 4.5 Admin Dashboard API

Responsibilities:

- Floor/shift management.
- Calendar/day view.
- Manual booking and walk-ins.

---

## 5) Plugin architecture (website integration)

Provide two integration options:

1. **Hosted widget (iframe)**
   - Easiest to integrate.
   - Centralized updates.
2. **JS SDK + custom UI**
   - More brand control.
   - Requires stronger frontend maintenance.

### Minimum widget flow

1. Customer opens widget.
2. Widget requests available slots.
3. Customer selects date/time/party size.
4. Widget submits reservation.
5. Backend sends confirmation + optional OTP.

---

## 6) Mobile app readiness strategy

Design now for mobile usage later:

- Versioned REST API (`/v1/...`).
- Token-based auth with role scopes.
- Push notification events planned in event model.
- Keep response payloads consistent and documented in OpenAPI.

---

## 7) Data layer recommendation

**Primary DB:** PostgreSQL

- Strong relational consistency for booking integrity.
- Supports transactions to prevent overbooking.

**Optional cache:** Redis

- Cache availability queries for popular hours.
- Rate limiting and temporary holds.

### Anti-overbooking rules

- Use transaction + row locking for slot allocation.
- Short-lived “reservation hold” before final confirmation.
- Idempotency key on create reservation endpoint.

---

## 8) Security & compliance baseline

- TLS everywhere.
- Encrypt PII at rest where possible.
- Consent tracking for marketing messages.
- Role-based access control for staff/admin.
- Audit log for booking modifications.

---

## 9) Deployment strategy

- Containerized services.
- CI/CD pipeline with test + security scan.
- Staging environment mirrors production.
- Observability stack: logs, metrics, tracing.

---

## 10) MVP scope (first release)

Must-have:

- Reservation widget on website.
- Availability endpoint.
- Reservation create/cancel.
- Admin day view + manual confirm.
- Confirmation + reminder notifications.

Later phases:

- Waitlist.
- Dynamic seating optimization.
- Multi-branch support.
- Mobile apps for owner/staff.

