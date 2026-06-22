# SCADA Deploy Test — Quick Start

ทดสอบ chain: **GitHub Pages → Cloudflare Worker → Cloudflare Tunnel → Local FastAPI → PostgreSQL**

```
[Browser]
   |
   v
[GitHub Pages]  (index.html, static)
   |  fetch(WORKER_URL + "/health", "/db-check")
   v
[Cloudflare Worker]  (proxy, hides tunnel URL, fixes CORS)
   |  forwards to TUNNEL_URL
   v
[Cloudflare Tunnel]  (cloudflared, running on your local machine)
   |
   v
[FastAPI backend]  (localhost:8000)
   |  psycopg2
   v
[PostgreSQL]
```

---

## Step 1 — Backend (เครื่อง local ที่มี PostgreSQL)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# แก้ DB credentials — ใช้ env var (แนะนำ) หรือแก้ default ใน main.py
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=yourpassword

uvicorn main:app --host 0.0.0.0 --port 8000
```

ทดสอบในเครื่องก่อน:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/db-check
```

`/db-check` ควร return `{"status": "success", "message": "Connected OK in ...ms. PostgreSQL ..."}`

---

## Step 2 — Cloudflare Tunnel (เปิด local backend ออกสู่อินเทอร์เน็ต)

ติดตั้ง `cloudflared` ([docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/)):

```bash
# วิธีเร็วที่สุดสำหรับทดสอบ (Quick Tunnel, ไม่ต้อง login/domain)
cloudflared tunnel --url http://localhost:8000
```

จะได้ URL แบบ `https://random-words.trycloudflare.com` — **เอา URL นี้ไปใส่ใน Worker** (Step 3)

> Quick Tunnel เหมาะกับทดสอบเฉยๆ — URL จะเปลี่ยนทุกครั้งที่รันใหม่ ถ้าต้องการ URL คงที่ ให้ตั้ง **Named Tunnel** ผูกกับ domain ที่มีอยู่ใน Cloudflare account (ดู docs ด้านบน)

---

## Step 3 — Cloudflare Worker (deploy proxy)

```bash
cd worker
npm install -g wrangler   # ถ้ายังไม่มี
wrangler login
```

แก้ `wrangler.toml` ใส่ TUNNEL_URL จาก Step 2:
```toml
[vars]
TUNNEL_URL = "https://random-words.trycloudflare.com"
```

Deploy:
```bash
wrangler deploy
```

จะได้ Worker URL แบบ `https://scada-deploy-test.yourname.workers.dev` — **เอา URL นี้ไปใส่ในหน้าเว็บ** (Step 4)

ทดสอบ Worker ตรงๆ:
```bash
curl https://scada-deploy-test.yourname.workers.dev/health
```

---

## Step 4 — Frontend (GitHub Pages)

1. Push โฟลเดอร์ `frontend/` (มีแค่ `index.html`) ไปที่ repo บน GitHub
2. ไปที่ repo → **Settings → Pages** → Source: เลือก branch + โฟลเดอร์ที่มี `index.html`
3. รอ 1-2 นาที จะได้ URL แบบ `https://yourname.github.io/repo-name/`
4. เปิดหน้าเว็บ → ใส่ Worker URL จาก Step 3 ในช่อง input → กด **Run test**

---

## เช็คทีละจุดถ้ามีปัญหา

| ปัญหา | เช็คที่ |
|---|---|
| `/health` fail ที่ frontend แต่ curl ตรงๆได้ | CORS — เช็ค response headers จาก Worker |
| Worker คืน 502 "could not reach tunnel" | Tunnel ตายหรือ URL ใน `wrangler.toml` ไม่ตรง — เช็ค `cloudflared` ยังรันอยู่ไหม |
| `/db-check` fail แต่ `/health` ผ่าน | ปัญหาที่ DB เอง — credentials, firewall, PostgreSQL ไม่ accept connection จาก localhost (เช็ค `pg_hba.conf` และ `listen_addresses` ใน `postgresql.conf`) |
| Worker deploy ไม่ผ่าน | เช็ค `wrangler login` แล้วหรือยัง, account มี Workers enabled ไหม |

---

## ไฟล์ในโปรเจกต์นี้

```
scada-test/
├── backend/
│   ├── main.py            # FastAPI app: /health, /db-check
│   ├── requirements.txt
│   └── .env.example
├── worker/
│   ├── worker.js           # Cloudflare Worker proxy
│   └── wrangler.toml
└── frontend/
    └── index.html          # หน้าทดสอบ (deploy ที่ GitHub Pages)
```
