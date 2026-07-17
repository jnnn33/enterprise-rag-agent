"use client";

import { BookOpen, LoaderCircle, MessageSquareText, Plus, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { ChatResponse, Conversation, ConversationMessage } from "@/lib/types";

import styles from "./ask.module.css";

type AskResult = { conversation: Conversation; response: ChatResponse };

export default function AskPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => conversations.find((item) => item.id === selectedId) || null,
    [conversations, selectedId],
  );
  const latestAssistant = [...(selected?.messages || [])]
    .reverse()
    .find((message) => message.role === "assistant");

  async function loadConversations(preferredId?: string) {
    const items = await api<Conversation[]>("/conversations");
    setConversations(items);
    setSelectedId((current) => preferredId || current || items[0]?.id || null);
  }

  useEffect(() => {
    loadConversations().catch((reason: Error) => setError(reason.message));
  }, []);

  async function createConversation(title = "New conversation") {
    const created = await api<Conversation>("/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
    await loadConversations(created.id);
    return created;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError("");
    try {
      const conversation =
        selected || (await createConversation(trimmed.slice(0, 48)));
      const result = await api<AskResult>(
        `/conversations/${conversation.id}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ question: trimmed, top_k: 3 }),
        },
      );
      setQuestion("");
      setConversations((current) => [
        result.conversation,
        ...current.filter((item) => item.id !== result.conversation.id),
      ]);
      setSelectedId(result.conversation.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "请求失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.layout}>
      <section className={`panel ${styles.history}`}>
        <div className="panel-header">
          <div>
            <h2>对话</h2>
            <p>{conversations.length} 个会话</p>
          </div>
          <button
            className="btn icon-btn"
            aria-label="新建对话"
            title="新建对话"
            onClick={() => createConversation().catch((e) => setError(e.message))}
          >
            <Plus size={16} />
          </button>
        </div>
        <div className={styles.historyList}>
          {conversations.length === 0 ? (
            <div className="empty-state">发送第一条问题开始对话</div>
          ) : (
            conversations.map((conversation) => (
              <button
                key={conversation.id}
                className={
                  conversation.id === selectedId
                    ? `${styles.historyItem} ${styles.active}`
                    : styles.historyItem
                }
                onClick={() => setSelectedId(conversation.id)}
              >
                <MessageSquareText size={15} />
                <span>
                  <strong>{conversation.title}</strong>
                  <small>{conversation.messages.length} 条消息</small>
                </span>
              </button>
            ))
          )}
        </div>
      </section>

      <section className={`panel ${styles.chat}`}>
        <div className="panel-header">
          <div>
            <h2>{selected?.title || "企业知识问答"}</h2>
            <p>回答严格附带知识库引用与执行轨迹</p>
          </div>
        </div>
        <div className={styles.messages}>
          {!selected || selected.messages.length === 0 ? (
            <div className={styles.welcome}>
              <span>
                <BookOpen size={22} />
              </span>
              <h2>从企业知识库中寻找答案</h2>
              <p>可以询问制度、流程、报销标准或已上传文档中的具体内容。</p>
            </div>
          ) : (
            selected.messages.map((message) => (
              <Message key={message.id} message={message} />
            ))
          )}
        </div>
        <form className={styles.composer} onSubmit={handleSubmit}>
          {error ? <div className="error-banner">{error}</div> : null}
          <div className={styles.composerRow}>
            <textarea
              className="textarea"
              value={question}
              placeholder="输入问题，Enter 发送，Shift + Enter 换行"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <button
              className="btn primary icon-btn"
              disabled={!question.trim() || busy}
              aria-label="发送问题"
              title="发送问题"
            >
              {busy ? (
                <LoaderCircle className={styles.spin} size={17} />
              ) : (
                <Send size={17} />
              )}
            </button>
          </div>
        </form>
      </section>

      <aside className={`panel ${styles.evidence}`}>
        <div className="panel-header">
          <div>
            <h2>Evidence</h2>
            <p>引用与 RAG Trace</p>
          </div>
        </div>
        {latestAssistant ? (
          <div className={styles.evidenceBody}>
            <h3>引用片段</h3>
            {(latestAssistant.metadata.citations || []).map((citation, index) => (
              <article className={styles.citation} key={citation.chunk_id}>
                <header>
                  <span>[{index + 1}]</span>
                  <strong>{citation.document_title}</strong>
                </header>
                <p>{citation.excerpt}</p>
                <small>
                  {citation.source} · score {citation.score.toFixed(3)}
                </small>
              </article>
            ))}
            {latestAssistant.metadata.citations?.length === 0 ? (
              <div className="empty-state">本次回答没有检索到证据</div>
            ) : null}
            {latestAssistant.metadata.trace ? (
              <>
                <h3>执行轨迹</h3>
                <dl className={styles.trace}>
                  <div>
                    <dt>Rewrite</dt>
                    <dd>{latestAssistant.metadata.trace.query_rewrite_strategy}</dd>
                  </div>
                  <div>
                    <dt>Retrieval</dt>
                    <dd>{latestAssistant.metadata.trace.retrieval_strategy}</dd>
                  </div>
                  <div>
                    <dt>Rerank</dt>
                    <dd>{latestAssistant.metadata.trace.rerank_strategy}</dd>
                  </div>
                  <div>
                    <dt>Answer</dt>
                    <dd>{latestAssistant.metadata.trace.answer_strategy}</dd>
                  </div>
                </dl>
              </>
            ) : null}
          </div>
        ) : (
          <div className="empty-state">完成一次问答后显示引用证据</div>
        )}
      </aside>
    </div>
  );
}

function Message({ message }: { message: ConversationMessage }) {
  return (
    <article
      className={
        message.role === "user"
          ? `${styles.message} ${styles.userMessage}`
          : `${styles.message} ${styles.assistantMessage}`
      }
    >
      <span className={styles.avatar}>{message.role === "user" ? "U" : "AI"}</span>
      <div>
        <strong>{message.role === "user" ? "你" : "Ask Runtime"}</strong>
        <p>{message.content}</p>
      </div>
    </article>
  );
}
