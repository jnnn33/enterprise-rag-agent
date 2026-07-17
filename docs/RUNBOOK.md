# Enterprise RAG Agent Runbook

## 1. 默认离线运行

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

访问 `http://127.0.0.1:3000`。默认使用 SQLite、Qdrant Local、Hash Embedding、Heuristic Reranker 和 Extractive Answer。

## 2. 真实模型与重排

当前进程直接读取环境变量。PowerShell 示例：

```powershell
$env:EMBEDDING_PROVIDER = "openai_compatible"
$env:EMBEDDING_BASE_URL = "https://provider.example/v1"
$env:EMBEDDING_API_KEY = "..."
$env:EMBEDDING_MODEL = "embedding-model"
$env:EMBEDDING_DIMENSION = "1024"

$env:LLM_PROVIDER = "openai_compatible"
$env:LLM_BASE_URL = "https://provider.example/v1"
$env:LLM_API_KEY = "..."
$env:LLM_MODEL = "chat-model"
$env:QUERY_REWRITE_ENABLED = "true"

$env:RERANKER_PROVIDER = "openai_compatible"
$env:RERANKER_BASE_URL = "https://provider.example/v1"
$env:RERANKER_API_KEY = "..."
$env:RERANKER_MODEL = "reranker-model"
```

重启后端后，通过 `/api/v1/providers` 检查生效状态。更换 Embedding 维度时，应使用新的向量集合或删除本地开发索引后重新入库。

## 3. Milvus

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,milvus]"
$env:VECTOR_STORE_PROVIDER = "milvus"
$env:MILVUS_URI = "data/milvus.db"
$env:MILVUS_COLLECTION = "knowledge_chunks"
```

`MILVUS_URI` 可以是 Milvus Lite 数据库文件，也可以是远程 URI；远程认证使用 `MILVUS_TOKEN`。项目会创建 VARCHAR 主键、FLOAT_VECTOR 字段和 COSINE 索引。

## 4. MCP 本地演示

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,mcp]"
$python = (Resolve-Path ".\.venv\Scripts\python.exe").Path.Replace("\", "\\")
$env:MCP_SERVERS_JSON = '[{"name":"demo","transport":"stdio","command":"' + $python + '","args":["backend/app/mcp/demo_server.py"]}]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

启动后查看：

- `/api/v1/mcp/servers`
- `/api/v1/mcp/tools`
- Workspace 中的 `mcp_tool` Skill

MCP Tool 风险固定为 `external`，必须经过 Preview 和 Confirm。

## 5. 审批策略

默认所有 Agent Action 都需要确认。只读工具可选自动批准：

```powershell
$env:AUTO_APPROVE_READ_ACTIONS = "true"
```

`write` 和 `external` 不会被该配置跳过。

## 6. 飞书

默认 `FEISHU_DRY_RUN=true`，只记录模拟结果。启用真实 Webhook：

```powershell
$env:FEISHU_DRY_RUN = "false"
$env:FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/..."
```

## 7. Docker

```powershell
docker compose up --build
```

Docker 是打包和统一运行环境，不是代码功能本身。默认 Compose 使用 Qdrant Local 文件模式，不要求单独部署 Qdrant 或 Milvus 服务。

## 8. 验证

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend/app backend/tests
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
```