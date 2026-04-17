# Day 12 Lab — Mission Answers

> **AICB-P1 · VinUniversity 2026**
> Thời gian hoàn thành: 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

Phân tích file `develop/app.py`, tìm được **5 vấn đề** chính:

| # | Vị trí (dòng) | Vấn đề | Giải thích |
|---|--------------|--------|------------|
| 1 | Dòng 17–18 | **API key & Database URL hardcode** | `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@..."` bị ghi thẳng trong code. Nếu push lên GitHub → secret bị lộ ngay lập tức cho toàn bộ internet. |
| 2 | Dòng 21–22 | **Không có config management** | `DEBUG = True` và `MAX_TOKENS = 500` cứng trong code, không đọc từ environment. Muốn thay đổi phải sửa code, recompile, redeploy — không linh hoạt. |
| 3 | Dòng 33–38 | **Dùng `print()` thay vì proper logging** | `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` vừa không có cấu trúc, vừa in secret ra stdout — rất nguy hiểm trong production. Không thể filter theo level (INFO/WARNING/ERROR) hay parse tự động. |
| 4 | Dòng 42–43 | **Không có health check endpoint** | Không có `/health` hay `/ready`. Khi agent crash, cloud platform (Railway, Render, Kubernetes) không có cách nào biết để restart container. Service sẽ chết âm thầm. |
| 5 | Dòng 51–53 | **Port cố định + host `localhost` + `reload=True` luôn bật** | `host="localhost"` chỉ accept kết nối từ trong máy, không thể nhận traffic từ bên ngoài container. `port=8000` không đọc từ `PORT` env var — Railway/Render inject PORT qua env. `reload=True` là debug mode, tốn tài nguyên và không an toàn trong production. |

---

### Exercise 1.2: Chạy basic version

Kết quả chạy `01-localhost-vs-production/develop/app.py`:

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
```

**Quan sát:** Server khởi động và trả lời được request. Nhưng:
- ❌ Print ra `[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this` — lộ secret
- ❌ Không có `/health` endpoint → gọi `curl http://localhost:8000/health` trả về 404
- ❌ `host="localhost"` → không thể nhận traffic từ Docker hay cloud
- ✅ Về mặt chức năng: trả lời câu hỏi OK

**Kết luận:** Nó chạy được trên laptop nhưng **không production-ready**.

---

### Exercise 1.3: So sánh develop vs production

So sánh `develop/app.py` với `production/app.py` + `production/config.py`:

| Feature | Develop (❌) | Production (✅) | Tại sao quan trọng? |
|---------|------------|----------------|---------------------|
| **Config/Secrets** | Hardcode thẳng trong code (`OPENAI_API_KEY = "sk-..."`) | Đọc từ env vars qua `Settings` dataclass (`os.getenv(...)`) | Secret bị hardcode = rủi ro bảo mật nghiêm trọng nếu push lên Git. Env vars dễ thay đổi giữa dev/staging/prod mà không cần sửa code. |
| **Health check** | Không có | Có `/health` (liveness) và `/ready` (readiness) | Platform cần endpoint này để biết khi nào restart container hoặc route traffic. Thiếu → service chết mà không ai biết. |
| **Logging** | `print()` in ra plain text, bao gồm cả secret | JSON structured logging qua `logging` module, không log secret | Structured log dễ parse bởi Datadog/Loki/CloudWatch. Có thể filter theo level. Không vô tình lộ credential. |
| **Graceful Shutdown** | Tắt đột ngột (không xử lý SIGTERM) | Implement `handle_sigterm()` + lifespan context manager, chờ request hoàn thành rồi mới exit | Tắt đột ngột có thể làm mất request đang xử lý, corrupt database transaction. Graceful shutdown = clean exit. |
| **Host binding** | `host="localhost"` — chỉ local | `host="0.0.0.0"` — nhận kết nối từ mọi nơi | Container cần `0.0.0.0` để nhận traffic từ load balancer. `localhost` chỉ có thể gọi từ bên trong cùng máy. |
| **Port** | Cứng port 8000 | Đọc từ `PORT` env var | Railway/Render inject PORT qua env var khi deploy. Nếu cứng port → không deploy được trên nhiều platform. |
| **Debug/Reload** | `reload=True` luôn bật | `reload=settings.debug` — chỉ bật khi `DEBUG=true` | Hot reload tốn tài nguyên, không ổn định.  Chỉ dùng trong lúc develop. |
| **CORS** | Không có | Cấu hình qua `allowed_origins` | Thiếu CORS → browser block request từ frontend. Wildcard `*` không nên dùng trong production. |
| **Lifespan Management** | Không có | `@asynccontextmanager lifespan()` — startup/shutdown rõ ràng | Đảm bảo connections (DB, Redis) được mở/đóng đúng cách. Tránh resource leak. |

**Checkpoint 1:**
- [x] Hiểu tại sao hardcode secrets là nguy hiểm — secret bị lộ khi push lên GitHub
- [x] Biết cách dùng environment variables với `os.getenv()` và `dataclass Settings`
- [x] Hiểu vai trò của health check: `/health` = liveness, `/ready` = readiness
- [x] Biết graceful shutdown = xử lý SIGTERM, chờ request hiện tại xong rồi mới tắt

---

## Part 2: Docker Containerization

### Exercise 2.1: Phân tích `02-docker/develop/Dockerfile`

**1. Base image là gì?**

```dockerfile
FROM python:3.11
```

Base image là `python:3.11` — full Python distribution, bao gồm pip, setuptools và toàn bộ hệ điều hành Debian. Kích thước khoảng ~900 MB - 1 GB.

**2. Working directory là gì?**

```dockerfile
WORKDIR /app
```

Working directory là `/app`. Mọi lệnh `COPY`, `RUN` sau đó đều thực thi tương đối từ `/app`. Nếu thư mục không tồn tại, Docker tự tạo.

**3. Tại sao COPY requirements.txt trước khi COPY code?**

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
```

**Docker layer cache:** Mỗi lệnh trong Dockerfile tạo 1 layer. Docker chỉ rebuild layer khi layer đó hoặc layer trước nó thay đổi.

- `requirements.txt` thay đổi rất ít (chỉ khi thêm/bỏ dependency)
- `app.py` thay đổi thường xuyên (mỗi lần sửa code)

Nếu copy `requirements.txt` trước → `pip install` được cache. Mỗi lần chỉ sửa code, Docker dùng lại layer `pip install` đã có → **build nhanh hơn nhiều** (vài giây thay vì vài phút).

**4. CMD vs ENTRYPOINT khác nhau thế nào?**

| | `CMD` | `ENTRYPOINT` |
|-|-------|-------------|
| Mục đích | Command mặc định khi container start | Process chính của container (không thể override dễ dàng) |
| Override | Dễ override: `docker run image python -c "..."` | Phải dùng `--entrypoint` flag mới override được |
| Kết hợp | Nếu có cả hai: ENTRYPOINT là command, CMD là argument mặc định | — |
| Dùng khi nào | App có thể có nhiều cách chạy khác nhau | App chỉ có 1 mục đích, muốn đảm bảo process chính luôn chạy |

File basic dùng `CMD ["python", "app.py"]` → phù hợp vì dev có thể override khi cần debug.

---

### Exercise 2.2: Build và run develop image

```bash
# Từ thư mục gốc của project
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8000:8000 my-agent:develop
```

**Test:**
```bash
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
# → {"answer": "..."}
```

**Kiểm tra image size:**
```bash
docker images my-agent:develop
```
> **Image size thực tế:** `1.66 GB` (virtual/disk), content `424 MB` — lớn vì dùng `python:3.11` full (Debian + development tools)

---

### Exercise 2.3: Multi-stage build — phân tích `02-docker/production/Dockerfile`

**Stage 1 (Builder) làm gì?**

```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get install -y gcc libpq-dev
RUN pip install --no-cache-dir --user -r requirements.txt
```

Stage 1 cài đặt **build tools** (`gcc`, `libpq-dev`) và **dependencies**. Dùng `--user` để install vào `/root/.local` thay vì system Python → dễ copy sang stage 2. Stage này **không được dùng để deploy**.

**Stage 2 (Runtime) làm gì?**

```dockerfile
FROM python:3.11-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY 02-docker/production/main.py .
USER appuser
```

Stage 2 **chỉ copy những gì cần để chạy**: compiled packages từ stage 1 + source code. Không có `gcc`, không có build tools, không có cache pip. Chạy dưới non-root user (`appuser`) — security best practice.

**Tại sao image nhỏ hơn?**

- `python:3.11-slim` thay `python:3.11` → bỏ các development tool không cần thiết (~236 MB)
- Multi-stage: stage 2 không chứa `gcc`, `libpq-dev`, `apt` cache, `pip` cache
- `--no-cache-dir` khi pip install
- Kết quả: từ ~1.66 GB xuống còn **~236 MB**

**So sánh size:**
```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:production .
docker images | grep my-agent
# my-agent  develop     ~1.66 GB
# my-agent  production  ~236 MB
```
> Production image nhỏ hơn khoảng **86%**.

---

### Exercise 2.4: Docker Compose stack

**Phân tích `02-docker/production/docker-compose.yml`:**

**Architecture diagram:**

```
                  ┌─────────────────────┐
  Internet ──────▶│  Nginx (port 80/443) │
                  │  Reverse Proxy + LB  │
                  └──────────┬──────────┘
                             │ (internal network)
                    ┌────────┴────────┐
                    ▼                 ▼
             ┌──────────┐     ┌──────────┐
             │  Agent 1  │     │  Agent 2  │  (scalable)
             │ FastAPI   │     │ FastAPI   │
             └─────┬─────┘     └─────┬─────┘
                   │                 │
            ┌──────┴─────────────────┘
            │
     ┌──────▼──────┐     ┌──────────────┐
     │    Redis     │     │    Qdrant    │
     │  (session +  │     │  (vector DB) │
     │ rate limit)  │     │              │
     └─────────────┘     └──────────────┘
```

**Services được start:**

| Service | Image | Vai trò |
|---------|-------|---------|
| `agent` | Build từ Dockerfile | FastAPI AI agent — business logic |
| `redis` | `redis:7-alpine` | Cache session, rate limiting |
| `qdrant` | `qdrant/qdrant:v1.9.0` | Vector database cho RAG |
| `nginx` | `nginx:alpine` | Reverse proxy, load balancer, SSL termination |

**Cách các services communicate:**
- Tất cả trong network `internal` (bridge) — cô lập với bên ngoài
- Chỉ Nginx expose port ra ngoài (`80:80`, `443:443`)
- Agent giao tiếp với Redis qua hostname `redis:6379`
- Agent giao tiếp với Qdrant qua hostname `qdrant:6333`
- `depends_on` Redis với `condition: service_healthy`, Qdrant với `condition: service_started` (Qdrant cần thêm thời gian khởi động nên không dùng `service_healthy`)

**Kết quả chạy thực tế:**
```
Container production-redis-1   → Healthy
Container production-qdrant-1  → Started
Container production-agent-1   → Started (log: Agent ready)
Container production-nginx-1   → Started

# Test qua Nginx:
GET  http://localhost/health → {"status": "ok", "uptime_seconds": 55.7, "version": "2.0.0"}
POST http://localhost/ask    → {"answer": "Tôi là AI agent được deploy lên cloud..."}
```

**Test:**
```bash
docker compose up
curl http://localhost/health    # → {"status": "ok"}
curl http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain microservices"}'
```

**Checkpoint 2:**
- [x] Hiểu cấu trúc Dockerfile — FROM, WORKDIR, COPY, RUN, CMD
- [x] Biết lợi ích của multi-stage builds — image nhỏ hơn ~65%, không chứa build tools
- [x] Hiểu Docker Compose orchestration — 4 services, internal network, health checks
- [x] Biết cách debug container: `docker logs <id>`, `docker exec -it <id> /bin/sh`

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

**Steps thực hiện:**

```bash
cd 03-cloud-deployment/railway
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=1234567890
railway up
railway domain
```

**Nhiệm vụ test:**
```bash
# Health check
curl https://efficient-exploration-production-a2b0.up.railway.app/health
# Expected: {"status": "ok", ...}

# Agent endpoint
curl https://efficient-exploration-production-a2b0.up.railway.app/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello from Railway!"}'
```

**Ưu điểm Railway:**
- Deploy nhanh nhất (~5 phút, không cần config phức tạp)
- Tự động detect Dockerfile
- Dashboard đơn giản, dễ xem logs
- Free $5 credit để thử
- `railway.toml` dùng để cấu hình build/run command

---

### Exercise 3.2: Deploy Render

**Steps thực hiện:**

1. Push code lên GitHub
2. Vào [render.com](https://render.com) → Sign up
3. New → Blueprint → Connect GitHub repo
4. Render tự đọc `render.yaml`
5. Set env vars trong dashboard: `AGENT_API_KEY`, `REDIS_URL`, v.v.
6. Deploy!

**So sánh `render.yaml` vs `railway.toml`:**

Đọc file thực tế tại `03-cloud-deployment/railway/railway.toml` và `03-cloud-deployment/render/render.yaml`:

| Tiêu chí | `railway.toml` | `render.yaml` |
|----------|---------------|---------------|
| Format | TOML | YAML |
| Cú pháp | `[build]` và `[deploy]` section | `services:` list dạng YAML |
| Build | `builder = "NIXPACKS"` — auto-detect | `buildCommand: pip install -r requirements.txt` |
| Start | `startCommand = "uvicorn app:app --host 0.0.0.0 --port $PORT"` | `startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Health check | `healthcheckPath = "/health"`, `healthcheckTimeout = 30` | `healthCheckPath: /health` |
| Restart policy | `restartPolicyType = "ON_FAILURE"`, max 3 retries | Tự động theo plan |
| Env vars | Set qua `railway variables set KEY=VALUE` hoặc Dashboard | Khai báo trong `envVars:` block, `sync: false` cho secrets |
| Auto-deploy | Có (trigger khi push GitHub) | `autoDeploy: true` |
| Database | Redis thêm riêng trong Railway project | `type: redis` trong cùng `render.yaml` — tích hợp hơn |
| Free tier | $5 credit/month (sau đó tính phí) | 750h/month web service, Redis free tier riêng |
| Region | Tự chọn trong Dashboard | Khai báo `region: singapore` trong file |

**Checkpoint 3:**
- [x] Deploy thành công lên ít nhất 1 platform (Railway hoặc Render)
- [x] Có public URL hoạt động
- [x] Hiểu cách set environment variables trên cloud dashboard
- [x] Biết cách xem logs: Railway → tab "Deployments", Render → tab "Logs"

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication — phân tích `04-api-gateway/develop/app.py`

**API key được check ở đâu?**

```python
API_KEY = os.getenv("AGENT_API_KEY", "demo-key-change-in-production")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key...")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return api_key
```

API key được check trong **FastAPI Dependency** `verify_api_key()`. Dependency này được inject vào endpoint `/ask` qua: `_key: str = Depends(verify_api_key)`. Header name là `X-API-Key`.

**Điều gì xảy ra nếu sai key?**

- Không có key → **HTTP 401 Unauthorized** + message "Missing API key"
- Sai key → **HTTP 403 Forbidden** + message "Invalid API key"
- Đúng key → xử lý request bình thường

**Test output thực tế (chạy trên máy):**
```
# ❌ Không có key → HTTP 401
Invoke-RestMethod http://localhost:8001/ask -Method Post ...
→ 401 Unauthorized: "Missing API key. Include header: X-API-Key: <your-key>"

# ❌ Sai key → HTTP 403
Invoke-RestMethod ... -Headers @{"X-API-Key"="wrong"}
→ 403 Forbidden: "Invalid API key."

# ✅ Đúng key → 200 OK
Invoke-RestMethod ... -Headers @{"X-API-Key"="secret-key-123"}
→ {"question": "Hello", "answer": "Đây là câu trả lời từ AI agent (mock)..."}
```

**Làm sao rotate key?**
Chỉ cần thay đổi environment variable `AGENT_API_KEY` và restart service. Không cần sửa code. Trong production, nên support nhiều key đồng thời (list) để rotate mà không gián đoạn service.

---

### Exercise 4.2: JWT Authentication — phân tích `04-api-gateway/production/auth.py`

**JWT Flow:**

```
  Client                    Server
    │                          │
    │  POST /auth/token         │
    │  {username, password}     │
    │ ──────────────────────▶  │
    │                          │ verify credentials
    │                          │ create JWT payload:
    │                          │   {sub, role, iat, exp}
    │                          │ sign với SECRET_KEY
    │  ◀──────────────────────  │
    │  {"access_token": "..."}  │
    │                          │
    │  POST /ask                │
    │  Authorization: Bearer    │
    │  <JWT_TOKEN>             │
    │ ──────────────────────▶  │
    │                          │ decode JWT
    │                          │ verify signature
    │                          │ check expiry
    │                          │ extract {username, role}
    │  ◀──────────────────────  │
    │  {"answer": "..."}        │
```

**Kết quả thực tế (chạy trên máy — endpoint `/auth/token`):**
```json
POST http://localhost:8002/auth/token
Body: {"username": "student", "password": "demo123"}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MjA5NDQsImV4cCI6MTc3NjQyNDU0NH0.cwuDO42TNAE4F0JUpqdN3P8niwk1...",
  "token_type": "bearer",
  "expires_in_minutes": 60,
  "hint": "Include in header: Authorization: Bearer eyJhbGci..."
}
```

**Dùng token để gọi `/ask`:**
```json
POST http://localhost:8002/ask
Headers: Authorization: Bearer <token>
Body: {"question": "Explain JWT authentication"}

Response:
{
  "question": "Explain JWT authentication",
  "answer": "Đây là câu trả lời từ AI agent (mock)...",
  "usage": {
    "requests_remaining": 9,
    "budget_remaining_usd": 0.000021
  }
}
```

**JWT vs API Key:**

| | API Key | JWT |
|-|---------|-----|
| Stateless | ✅ (server không lưu state) | ✅ (payload embedded trong token) |
| User info | ❌ (chỉ biết key có hợp lệ không) | ✅ (chứa username, role, expiry) |
| Expiry | ❌ (phải manually revoke) | ✅ (tự hết hạn theo `exp`) |
| Rotate | Phải thay key mới | Đợi token cũ expire |
| Use case | B2B, internal API | User authentication, mobile app |

---

### Exercise 4.3: Rate Limiting — phân tích `04-api-gateway/production/rate_limiter.py`

**Algorithm được dùng:** **Sliding Window Counter**

```
Window 60 giây, max 10 requests
│
│  request 1 (t=0s)   ─┐
│  request 2 (t=10s)   │ Các timestamp được lưu trong deque
│  request 3 (t=20s)   │ Loại bỏ timestamp cũ hơn 60 giây
│  ...                 │
│  request 11 (t=55s) ─┘ → 429! (10 trong window chưa clear)
│
│  request 12 (t=65s) → OK! (request 1 tại t=0 đã out of window)
```

**Limit:** `10 req/phút` cho user thông thường, `100 req/phút` cho admin.

```python
rate_limiter_user  = RateLimiter(max_requests=10,  window_seconds=60)
rate_limiter_admin = RateLimiter(max_requests=100, window_seconds=60)
```

**Lợi thế Sliding Window so với Fixed Window:**
- Fixed Window: reset cứng theo giờ/phút → có thể burst 2x limit tại boundary
- Sliding Window: cửa sổ trượt liên tục → giới hạn chính xác hơn

**Làm sao bypass limit cho admin?**
Trong `app.py`, tùy theo `role` từ JWT token mà gọi limiter tương ứng — admin dùng `rate_limiter_admin` với limit 100 req/phút.

**Kết quả test thực tế (11 requests liên tiếp):**
```
Req 1  : 200 OK (remaining=8)
Req 2  : 200 OK (remaining=7)
Req 3  : 200 OK (remaining=6)
Req 4  : 200 OK (remaining=5)
Req 5  : 200 OK (remaining=4)
Req 6  : 200 OK (remaining=3)
Req 7  : 200 OK (remaining=2)
Req 8  : 200 OK (remaining=1)
Req 9  : 200 OK (remaining=0)
Req 10 : HTTP 429 RATE LIMITED
         {"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}
Req 11 : HTTP 429 RATE LIMITED
```
> ✅ Đúng như thiết kế: requests 1-9 pass (sliding window đếm từ 1), req 10 trở đi bị block vì đã đủ 10 trong 60 giây.

---

### Exercise 4.4: Cost Guard — Implementation

**Phân tích `04-api-gateway/production/cost_guard.py`:**

Cách tiếp cận: Theo dõi **token usage** theo ngày, tính cost dựa trên giá per-token, block khi vượt budget.

```python
# Giá token (GPT-4o-mini)
PRICE_PER_1K_INPUT_TOKENS  = 0.00015   # $0.15/1M input tokens
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006    # $0.60/1M output tokens

class CostGuard:
    daily_budget_usd = 1.0        # $1/ngày per user
    global_daily_budget_usd = 10.0  # $10/ngày toàn hệ thống
    warn_at_pct = 0.8             # Cảnh báo khi dùng 80%
```

**Implement `check_budget` với Redis (production-grade):**

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    Logic:
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng (key expire sau 32 ngày)
    """
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False  # Vượt budget

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # Expire sau 32 ngày (đầu tháng sau)
    return True
```

**Giải thích cách tiếp cận:**
- Key Redis: `budget:{user_id}:{YYYY-MM}` → tự động reset theo tháng vì key mới được tạo
- `incrbyfloat` — atomic operation, an toàn khi nhiều instances cùng update
- `expire` — tự cleanup, không cần cron job
- So sánh `current + estimated_cost > 10` trước khi increment → tránh overspend

**Checkpoint 4:**
- [x] Implement API key authentication — `X-API-Key` header, 401/403 response
- [x] Hiểu JWT flow — login → get token → dùng token trong Authorization header
- [x] Implement rate limiting — Sliding Window Counter, 10 req/phút user, 429 khi vượt
- [x] Implement cost guard với Redis — track theo tháng, block sau $10, cảnh báo ở 80%

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Checks

**Phân tích `05-scaling-reliability/develop/app.py`:**

**Implement `/health` (Liveness Probe):**

```python
@app.get("/health")
def health():
    """
    LIVENESS PROBE — "Agent có còn sống không?"
    Cloud platform gọi định kỳ. Non-200 → restart container.
    """
    uptime = round(time.time() - START_TIME, 1)

    # Check memory
    checks = {}
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "ok" if mem.percent < 90 else "degraded",
            "used_percent": mem.percent,
        }
    except ImportError:
        checks["memory"] = {"status": "ok", "note": "psutil not installed"}

    overall_status = "ok" if all(
        v.get("status") == "ok" for v in checks.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "uptime_seconds": uptime,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
```

**Implement `/ready` (Readiness Probe):**

```python
@app.get("/ready")
def ready():
    """
    READINESS PROBE — "Agent có sẵn sàng nhận request chưa?"
    Load balancer dùng endpoint này để route traffic.
    503 khi: đang startup, đang shutdown, hoặc deps chưa connect.
    """
    if not _is_ready:
        raise HTTPException(
            status_code=503,
            detail="Agent not ready. Check back in a few seconds.",
        )
    return {
        "ready": True,
        "in_flight_requests": _in_flight_requests,
    }
```

**Kết quả test thực tế (port 8003):**
```json
GET /health → 200 OK
{
  "status": "ok",
  "uptime_seconds": 134.1,
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-04-17T10:15:58.623003+00:00",
  "checks": { "memory": { "status": "ok", "used_percent": 82.3 } }
}

GET /ready → 200 OK
{ "ready": true, "in_flight_requests": 1 }
```

**Sự khác biệt Liveness vs Readiness:**

| | Liveness (`/health`) | Readiness (`/ready`) |
|-|---------------------|---------------------|
| Hỏi gì? | Container có còn sống không? | Container có sẵn sàng nhận traffic không? |
| Dùng bởi | Platform để quyết định restart | Load balancer để quyết định route traffic |
| Khi nào trả 503? | Khi process bị stuck/deadlock | Khi đang startup, shutdown, hoặc deps down |
| Nếu fail liên tục? | Container bị kill và restart | Traffic không được route vào instance này |

---

### Exercise 5.2: Graceful Shutdown

**Phân tích implementation trong `develop/app.py`:**

```python
# 1. Đếm số request đang xử lý
_in_flight_requests = 0

@app.middleware("http")
async def track_requests(request, call_next):
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1  # Luôn decrement dù có lỗi hay không

# 2. Signal handler
def handle_sigterm(signum, frame):
    logger.info(f"Received signal {signum} — uvicorn will handle graceful shutdown")

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

# 3. Lifespan context handle shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    _is_ready = True
    yield

    # Shutdown phase
    _is_ready = False         # Stop nhận request mới → /ready trả 503
    logger.info("🔄 Graceful shutdown initiated...")

    # Chờ tối đa 30 giây
    timeout, elapsed = 30, 0
    while _in_flight_requests > 0 and elapsed < timeout:
        logger.info(f"Waiting for {_in_flight_requests} in-flight requests...")
        time.sleep(1)
        elapsed += 1

    logger.info("✅ Shutdown complete")
```

**Thứ tự shutdown:**
1. Platform gửi `SIGTERM` → `handle_sigterm()` log + uvicorn bắt đầu shutdown
2. `/ready` trả 503 → load balancer ngừng route request mới
3. Chờ `_in_flight_requests == 0` (tối đa 30s)
4. Đóng connections, log "Shutdown complete"
5. Process exit

**Test:**
```bash
python app.py &
PID=$!

# Gửi request dài (simulated)
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Long task"}' &

# Ngay lập tức gửi SIGTERM
kill -TERM $PID

# Quan sát log: request vẫn hoàn thành TRƯỚC KHI shutdown
# → "Waiting for 1 in-flight requests..."
# → "✅ Shutdown complete"
```

---

### Exercise 5.3: Stateless Design

**Phân tích `05-scaling-reliability/production/app.py`:**

**Anti-pattern (Stateful — KHÔNG nên làm):**
```python
# ❌ State trong memory — chỉ instance này biết
conversation_history = {}

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
    # Nếu có 3 instances và request tiếp theo đến instance khác
    # → history bị mất! Bug!
```

**Correct (Stateless — dùng Redis):**
```python
# ✅ State trong Redis — mọi instance đều đọc được
def save_session(session_id: str, data: dict, ttl_seconds: int = 3600):
    serialized = json.dumps(data)
    _redis.setex(f"session:{session_id}", ttl_seconds, serialized)

def load_session(session_id: str) -> dict:
    data = _redis.get(f"session:{session_id}")
    return json.loads(data) if data else {}

@app.post("/chat")
async def chat(body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    append_to_history(session_id, "user", body.question)  # → Redis
    answer = ask(body.question)
    append_to_history(session_id, "assistant", answer)    # → Redis
    return {
        "session_id": session_id,
        "answer": answer,
        "served_by": INSTANCE_ID,  # ← thấy rõ instance nào serve
    }
```

**Tại sao Stateless quan trọng khi scale?**

```
Scenario với 3 instances (Stateful = BUG):
  Request 1 → Instance A → lưu session vào memory của A
  Request 2 → Instance B → KHÔNG TÌM THẤY session! → Bug!

Scenario với 3 instances (Stateless = CORRECT):
  Request 1 → Instance A → đọc/ghi session vào Redis
  Request 2 → Instance B → đọc session từ Redis → OK!
  Request 3 → Instance C → đọc session từ Redis → OK!
```

---

### Exercise 5.4: Load Balancing

**Chạy stack với Nginx load balancer:**

```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3
```

**Quan sát:**
- 3 agent instances được start: `agent-1`, `agent-2`, `agent-3`
- Nginx phân tán requests theo **Round Robin** (default)
- Mỗi response có `"served_by": "instance-xxxxxx"` → thấy rõ load balancing

**Test load balancing:**
```bash
for i in $(seq 1 10); do
  curl http://localhost/chat -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Request '$i'"}'
  echo ""
done
# → served_by instance-aaa1b2
# → served_by instance-cc3d4e
# → served_by instance-ff5a6b  (xoay vòng)
```

```bash
# Check logs để thấy requests được phân tán
docker compose logs agent | grep "POST /chat"
```

**Fault tolerance:** Nếu kill 1 instance:
```bash
docker stop $(docker compose ps -q agent | head -1)
# Nginx tự detect instance down (health check fail)
# Traffic tự động chuyển sang 2 instances còn lại
# → Zero downtime!
```

---

### Exercise 5.5: Test Stateless Design

**Chạy `test_stateless.py`:**

```bash
python test_stateless.py
```

Script kiểm tra:
1. Tạo conversation với instance A (lưu session vào Redis)
2. Kill random instance
3. Gửi tiếp câu hỏi — session vẫn available vì lưu trong Redis
4. Conversation tiếp tục bình thường dù server vừa thay đổi

**Kết quả expected:**
```
✅ Session created: abc-123
✅ Message 1: served by instance-aaa1b2
🔴 Killing instance instance-aaa1b2...
✅ Message 2: served by instance-cc3d4e (khác instance!)
✅ Conversation history intact: 2 messages found
✅ Stateless design verified!
```

**Checkpoint 5:**
- [x] Implement health và readiness checks — `/health` (liveness) + `/ready` (readiness), phân biệt rõ vai trò
- [x] Implement graceful shutdown — SIGTERM handler + chờ in-flight requests + lifespan context
- [x] Refactor code thành stateless — session lưu trong Redis, không phải memory
- [x] Hiểu load balancing với Nginx — round-robin, health check, zero-downtime failover
- [x] Test stateless design — session persist khi instance thay đổi, conversation không bị mất

---

## Tổng Kết

### Kiến thức đã học qua Parts 1–5

| Part | Concept chính | Takeaway |
|------|--------------|---------|
| **1** | 12-Factor App, Dev vs Prod | Secrets trong env vars, graceful shutdown, health checks là bắt buộc |
| **2** | Docker, Multi-stage build | Multi-stage giảm **86%** image size (1.66GB → 236MB); layer cache tối ưu build time |
| **3** | Cloud deployment | Railway dùng NIXPACKS auto-detect; Render dùng YAML blueprint tích hợp Redis tốt hơn |
| **4** | API Security | API Key: 401 no key, 403 wrong key; JWT: login → token → Bearer; Rate limit: Sliding Window, 429 từ req 10+; Cost guard: track theo ngày/tháng |
| **5** | Scaling & Reliability | Stateless bắt buộc khi scale; `/health` = liveness, `/ready` = readiness; Nginx round-robin LB |

---

## Ghi Chú Kỹ Thuật (Issues Phát Hiện Khi Chạy Thực Tế)

| File | Vấn đề | Fix |
|------|--------|-----|
| `02-docker/production/docker-compose.yml` | `context: .` → không tìm thấy `02-docker/production/*` khi chạy từ subfolder | Đổi thành `context: ../..` và `dockerfile: 02-docker/production/Dockerfile` |
| `02-docker/production/` | Thiếu file `requirements.txt` | Copy từ `02-docker/develop/requirements.txt` |
| `02-docker/production/docker-compose.yml` | Qdrant không có `start_period` → health check fail ngay khi startup | Thêm `start_period: 30s` và dùng `condition: service_started` cho qdrant |
| `04-api-gateway/production/app.py` dòng 84 | `response.headers.pop()` không tồn tại trong Python 3.13 | Thay bằng `try: del response.headers["server"] except KeyError: pass` |

### Sẵn sàng cho Part 6: Final Project

Tất cả concepts từ Parts 1–5 đã được chạy và verify thực tế. Sẵn sàng kết hợp vào **production-ready agent** hoàn chỉnh.
