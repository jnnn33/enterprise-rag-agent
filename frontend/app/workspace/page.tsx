"use client";

import {
  Check,
  CircleX,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { StatusPill } from "@/components/status-pill";
import { API_BASE, api } from "@/lib/api";
import { AgentRun, Capability, WorkItem } from "@/lib/types";

import styles from "./workspace.module.css";

type FeishuStatus = { provider: string; configured: boolean; mode: string };

export default function WorkspacePage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [skills, setSkills] = useState<Capability[]>([]);
  const [tasks, setTasks] = useState<WorkItem[]>([]);
  const [feishu, setFeishu] = useState<FeishuStatus | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skillName, setSkillName] = useState("knowledge_qa");
  const [objective, setObjective] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [role, setRole] = useState("");
  const [notes, setNotes] = useState("");
  const [owner, setOwner] = useState("Recruiting team");
  const [notify, setNotify] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => runs.find((run) => run.id === selectedId) || runs[0] || null,
    [runs, selectedId],
  );
  const waitingCount = runs.filter(
    (run) => run.status === "awaiting_confirmation",
  ).length;
  const completedCount = runs.filter((run) => run.status === "completed").length;

  async function loadAll(preferredId?: string) {
    const [runItems, skillItems, taskItems, feishuStatus] = await Promise.all([
      api<AgentRun[]>("/agent/runs"),
      api<Capability[]>("/agent/skills"),
      api<WorkItem[]>("/workspace/tasks"),
      api<FeishuStatus>("/workspace/integrations/feishu"),
    ]);
    setRuns(runItems);
    setSkills(skillItems);
    setTasks(taskItems);
    setFeishu(feishuStatus);
    setSelectedId((current) => preferredId || current || runItems[0]?.id || null);
  }

  useEffect(() => {
    loadAll().catch((reason: Error) => setError(reason.message));
  }, []);

  async function handlePreview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const inputs =
        skillName === "hr_recruiting"
          ? {
              workflow: "candidate_review",
              candidate_name: candidateName,
              role,
              interview_notes: notes,
              owner,
              notify,
            }
          : { top_k: 3 };
      const run = await api<AgentRun>("/agent/runs", {
        method: "POST",
        body: JSON.stringify({ objective, skill_name: skillName, inputs }),
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
      const updated = await api<AgentRun>(
        `/agent/runs/${selected.id}/${path}`,
        {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        },
      );
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
        <div className="stat">
          <span>Agent Runs</span>
          <strong>{runs.length}</strong>
        </div>
        <div className="stat">
          <span>等待审批</span>
          <strong>{waitingCount}</strong>
        </div>
        <div className="stat">
          <span>已完成</span>
          <strong>{completedCount}</strong>
        </div>
      </div>

      {error ? <div className={`error-banner ${styles.error}`}>{error}</div> : null}

      <div className={styles.layout}>
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>创建 Agent 计划</h2>
              <p>先预览，确认后才能执行 Tool</p>
            </div>
            <Plus size={17} className="muted" />
          </div>
          <form className={styles.form} onSubmit={handlePreview}>
            <div className="field">
              <label htmlFor="skill">Skill</label>
              <select
                id="skill"
                className="select"
                value={skillName}
                onChange={(event) => setSkillName(event.target.value)}
              >
                {skills.map((skill) => (
                  <option key={skill.name} value={skill.name}>
                    {skill.name}
                  </option>
                ))}
              </select>
              <small className="muted">
                {skills.find((skill) => skill.name === skillName)?.description}
              </small>
            </div>
            <div className="field">
              <label htmlFor="objective">目标</label>
              <textarea
                id="objective"
                className="textarea"
                value={objective}
                required
                placeholder={
                  skillName === "knowledge_qa"
                    ? "例如：总结远程办公补贴制度"
                    : "例如：评估候选人并创建后续跟进任务"
                }
                onChange={(event) => setObjective(event.target.value)}
              />
            </div>
            {skillName === "hr_recruiting" ? (
              <div className={styles.hrFields}>
                <div className="field">
                  <label htmlFor="candidate">候选人</label>
                  <input
                    id="candidate"
                    className="input"
                    value={candidateName}
                    required
                    onChange={(event) => setCandidateName(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="role">岗位</label>
                  <input
                    id="role"
                    className="input"
                    value={role}
                    required
                    onChange={(event) => setRole(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="notes">面试记录</label>
                  <textarea
                    id="notes"
                    className="textarea"
                    value={notes}
                    required
                    onChange={(event) => setNotes(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="owner">负责人</label>
                  <input
                    id="owner"
                    className="input"
                    value={owner}
                    onChange={(event) => setOwner(event.target.value)}
                  />
                </div>
                <label className={styles.checkbox}>
                  <input
                    type="checkbox"
                    checked={notify}
                    onChange={(event) => setNotify(event.target.checked)}
                  />
                  执行后发送飞书通知
                </label>
              </div>
            ) : null}
            <button className="btn primary" disabled={busy}>
              {busy ? <LoaderCircle className={styles.spin} size={16} /> : <Plus size={16} />}
              生成 Preview
            </button>
          </form>
        </section>

        <section className={`panel ${styles.runPanel}`}>
          <div className="panel-header">
            <div>
              <h2>运行详情</h2>
              <p>{selected ? selected.skill_name : "选择一个 Agent Run"}</p>
            </div>
            {selected ? <StatusPill status={selected.status} /> : null}
          </div>
          {!selected ? (
            <div className="empty-state">创建一个计划后在这里审批和执行</div>
          ) : (
            <div className={styles.runBody}>
              <div className={styles.objective}>
                <span>OBJECTIVE</span>
                <p>{selected.objective}</p>
              </div>
              <div className={styles.actionsHeader}>
                <h3>Planned Actions</h3>
                <span>{selected.actions.length} steps</span>
              </div>
              <div className={styles.actions}>
                {selected.actions.map((action, index) => (
                  <article className={styles.action} key={action.id}>
                    <span className={styles.step}>{index + 1}</span>
                    <div>
                      <header>
                        <strong>{action.tool_name}</strong>
                        <StatusPill status={action.status} />
                      </header>
                      <p>{action.preview}</p>
                      <small>attempts: {action.attempt_count}</small>
                      {action.result ? (
                        <details>
                          <summary>查看 Tool 结果</summary>
                          <pre>{JSON.stringify(action.result, null, 2)}</pre>
                        </details>
                      ) : null}
                      {action.error ? <div className="error-banner">{action.error}</div> : null}
                    </div>
                  </article>
                ))}
              </div>
              <div className={styles.controls}>
                {selected.status === "awaiting_confirmation" ? (
                  <>
                    <button
                      className="btn primary"
                      disabled={busy}
                      onClick={() => updateRun("confirm", { note: "Approved in workspace" })}
                    >
                      <Check size={15} /> 确认计划
                    </button>
                    <button
                      className="btn danger"
                      disabled={busy}
                      onClick={() => updateRun("reject", { note: "Rejected in workspace" })}
                    >
                      <CircleX size={15} /> 拒绝
                    </button>
                  </>
                ) : null}
                {selected.status === "confirmed" ? (
                  <button className="btn primary" disabled={busy} onClick={executeWithEvents}>
                    <Play size={15} /> 执行 Actions
                  </button>
                ) : null}
                {selected.status === "failed" ? (
                  <button className="btn" disabled={busy} onClick={() => updateRun("retry")}>
                    <RotateCcw size={15} /> 重试失败步骤
                  </button>
                ) : null}
                <button
                  className="btn icon-btn"
                  title="刷新运行"
                  aria-label="刷新运行"
                  onClick={() => loadAll(selected.id).catch((e) => setError(e.message))}
                >
                  <RefreshCw size={15} />
                </button>
              </div>
              <div className={styles.audit}>
                <h3>Audit Events</h3>
                {selected.events.map((event) => (
                  <div key={event.id}>
                    <span />
                    <p>
                      <strong>{event.event_type}</strong>
                      {event.message}
                    </p>
                    <time>{new Date(event.created_at).toLocaleTimeString("zh-CN")}</time>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className={styles.rightColumn}>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Recent Runs</h3>
                <p>持久化运行记录</p>
              </div>
            </div>
            <div className={styles.runList}>
              {runs.map((run) => (
                <button
                  key={run.id}
                  className={run.id === selected?.id ? styles.selectedRun : ""}
                  onClick={() => setSelectedId(run.id)}
                >
                  <span>
                    <strong>{run.objective}</strong>
                    <small>{run.skill_name}</small>
                  </span>
                  <StatusPill status={run.status} />
                </button>
              ))}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Feishu</h3>
                <p>企业消息适配器</p>
              </div>
              <Send size={15} className="muted" />
            </div>
            <div className={styles.integration}>
              <StatusPill status={feishu?.mode || "loading"} />
              <p>
                {feishu?.mode === "live"
                  ? "Webhook 已启用，审批后发送真实消息。"
                  : "当前为安全模拟模式，Tool 结果会完整记录。"}
              </p>
            </div>
          </section>
        </aside>
      </div>

      <section className={`panel ${styles.tasks}`}>
        <div className="panel-header">
          <div>
            <h2>Recruiting Tasks</h2>
            <p>由已确认的 HR Agent Action 创建</p>
          </div>
        </div>
        {tasks.length === 0 ? (
          <div className="empty-state">暂无招聘跟进任务</div>
        ) : (
          <div className={styles.tableWrap}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>任务</th>
                  <th>负责人</th>
                  <th>候选人 / 岗位</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <strong>{task.title}</strong>
                      <div className="muted">{task.description}</div>
                    </td>
                    <td>{task.owner}</td>
                    <td className="muted">
                      {String(task.metadata.candidate_name || "-")} /{" "}
                      {String(task.metadata.role || "-")}
                    </td>
                    <td><StatusPill status={task.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
