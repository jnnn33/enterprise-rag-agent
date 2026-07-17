"use client";

import { CheckCircle2, FlaskConical, LoaderCircle, Plus, XCircle } from "lucide-react";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import { EvaluationReport } from "@/lib/types";

import styles from "./evaluations.module.css";

type EvaluationCase = { question: string; expected_terms: string[] };

export default function EvaluationsPage() {
  const [question, setQuestion] = useState("");
  const [terms, setTerms] = useState("");
  const [cases, setCases] = useState<EvaluationCase[]>([]);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function addCase(event: FormEvent) {
    event.preventDefault();
    const expectedTerms = terms
      .split(",")
      .map((term) => term.trim())
      .filter(Boolean);
    if (!question.trim() || expectedTerms.length === 0) return;
    setCases((current) => [
      ...current,
      { question: question.trim(), expected_terms: expectedTerms },
    ]);
    setQuestion("");
    setTerms("");
  }

  async function runEvaluation() {
    if (cases.length === 0) return;
    setBusy(true);
    setError("");
    try {
      setReport(
        await api<EvaluationReport>("/evaluations/rag", {
          method: "POST",
          body: JSON.stringify({ cases }),
        }),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "评测失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.layout}>
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>RAG 评测集</h2>
            <p>用预期事实和引用覆盖率验证回答</p>
          </div>
          <FlaskConical size={17} className="muted" />
        </div>
        <form className={styles.form} onSubmit={addCase}>
          <div className="field">
            <label htmlFor="eval-question">问题</label>
            <textarea
              id="eval-question"
              className="textarea"
              value={question}
              required
              placeholder="例如：远程办公补贴是多少？"
              onChange={(event) => setQuestion(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="expected-terms">预期关键词</label>
            <input
              id="expected-terms"
              className="input"
              value={terms}
              required
              placeholder="300元, 每月"
              onChange={(event) => setTerms(event.target.value)}
            />
          </div>
          <button className="btn">
            <Plus size={15} /> 添加 Case
          </button>
        </form>
        <div className={styles.caseList}>
          {cases.length === 0 ? (
            <div className="empty-state">添加至少一个评测问题</div>
          ) : (
            cases.map((item, index) => (
              <article key={`${item.question}-${index}`}>
                <span>{index + 1}</span>
                <div>
                  <strong>{item.question}</strong>
                  <small>{item.expected_terms.join(" · ")}</small>
                </div>
                <button
                  aria-label="删除 Case"
                  title="删除 Case"
                  onClick={() =>
                    setCases((current) => current.filter((_, i) => i !== index))
                  }
                >
                  <XCircle size={15} />
                </button>
              </article>
            ))
          )}
        </div>
        {error ? <div className={`error-banner ${styles.error}`}>{error}</div> : null}
        <div className={styles.runBar}>
          <button
            className="btn primary"
            disabled={busy || cases.length === 0}
            onClick={runEvaluation}
          >
            {busy ? <LoaderCircle className={styles.spin} size={16} /> : <FlaskConical size={16} />}
            运行评测
          </button>
        </div>
      </section>

      <section className={`panel ${styles.report}`}>
        <div className="panel-header">
          <div>
            <h2>评测报告</h2>
            <p>Term Match + Citation Coverage</p>
          </div>
          {report ? (
            <strong className={report.pass_rate === 1 ? styles.good : styles.warn}>
              {(report.pass_rate * 100).toFixed(0)}%
            </strong>
          ) : null}
        </div>
        {!report ? (
          <div className={styles.reportEmpty}>
            <FlaskConical size={28} />
            <p>运行评测后显示逐题答案、关键词命中和引用数量。</p>
          </div>
        ) : (
          <div className={styles.results}>
            <div className={styles.summary}>
              <div>
                <span>Cases</span>
                <strong>{report.case_count}</strong>
              </div>
              <div>
                <span>Passed</span>
                <strong>{report.passed_count}</strong>
              </div>
              <div>
                <span>Pass rate</span>
                <strong>{(report.pass_rate * 100).toFixed(0)}%</strong>
              </div>
            </div>
            {report.results.map((result, index) => (
              <article className={styles.result} key={`${result.question}-${index}`}>
                <header>
                  {result.passed ? (
                    <CheckCircle2 size={17} className={styles.goodIcon} />
                  ) : (
                    <XCircle size={17} className={styles.badIcon} />
                  )}
                  <strong>{result.question}</strong>
                  <span>{(result.term_score * 100).toFixed(0)}%</span>
                </header>
                <p>{result.answer}</p>
                <footer>
                  <span>命中：{result.matched_terms.join(", ") || "无"}</span>
                  <span>引用：{result.citation_count}</span>
                </footer>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
