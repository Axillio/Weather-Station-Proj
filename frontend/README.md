# Weather Station Frontend

Next.js dashboard for the ESP32 weather station.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

The frontend expects the FastAPI backend at:

```text
http://127.0.0.1:8000
```

For Docker/Dokploy, change `NEXT_PUBLIC_API_BASE_URL` in the root `docker-compose.yml`.
