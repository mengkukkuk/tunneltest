# SCADA Deploy Test — Quick Start (Cloudflare เท่านั้น)

ทดสอบ chain ทั้งหมดด้วย **Cloudflare เพียงตัวเดียว** ไม่ใช้ GitHub Pages — ฟรี 100% ไม่ต้องซื้อโดเมน:

**Cloudflare Pages → Cloudflare Worker → Cloudflare Tunnel → Local FastAPI → Database (PostgreSQL หรือ MSSQL)**

```
[Browser]
   |
   v
[Cloudflare Pages]  (index.html, static — *.pages.dev)
   |  fetch(WORKER_URL + "/health", "/db-check")
   v
[Cloudflare Worker]  (proxy, hides tunnel URL, fixes CORS — *.workers.dev)
   |  forwards to TUNNEL_URL
   v
[Cloudflare Tunnel]  (cloudflared, running on your local machine)
   |
   v
[FastAPI backend]  (localhost:8000)
   |  psycopg2 (PostgreSQL) หรือ pyodbc (MSSQL)
   v
[Database]
```

ทุกชั้นเป็น Cloudflare หมด ใช้ account เดียว ไม่ต้องมี GitHub repo เลยก็ได้ (ถึงจะ deploy ผ่าน `wrangler` หรือลาก-วางไฟล์ใน dashboard ก็ทำได้)

มี backend สองเวอร์ชันในโฟลเดอร์ `backend/` — เลือกใช้ตัวที่ตรงกับ database จริง:

| ไฟล์ | Database | Driver |
|---|---|---|
| `main.py` | PostgreSQL | psycopg2 |
| `main_mssql.py` | MSSQL (SQL Server) | pyodbc |

ทั้งสองตัวมี endpoint เหมือนกัน (`/health`, `/db-check`) ใช้กับ Worker/Frontend ตัวเดียวกันได้เลย ไม่ต้องแก้อะไรฝั่ง frontend

---

## Step 0 — สมัคร Cloudflare account (ทำครั้งเดียว)

1. ไปที่ [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) → สมัครด้วย email ฟรี ไม่ต้องผูกบัตรเครดิต
2. Login เข้า dashboard → ไปที่เมนู **Workers & Pages** ทางซ้าย
3. ครั้งแรกที่เข้า ระบบจะให้ตั้งชื่อ **workers.dev subdomain** ของตัวเอง เช่น `mengkukkuk` → subdomain ทั้งหมดจะอยู่ในรูป `xxx.mengkukkuk.workers.dev`
4. ติดตั้ง Wrangler CLI (ตัวจัดการ deploy จากเครื่อง local):
   ```bash
   npm install -g wrangler
   wrangler login
   ```
   จะเปิด browser ให้ login ครั้งเดียว ครั้งต่อไปไม่ต้อง login ซ้ำ

---

## Step 1a — Backend: PostgreSQL

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

## Step 1b — Backend: MSSQL (ใช้แทน Step 1a ถ้า database คือ SQL Server)

**ก่อนเริ่ม ต้องมี ODBC Driver for SQL Server ติดตั้งในเครื่องที่รัน backend:**

- **Windows:** มักมีอยู่แล้ว หรือดาวน์โหลด [ODBC Driver 17/18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) จาก Microsoft
- **Linux (Ubuntu/Debian):**
  ```bash
  curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
  curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
  sudo apt-get update
  ACCEPT_EULA=Y sudo apt-get install -y msodbcsql17 unixodbc-dev
  ```

ติดตั้ง dependencies และรัน:

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements_mssql.txt

# แก้ DB credentials — ดูตัวอย่างใน .env.mssql.example
export DB_SERVER="localhost\SQLEXPRESS"   # หรือ "localhost,1433" ถ้าใช้ default instance/port
export DB_NAME=master
export DB_USER=sa
export DB_PASSWORD=yourpassword
export DB_DRIVER="ODBC Driver 17 for SQL Server"
export DB_TRUST_CERT=yes

uvicorn main_mssql:app --host 0.0.0.0 --port 8000
```

ทดสอบในเครื่องก่อน:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/db-check
```

`/db-check` ควร return `{"status": "success", "message": "Connected OK in ...ms. Microsoft SQL Server ..."}`

> **เช็ค driver ที่มีในเครื่อง** ด้วย Python:
> ```python
> import pyodbc; print(pyodbc.drivers())
> ```
> ถ้าไม่เห็น "ODBC Driver 17/18 for SQL Server" ในลิสต์ ต้องติดตั้งก่อนตามขั้นตอนด้านบน

---

## Step 2 — Cloudflare Tunnel (เปิด local backend ออกสู่อินเทอร์เน็ต)

ติดตั้ง `cloudflared` ([docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/)):

```bash
# วิธีเร็วที่สุดสำหรับทดสอบ (Quick Tunnel, ไม่ต้อง login/domain เพิ่ม)
cloudflared tunnel --url http://localhost:8000
```

จะได้ URL แบบ `https://random-words.trycloudflare.com` — **เอา URL นี้ไปใส่ใน Worker** (Step 3)

> Quick Tunnel เหมาะกับทดสอบเฉยๆ — URL จะเปลี่ยนทุกครั้งที่รันใหม่ ถ้าต้องการ URL คงที่ ต้องใช้ **Named Tunnel** ซึ่งต้องผูกกับโดเมนจริงใน Cloudflare account (มีค่าโดเมน) — สำหรับทดสอบยังไม่จำเป็น ใช้ Quick Tunnel ไปก่อนได้

---

## Step 3 — Cloudflare Worker (deploy proxy → ได้ `*.workers.dev` ฟรี)

```bash
cd worker
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

> ทุกครั้งที่ Quick Tunnel ได้ URL ใหม่ (เช่น restart เครื่อง) ต้องแก้ `TUNNEL_URL` ใน `wrangler.toml` แล้ว `wrangler deploy` ใหม่

---

## Step 4 — Frontend ด้วย Cloudflare Pages (ได้ `*.pages.dev` ฟรี)

ไม่ต้องใช้ GitHub เลยก็ได้ — เลือกวิธีใดวิธีหนึ่ง:

### วิธีที่ 1: Deploy ตรงจากเครื่อง local ด้วย Wrangler (เร็วสุด)

```bash
cd frontend
wrangler pages deploy . --project-name=scada-deploy-test
```

Wrangler จะถามตั้งชื่อ project ครั้งแรก จากนั้นอัปโหลด `index.html` ขึ้น Cloudflare Pages ทันที จะได้ URL แบบ:

```
https://scada-deploy-test.pages.dev
```

อัปเดตเว็บใหม่ทุกครั้งที่แก้ไฟล์ ก็แค่รันคำสั่งเดิมซ้ำ:
```bash
wrangler pages deploy . --project-name=scada-deploy-test
```

### วิธีที่ 2: ลาก-วางผ่าน Dashboard (ไม่ใช้ command line)

1. เข้า Cloudflare Dashboard → **Workers & Pages** → **Create** → เลือกแท็บ **Pages**
2. เลือก **Upload assets** (ไม่ใช่ "Connect to Git")
3. ลากไฟล์ `frontend/index.html` ลงไป → ตั้งชื่อ project → **Deploy**
4. จะได้ URL แบบ `https://scada-deploy-test.pages.dev` ทันที

### ใช้งานหน้าเว็บ

เปิด URL ที่ได้ → ใส่ Worker URL จาก Step 3 ในช่อง input → กด **Run test**

---

## เช็คทีละจุดถ้ามีปัญหา

| ปัญหา | เช็คที่ |
|---|---|
| `/health` fail ที่ frontend แต่ curl ตรงๆได้ | CORS — เช็ค response headers จาก Worker |
| Worker คืน 502 "could not reach tunnel" | Tunnel ตายหรือ URL ใน `wrangler.toml` ไม่ตรง — เช็ค `cloudflared` ยังรันอยู่ไหม |
| `/db-check` fail แต่ `/health` ผ่าน | ปัญหาที่ DB เอง — credentials, firewall, PostgreSQL ไม่ accept connection จาก localhost (เช็ค `pg_hba.conf` และ `listen_addresses` ใน `postgresql.conf`) / สำหรับ MSSQL เช็ค "TCP/IP" enabled ใน SQL Server Configuration Manager และ SQL Server Browser service ทำงานอยู่ (ถ้าใช้ named instance) |
| MSSQL: `pyodbc.Error: ('01000', "...Can't open lib...")` | ไม่มี ODBC Driver ติดตั้ง — ดูขั้นตอนติดตั้งใน Step 1b |
| MSSQL: Login failed for user | เช็คว่า SQL Server เปิด "SQL Server and Windows Authentication mode" (ไม่ใช่ Windows-only) และ user/password ถูกต้อง |
| Worker/Pages deploy ไม่ผ่าน | เช็ค `wrangler login` แล้วหรือยัง, account มี Workers/Pages enabled ไหม |
| Pages deploy สำเร็จแต่หน้าเว็บ fetch ไม่ได้ | เช็ค URL ที่ใส่ในช่อง input ตรงกับ Worker URL จริงไหม (ต้องมี `https://` ครบ) |

---

## ไฟล์ในโปรเจกต์นี้

```
scada-test/
├── backend/
│   ├── main.py                    # FastAPI app (PostgreSQL): /health, /db-check
│   ├── main_mssql.py              # FastAPI app (MSSQL): /health, /db-check
│   ├── requirements.txt           # deps for PostgreSQL version
│   ├── requirements_mssql.txt     # deps for MSSQL version
│   ├── .env.example               # PostgreSQL credential template
│   └── .env.mssql.example         # MSSQL credential template
├── worker/
│   ├── worker.js           # Cloudflare Worker proxy
│   └── wrangler.toml
└── frontend/
    └── index.html          # หน้าทดสอบ (deploy ที่ Cloudflare Pages)
```

---

## สรุป URL ทั้งหมดที่จะได้ (ฟรีทั้งหมด ไม่ใช้โดเมนของตัวเอง)

```
Frontend : https://scada-deploy-test.pages.dev              (Cloudflare Pages)
Worker   : https://scada-deploy-test.yourname.workers.dev   (Cloudflare Workers)
Tunnel   : https://random-words.trycloudflare.com           (Quick Tunnel, เปลี่ยนทุกครั้งที่รัน)
```
