# IPL Crowd Dashboard Frontend

React/Vite dashboard for the IPL crowd management prototype.

## Local Development

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

In local dev, API calls use `API_BASE_URL=/api`. Vite proxies `/api` to `http://localhost:8000`, so run the backend on port `8000`.

## Deployed Backend URL

For static or Cloud Run builds, set:

```text
VITE_BACKEND_URL=https://your-backend-url
```

The app removes a trailing slash automatically.

## Checks

```powershell
npm run lint
npm run test
npm run build
```

## Notes

- Admin endpoints require the backend `ADMIN_API_KEY`; the UI stores the entered key in `sessionStorage`.
- Firebase config values are optional for prototype mode. Set `VITE_FIREBASE_*` values when connecting to a real Firebase project.
