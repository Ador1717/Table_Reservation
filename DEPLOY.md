# Deploy to Render

Follow these steps to deploy the Table Reservation app to [Render](https://render.com).

## 1. Push your branch (if needed)

Your repo is at **https://github.com/Ador1717/Table_Reservation**.  
Deploy from this branch or merge to `main` first:

```bash
git push origin codex/build-restaurant-reservation-system-903e81
```

## 2. Create a Render account and connect GitHub

- Go to [dashboard.render.com](https://dashboard.render.com).
- Sign up or log in and connect your **GitHub** account (Settings → Account → Connect GitHub).

## 3. Deploy with Blueprint

1. In Render: **New +** → **Blueprint**.
2. Connect the repo **Ador1717/Table_Reservation** (one-time GitHub auth if needed).
3. Select the branch to deploy, e.g. **codex/build-restaurant-reservation-system-903e81** (or `main` after merge).
4. Render will read `render.yaml` and create the **table-reservation** web service.

## 4. Add secret environment variables

In the **table-reservation** service → **Environment** tab, set these as **Secret** (not plain env):

| Variable | Required | Example / note |
|----------|----------|----------------|
| `ADMIN_API_KEY` | Yes | Pick a long random string (e.g. for `X-Admin-Key` header). |
| `ADMIN_PASSWORD` | Yes | Admin dashboard login password. |
| `WHATSAPP_WEBHOOK_URL` | No* | Your WhatsApp relay URL, e.g. `https://your-relay.example.com/send`. Leave empty if not using WhatsApp. |

\* Required only if you want WhatsApp daily summary. Otherwise leave empty or omit.

`ADMIN_USERNAME` and `WHATSAPP_RECIPIENT` are already set in `render.yaml` (admin / 0617461487). Override in Environment if you want different values.

## 5. Deploy and open the app

- Click **Deploy** (or let the first deploy run automatically).
- When the build and deploy succeed, open:
  - **Widget:** `https://<your-service>.onrender.com/web/`
  - **Admin:** `https://<your-service>.onrender.com/web/admin.html`
- Log in with `ADMIN_USERNAME` (default `admin`) and the `ADMIN_PASSWORD` you set.

## Free tier note

On the free plan the service may spin down after inactivity; the first request after idle can take a minute to wake up.
