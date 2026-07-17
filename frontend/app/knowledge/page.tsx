"use client";

import { FileText, LoaderCircle, RefreshCw, Upload } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { DocumentSummary } from "@/lib/types";

import styles from "./knowledge.module.css";

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [mode, setMode] = useState<"file" | "manual">("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("manual");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const totalChunks = useMemo(
    () => documents.reduce((sum, document) => sum + document.chunk_count, 0),
    [documents],
  );
  const sourceCount = new Set(documents.map((item) => item.source)).size;

  async function loadDocuments() {
    setDocuments(await api<DocumentSummary[]>("/documents"));
  }

  useEffect(() => {
    loadDocuments().catch((reason: Error) => setError(reason.message));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "file") {
        if (!file) throw new Error("请选择 TXT、Markdown、PDF 或 DOCX 文件");
        const body = new FormData();
        body.append("file", file);
        await api<DocumentSummary>("/documents/upload", {
          method: "POST",
          body,
        });
        setFile(null);
      } else {
        await api<DocumentSummary>("/documents", {
          method: "POST",
          body: JSON.stringify({ title, source, content }),
        });
        setTitle("");
        setContent("");
      }
      await loadDocuments();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "入库失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="stat-grid">
        <div className="stat">
          <span>知识文档</span>
          <strong>{documents.length}</strong>
        </div>
        <div className="stat">
          <span>可检索 Chunks</span>
          <strong>{totalChunks}</strong>
        </div>
        <div className="stat">
          <span>数据来源</span>
          <strong>{sourceCount}</strong>
        </div>
      </div>

      <div className={styles.layout}>
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>文档入库</h2>
              <p>解析、切块、向量化并写入知识库</p>
            </div>
          </div>
          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.segmented}>
              <button
                type="button"
                className={mode === "file" ? styles.active : ""}
                onClick={() => setMode("file")}
              >
                文件上传
              </button>
              <button
                type="button"
                className={mode === "manual" ? styles.active : ""}
                onClick={() => setMode("manual")}
              >
                手动录入
              </button>
            </div>
            {mode === "file" ? (
              <label className={styles.dropzone}>
                <Upload size={23} />
                <strong>{file?.name || "选择知识文档"}</strong>
                <span>支持 TXT、MD、PDF、DOCX，最大 5 MB</span>
                <input
                  type="file"
                  accept=".txt,.md,.markdown,.pdf,.docx"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
              </label>
            ) : (
              <>
                <div className="field">
                  <label htmlFor="document-title">文档标题</label>
                  <input
                    id="document-title"
                    className="input"
                    value={title}
                    required
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="document-source">来源标识</label>
                  <input
                    id="document-source"
                    className="input"
                    value={source}
                    required
                    onChange={(event) => setSource(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="document-content">正文</label>
                  <textarea
                    id="document-content"
                    className="textarea"
                    value={content}
                    required
                    onChange={(event) => setContent(event.target.value)}
                  />
                </div>
              </>
            )}
            {error ? <div className="error-banner">{error}</div> : null}
            <button className="btn primary" disabled={busy}>
              {busy ? <LoaderCircle className={styles.spin} size={16} /> : <Upload size={16} />}
              {busy ? "处理中" : "写入知识库"}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>已入库文档</h2>
              <p>SQLite 元数据与 Qdrant 索引保持同步</p>
            </div>
            <button
              className="btn icon-btn"
              title="刷新文档"
              aria-label="刷新文档"
              onClick={() => loadDocuments().catch((e) => setError(e.message))}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className={styles.tableWrap}>
            {documents.length === 0 ? (
              <div className="empty-state">知识库为空，请先上传一份文档</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>文档</th>
                    <th>来源</th>
                    <th>Chunks</th>
                    <th>入库时间</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => (
                    <tr key={document.id}>
                      <td>
                        <span className={styles.documentTitle}>
                          <FileText size={15} />
                          <strong>{document.title}</strong>
                        </span>
                      </td>
                      <td className="muted">{document.source}</td>
                      <td>{document.chunk_count}</td>
                      <td className="muted">
                        {new Date(document.created_at).toLocaleString("zh-CN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
