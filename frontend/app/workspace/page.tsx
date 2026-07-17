"use client";

import {
  Check,
  CircleX,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { StatusPill } from "@/components/status-pill";
import { API_BASE, api } from "@/lib/api";
import {
  AgentRun,
  Capability,
  ProviderStatus,
  WorkItem,
} from "@/lib/types";

import styles from "./workspace.module.css";

type FeishuStatus = { provider: string; configured: boolean; mode: string };

export default function WorkspacePage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [skills, setSkills] = useState<Capability[]>([]);
  const [tools, setTools] = useState<Capability[]>([]);
  const [tasks, setTasks] = useState<WorkItem[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [feishu, setFeishu] = useState<FeishuStatus | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skillName, setSkillName] = useState("auto");
  const [objective, setObjective] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [role, setRole] = useState("");
  const [notes, setNotes] = useState("");
  const [owner, setOwner] = useState("Recruiting team");
  const [notify, setNotify] = useState(true);
  const [taskId, setTaskId] = useState("");
  const [taskStatus, setTaskStatus] = useState("completed");
  const [mcpTool, setMcpTool] = useState("");
  const [jsonInputs, setJsonInputs] = useState("{}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => runs.find((run) => run.id === selectedId) || runs[0] || null,
    [runs, selectedId],
  );
  const mcpTools = tools.filter((tool) => tool.name.startsWith("mcp."));
  const waitingCount = runs.filter(
    (run) => run.status === "awaiting_confirmation",
  ).length;
  const completedCount = runs.filter((run) => run.status === "completed").length;

  async function loadAll(preferredId?: string) {
    const [runItems, skillItems, toolItems, taskItems, providerItems, feishuStatus] =
      await Promise.all([
        api<AgentRun[]>("/agent/runs"),
        api<Capability[]>("/agent/skills"),
        api<Capability[]>("/agent/tools"),
        api<WorkItem[]>("/workspace/tasks"),
        api<ProviderStatus[]>("/providers"),
        api<FeishuStatus>("/workspace/integrations/feishu"),
      ]);
    setRuns(runItems);
    setSkills(skillItems);
    setTools(toolItems);
    setTasks(taskItems);
    setProviders(providerItems);
    setFeishu(feishuStatus);
    setTaskId((current) => current || taskItems[0]?.id || "");
    setMcpTool((current) => current || toolItems.find((tool) => tool.name.startsWith("mcp."))?.name || "");
    setSelectedId((current) => preferredId || current || runItems[0]?.id || null);
  }

  useEffect(() => {
    loadAll().catch((reason: Error) => setError(reason.message));
  }, []);

  function buildInputs(): Record<string, unknown> {
    if (skillName === "auto") return JSON.parse(jsonInputs);
    if (skillName === "knowledge_qa") return { top_k: 3 };
    if (skillName === "hr_recruiting") {
      return {
        workflow: "candidate_review",
        candidate_name: candidateName,
        role,
        interview_notes: notes,
        owner,
        notify,
      };
    }
    if (skillName === "workspace_management") {
      return { item_id: taskId, status: taskStatus };
    }
    if (skillName === "mcp_tool") {
      return { tool_name: mcpTool, arguments: JSON.parse(jsonInputs) };
    }
    return JSON.parse(jsonInputs);
  }

  async function handlePreview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        objective,
        inputs: buildInputs(),
      };
      if (skillName !== "auto") payload.skill_name = skillName;
      const run = await api<AgentRun>("/agent/runs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadAll(run.id);
      setObjective("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "创建计划失败");
    } finally {
      setBusy(false);
    }
  }

  async function updateRun(path: string, body?: object) {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<AgentRun>(`/agent/runs/${selected.id}/${path}`, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      await loadAll(updated.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function executeWithEvents() {
    if (!selected) return;
    const source = new EventSource(
      `${API_BASE}/agent/runs/${selected.id}/events?after=${selected.events.length}`,
    );
    source.addEventListener("agent_event", () => {
      loadAll(selected.id).catch(() => undefined);
    });
    source.addEventListener("run_complete", () => {
      source.close();
      loadAll(selected.id).catch(() => undefined);
    });
    source.onerror = () => source.close();
    await updateRun("execute");
    source.close();
  }

  return (
    <div>
      <div className="stat-grid">
        <div className="stat"><span>Agent Runs</span><strong>{runs.length}</strong></div>
        <div className="stat"><span>等待审批</span><strong>{waitingCount}</strong></div>
        <div className="stat"><span>已完成</span><strong>{completedCount}</strong></div>
      </div>

      {error ? <div className={`error-banner ${styles.error}`}>{error}</div> : null}

      <div className={styles.layout}>
        <section className="panel">
          <div className="panel-header">
            <div><h2>创建 Agent 计划</h2><p>Router → Planner → Policy → Preview</p></div>
            <Plus size={17} className="muted" />
          </div>
          <form className={styles.form} onSubmit={handlePreview}>
            <div className="field">
              <label htmlFor="skill">路由 / Skill</label>
              <select
                id="skill"
                className="select"
                value={skillName}
                onChange={(event) => setSkillName(event.target.value)}
              >
                <option value="auto">auto_router</option>
                {skills.map((skill) => (
                  <option key={skill.name} value={skill.name}>{skill.name}</option>
                ))}
              </select>
              <small className="muted">
                {skillName === "auto"
                  ? "由 Router 根据目标和参数自动选择 Skill"
                  : skills.find((skill) => skill.name === skillName)?.description}
              </small>
            </div>
            <div className="field">
              <label htmlFor="objective">目标</label>
              <textarea
                id="objective"
                className="textarea"
                value={objective}
                required
                placeholder="描述希望 Agent 完成的任务"
                onChange={(event) => setObjective(event.target.value)}
              />
            </div>

            {skillName === "hr_recruiting" ? (
              <div className={styles.hrFields}>
                <TextField label="候选人" value={candidateName} onChange={setCandidateName} />
                <TextField label="岗位" value={role} onChange={setRole} />
                <div className="field">
                  <label htmlFor="notes">面试记录</label>
                  <textarea id="notes" className="textarea" value={notes} required onChange={(e) => setNotes(e.target.value)} />
                </div>
                <TextField label="负责人" value={owner} onChange={setOwner} />
                <label className={styles.checkbox}>
                  <input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} />
                  执行后发送飞书通知
                </label>
              </div>
            ) : null}

            {skillName === "workspace_management" ? (
              <div className={styles.hrFields}>
                <div className="field">
                  <label htmlFor="task">工作项</label>
                  <select id="task" className="select" value={taskId} required onChange={(e) => setTaskId(e.target.value)}>
                    <option value="">选择任务</option>
                    {tasks.map((task) => <option key={task.id} value={task.id}>{task.title} ({task.status})</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="task-status">目标状态</label>
                  <select id="task-status" className="select" value={taskStatus} onChange={(e) => setTaskStatus(e.target.value)}>
                    <option value="open">open</option>
                    <option value="in_progress">in_progress</option>
                    <option value="completed">completed</option>
                    <option value="cancelled">cancelled</option>
                  </select>
                </div>
              </div>
            ) : null}

            {skillName === "mcp_tool" ? (
              <div className={styles.hrFields}>
                <div className="field">
                  <label htmlFor="mcp-tool">MCP Tool</label>
                  <select id="mcp-tool" className="select" value={mcpTool} required onChange={(e) => setMcpTool(e.target.value)}>
                    {mcpTools.map((tool) => <option key={tool.name} value={tool.name}>{tool.name}</option>)}
                  </select>
                </div>
                <JsonField value={jsonInputs} onChange={setJsonInputs} label="工具参数 JSON" />
              </div>
            ) : null}

            {skillName === "auto" ? (
              <JsonField value={jsonInputs} onChange={setJsonInputs} label="路由参数 JSON" />
            ) : null}

            <button className="btn primary" disabled={busy}>
              {busy ? <LoaderCircle className={styles.spin} size={16} /> : <Plus size={16} />}
              生成 Preview
            </button>
          </form>
        </section>

        <section className={`panel ${styles.runPanel}`}>
          <div className="panel-header">
            <div><h2>运行详情</h2><p>{selected ? selected.skill_name : "选择一个 Agent Run"}</p></div>
            {selected ? <StatusPill status={selected.status} /> : null}
          </div>
          {!selected ? (
            <div className="empty-state">创建计划后在这里审批和执行</div>
          ) : (
            <div className={styles.runBody}>
              <div className={styles.objective}><span>OBJECTIVE</span><p>{selected.objective}</p></div>
              <div className={styles.actionsHeader}><h3>Planned Actions</h3><span>{selected.actions.length} steps</span></div>
              <div className={styles.actions}>
                {selected.actions.map((action, index) => (
                  <article className={styles.action} key={action.id}>
                    <span className={styles.step}>{index + 1}</span>
                    <div>
                      <header>
                        <strong>{action.tool_name}</strong>
                        <span className={`${styles.risk} ${styles[`risk${capitalize(action.risk_level)}`]}`}>{action.risk_level}</span>
                        <StatusPill status={action.status} />
                      </header>
                      <p>{action.preview}</p>
                      <small>approval: {action.requires_approval ? "required" : "auto"} · attempts: {action.attempt_count}</small>
                      {action.result ? <details><summary>查看 Tool 结果</summary><pre>{JSON.stringify(action.result, null, 2)}</pre></details> : null}
                      {action.error ? <div className="error-banner">{action.error}</div> : null}
                    </div>
                  </article>
                ))}
              </div>
              <div className={styles.controls}>
                {selected.status === "awaiting_confirmation" ? (
                  <>
                    <button className="btn primary" disabled={busy} onClick={() => updateRun("confirm", { note: "Approved in workspace" })}><Check size={15} />确认计划</button>
                    <button className="btn danger" disabled={busy} onClick={() => updateRun("reject", { note: "Rejected in workspace" })}><CircleX size={15} />拒绝</button>
                  </>
                ) : null}
                {selected.status === "confirmed" ? <button className="btn primary" disabled={busy} onClick={executeWithEvents}><Play size={15} />执行 Actions</button> : null}
                {selected.status === "failed" ? <button className="btn" disabled={busy} onClick={() => updateRun("retry")}><RotateCcw size={15} />重试失败步骤</button> : null}
                <button className="btn icon-btn" title="刷新运行" aria-label="刷新运行" onClick={() => loadAll(selected.id).catch((e) => setError(e.message))}><RefreshCw size={15} /></button>
              </div>
              <div className={styles.audit}>
                <h3>Audit Events</h3>
                {selected.events.map((event) => (
                  <div key={event.id}><span /><p><strong>{event.event_type}</strong>{event.message}</p><time>{new Date(event.created_at).toLocaleTimeString("zh-CN")}</time></div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className={styles.rightColumn}>
          <section className="panel">
            <div className="panel-header"><div><h3>Recent Runs</h3><p>持久化运行记录</p></div></div>
            <div className={styles.runList}>
              {runs.map((run) => (
                <button key={run.id} className={run.id === selected?.id ? styles.selectedRun : ""} onClick={() => setSelectedId(run.id)}>
                  <span><strong>{run.objective}</strong><small>{run.skill_name}</small></span><StatusPill status={run.status} />
                </button>
              ))}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header"><div><h3>Providers</h3><p>当前运行模式</p></div></div>
            <div className={styles.providerList}>
              {providers.map((provider) => (
                <div key={provider.component}>
                  <span><strong>{provider.component}</strong><small>{provider.provider}</small></span>
                  <StatusPill status={provider.configured ? provider.mode : "disabled"} />
                </div>
              ))}
              <div><span><strong>feishu</strong><small>{feishu?.provider || "webhook"}</small></span><StatusPill status={feishu?.mode || "loading"} /></div>
            </div>
          </section>
        </aside>
      </div>

      <section className={`panel ${styles.tasks}`}>
        <div className="panel-header"><div><h2>Workspace Tasks</h2><p>由已确认 Agent Action 创建和更新</p></div></div>
        {tasks.length === 0 ? <div className="empty-state">暂无工作项</div> : (
          <div className={styles.tableWrap}>
            <table className="data-table"><thead><tr><th>任务</th><th>负责人</th><th>类型</th><th>状态</th></tr></thead>
              <tbody>{tasks.map((task) => <tr key={task.id}><td><strong>{task.title}</strong><div className="muted">{task.description}</div></td><td>{task.owner}</td><td>{task.kind}</td><td><StatusPill status={task.status} /></td></tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <div className="field"><label>{label}</label><input className="input" value={value} required onChange={(event) => onChange(event.target.value)} /></div>;
}

function JsonField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <div className="field"><label>{label}</label><textarea className="textarea" value={value} spellCheck={false} onChange={(event) => onChange(event.target.value)} /></div>;
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}