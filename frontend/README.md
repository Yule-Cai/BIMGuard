# Frontend — BIMGuard

Two modes:

## 1) No-build static demo (recommended for 7-day test)

Served by FastAPI at `http://localhost:8000/` — no `npm install` needed.

- File: `frontend/static.html` (single-file, CDN Tailwind + Three.js via importmap)
- Uses same API: `/api/upload`, `/api/summary`, `/api/chat`, `/api/elements`
- Works even when npm registry is slow.

## 2) React + Vite + Three.js (engineering taste)

Full UI in `frontend/src/`:

- `App.jsx` — layout, upload, score
- `components/Viewer.jsx` — Three.js via @react-three/fiber + drei, box placeholders by placement (IFC→GLB ready)
- `components/IssuesPanel.jsx` — Locate + Explain
- `components/ChatPanel.jsx` — Ask BIMGuard

Run:

```bash
cd frontend
npm install --registry https://registry.npmmirror.com  # or https://registry.npmjs.org
npm run dev   # http://localhost:5173  (proxies /api to :8000)
npm run build # → dist/  (served by FastAPI at /app if present)
```

If `npm install` hangs due to network, use static demo — reviewers can still evaluate fully.
