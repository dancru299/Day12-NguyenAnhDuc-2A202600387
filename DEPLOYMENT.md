# Deployment Information

## Public URL
https://efficient-exploration-production-a2b0.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://efficient-exploration-production-a2b0.up.railway.app/health
```
# Mong đợi trả về:
{"status":"ok","uptime_seconds":999.8,"platform":"Railway","timestamp":"2026-04-17T14:47:26.179423+00:00"}

### API Test (with authentication)
```bash
curl -X POST https://efficient-exploration-production-a2b0.up.railway.app/ask \
  -H "X-API-Key: 1234567890" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```
# Mong đợi trả về:
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","platform":"Railway"}

## Environment Variables Set
- PORT = 8000
- REDIS_URL =
- AGENT_API_KEY = 1234567890
- LOG_LEVEL = info

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
