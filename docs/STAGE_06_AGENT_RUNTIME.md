# Stage 6：Agent Runtime 与审批执行

## 本阶段目标

在现有 RAG 服务之上增加一个受控 Agent 运行时。Agent 不会在收到目标后立即执行，而是先生成可检查的计划，等待用户确认，再调用注册过的 Tool。

```text
objective
  -> Skill 生成 Action 预览
  -> awaiting_confirmation
  -> confirm 或 reject
  -> confirmed
  -> execute
  -> Tool 执行
  -> completed 或 failed
```

## 当前组件

- `AgentRuntime`：管理任务状态流转和执行顺序。
- `SkillRegistry`：只允许使用已经注册的 Skill。
- `KnowledgeQASkill`：把知识库问答目标规划成一个 Tool Action。
- `ToolRegistry`：只允许调用已经注册的 Tool。
- `KnowledgeAnswerTool`：调用现有 `RagService`，返回 Answer、Citations 和 Trace。
- `SQLiteAgentRunRepository`：持久化 Run、Action 和 Event，服务重启后仍能读取。

## API

```text
POST /api/v1/agent/runs
GET  /api/v1/agent/runs
GET  /api/v1/agent/runs/{run_id}
POST /api/v1/agent/runs/{run_id}/confirm
POST /api/v1/agent/runs/{run_id}/reject
POST /api/v1/agent/runs/{run_id}/execute
```

创建预览：

```json
{
  "objective": "员工每月远程办公补贴是多少？",
  "skill_name": "knowledge_qa",
  "inputs": {
    "top_k": 3
  }
}
```

确认任务：

```json
{
  "note": "同意根据知识库生成回答"
}
```

## 状态约束

- 新任务只能处于 `awaiting_confirmation`。
- 只有等待确认的任务可以被确认或拒绝。
- 只有 `confirmed` 任务可以执行。
- `rejected`、`completed` 和 `failed` 任务不能再次执行。
- Tool 异常会写入 Action、Run 和 Event，不会伪装成成功结果。

## 当前边界

这一版先完成单 Skill、单或多 Action 顺序执行和持久化审计。后续阶段再增加 LLM Planner、重试策略、并行 Action、SSE 事件流和真实企业工具集成。
