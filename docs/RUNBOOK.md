# Enterprise RAG Agent Runbook

## Local development

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd run dev
```

Open `http://127.0.0.1:3000`. API documentation is available at `http://127.0.0.1:8000/docs`.

## Docker

```powershell
docker compose up --build
```

SQLite data and the local Qdrant collection are stored under `data/`.

## External providers

The default configuration is fully offline and deterministic. Set the following values to enable compatible embedding and chat providers:

```text
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://provider.example/v1
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=...
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
QUERY_REWRITE_ENABLED=true
```

Feishu is safe by default. To enable live webhook delivery:

```text
FEISHU_DRY_RUN=false
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm.cmd run build
```
