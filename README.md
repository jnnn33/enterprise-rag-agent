# Enterprise RAG Agent

一个用于边开发边学习的企业级 RAG + Agent 原型。项目会从可解释的最小闭环逐步演进到真实向量检索、LLM、Agent Runtime、流式前端和部署。

## 当前阶段：第一项目功能开发完成 / 课程第 3 课

已经完成可持久化的最小 RAG 骨架：

1. 文档通过 JSON API 或 TXT/Markdown/PDF/DOCX 文件上传进入知识库。
2. 文档被切分为带来源信息的 Chunk。
3. 用户问题通过关键词检索与 Qdrant 向量检索召回 Chunk，并使用 RRF 融合排名。
4. 系统返回基于检索结果拼装的答案和 Citations。
5. 文档与 Chunk 持久化到 SQLite，服务重启后仍可检索。
6. PDF 页面文本、DOCX 段落与表格可以统一解析后入库。
7. 服务启动时会根据 SQLite 中已有 Chunk 恢复向量索引。
8. Embedding Provider 可在离线 Hash 与 OpenAI-compatible 语义模型之间切换。
9. Query Rewrite 可在原问题直通与 LLM 改写之间切换。
10. 二阶段 Heuristic Reranker 对候选 Chunk 重新排序。
11. Answer Generator 可在离线摘录答案与 OpenAI-compatible LLM 引用回答之间切换。
12. Agent Runtime 支持 preview、confirm、reject、execute 受控状态流转。
13. Knowledge QA Skill 可把用户目标规划成受审批的知识库问答 Action。
14. Tool Registry 只允许 Agent 调用已注册的 Knowledge Answer Tool。
15. Agent Run、Action 与审计 Event 持久化到 SQLite，服务重启后仍可读取。
16. 非法状态跳转、未知 Skill 和 Tool 执行异常均有明确的失败结果。
17. Conversation API 持久化多轮对话，并把 Citations 与 Trace 保存在消息元数据中。
18. HR Recruiting Skill 支持候选人摘要、面试反馈、跟进任务和飞书通知。
19. Agent Action 记录尝试次数，失败步骤可重试，已成功步骤不会重复执行。
20. SSE 持续输出 Agent 审计事件与最终状态。
21. RAG Evaluation API 计算关键词命中、引用覆盖和通过率。
22. Next.js + TypeScript 管理端提供 Ask、Knowledge、Workspace、Evaluations 页面。
23. Docker Compose 可同时启动 FastAPI、SQLite/Qdrant 本地数据和 Next.js 前端。

默认配置完全离线运行；配置 Embedding 与 LLM Provider 后，可以调用兼容接口完成真实语义检索、查询改写和引用回答。

学习笔记：[第三课：Embedding、Qdrant 与混合检索](docs/LESSON_03_VECTOR_RETRIEVAL.md)
学习笔记：[第五课：Query Rewrite、Rerank 与引用回答](docs/LESSON_05_LLM_PIPELINE.md)

课程路线：[30 课时企业 RAG + Agent 学习路线](docs/COURSE_ROADMAP.md)
阶段说明：[Stage 6：Agent Runtime 与审批执行](docs/STAGE_06_AGENT_RUNTIME.md)
运行手册：[本地开发、Docker 与外部 Provider 配置](docs/RUNBOOK.md)
## 目录结构

```text
backend/app/
  api/           HTTP 路由与依赖获取
  core/          配置和应用容器
  domain/        领域数据模型
  repositories/  数据存取接口、内存实现与 SQLite 实现
  schemas/       API 输入输出模型
  services/      切块、检索、问答业务逻辑
  main.py        FastAPI 应用入口
backend/tests/   自动化测试
frontend/app/    Next.js 页面与 CSS Modules
frontend/lib/    API 客户端与 TypeScript 类型
frontend/components/  应用外壳与共享组件
```

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --app-dir backend --reload
```

前端进入 frontend 目录后运行 npm.cmd install 和 npm.cmd run dev。

打开 `http://127.0.0.1:8000/docs` 可以使用 FastAPI 自动生成的接口页面。

## 示例

先写入一份制度文档：

```powershell
$body = @{
  title = "差旅报销制度"
  source = "finance-policy-v1"
  content = "员工出差应提前申请。高铁二等座可以报销，市内交通每天报销上限为 200 元。"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/documents `
  -ContentType "application/json" -Body $body
```

然后提问：

```powershell
$body = @{ question = "市内交通报销上限是多少？"; top_k = 3 } | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/chat `
  -ContentType "application/json" -Body $body
```

## 演进路线

- 阶段 1：FastAPI 与最小 RAG 闭环
- 阶段 2：SQLite 持久化与文件上传
- 阶段 3：TXT/Markdown/PDF/DOCX 多格式解析
- 阶段 4：Embedding、Qdrant 与 RRF 混合检索
- 阶段 5：LLM、Query Rewrite、Rerank 与 Answer + Citations
- 阶段 6：Agent Runtime、Skill、Tool 与审批执行
- 阶段 7：Next.js、SSE、评测、Docker 与部署（已完成）

