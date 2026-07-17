"use client";

import { BookOpen, LoaderCircle, MessageSquareText, Plus, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, streamApi } from "@/lib/api";
import {
  Citation,
  Conversation,
  ConversationMessage,
  RagTrace,
} from "@/lib/types";

import styles from "./ask.module.css";

type StreamState = {
  conversationId: string;
  question: string;
  answer: string;
  status: string;
  citations: Citation[];
  trace?: RagTrace;
};

export default function AskPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState<StreamState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => conversations.find((item) => item.id === selectedId) || null,
    [conversations, selectedId],
  );
  const visibleMessages = useMemo(() => {
    const messages = selected?.messages || [];
    if (!streaming || streaming.conversationId !== selectedId) return messages;
    const now = new Date().toISOString();
    const pending: ConversationMessage[] = [
      {
        id: "stream-user",
        role: "user",
        content: streaming.question,
        metadata: {},
        created_at: now,
      },
      {
        id: "stream-assistant",
        role: "assistant",
        content: streaming.answer,
        metadata: {
          citations: streaming.citations,
          trace: streaming.trace,
          display_question: streaming.question,
        },
        created_at: now,
      },
    ];
    return [...messages, ...pending];
  }, [selected, selectedId, streaming]);
  const latestAssistant = [...visibleMessages]
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

  async function createConversation(title = "新对话") {
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
    let activeId: string | undefined;
    try {
      const conversation =
        selected || (await createConversation(trimmed.slice(0, 48)));
      activeId = conversation.id;
      setSelectedId(activeId);
      setQuestion("");
      setStreaming({
        conversationId: activeId,
        question: trimmed,
        answer: "",
        status: "正在检索证据",
        citations: [],
      });
      await streamApi(
        `/conversations/${activeId}/messages/stream`,
        {
          method: "POST",
          body: JSON.stringify({ question: trimmed, top_k: 3 }),
        },
        ({ event: eventName, data }) => {
          if (eventName === "status") {
            const message = String(data.message || "处理中");
            setStreaming((current) =>
              current ? { ...current, status: message } : current,
            );
          }
          if (eventName === "evidence") {
            setStreaming((current) =>
              current
                ? {
                    ...current,
                    citations: (data.citations || []) as Citation[],
                    trace: data.trace as RagTrace,
                  }
                : current,
            );
          }
          if (eventName === "token") {
            const text = String(data.text || "");
            setStreaming((current) =>
              current
                ? { ...current, answer: current.answer + text, status: "正在生成回答" }
                : current,
            );
          }
          if (eventName === "error") {
            throw new Error(String(data.message || "流式回答失败"));
          }
        },
      );
      await loadConversations(activeId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "请求失败");
      if (activeId) await loadConversations(activeId).catch(() => undefined);
    } finally {
      setStreaming(null);
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
            <p>{streaming?.status || "回答附带知识库引用与执行轨迹"}</p>
          </div>
          {streaming ? <LoaderCircle className={styles.spin} size={16} /> : null}
        </div>
        <div className={styles.messages}>
          {visibleMessages.length === 0 ? (
            <div className={styles.welcome}>
              <span><BookOpen size={22} /></span>
              <h2>从企业知识库中寻找答案</h2>
              <p>可以询问制度、流程、报销标准或已上传文档中的具体内容。</p>
            </div>
          ) : (
            visibleMessages.map((message) => (
              <Message
                key={message.id}
                message={message}
                pending={message.id === "stream-assistant"}
              />
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
              {busy ? <LoaderCircle className={styles.spin} size={17} /> : <Send size={17} />}
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
                <small>{citation.source} · score {citation.score.toFixed(3)}</small>
              </article>
            ))}
            {latestAssistant.metadata.citations?.length === 0 ? (
              <div className="empty-state">本次回答没有检索到证据</div>
            ) : null}
            {latestAssistant.metadata.trace ? (
              <>
                <h3>执行轨迹</h3>
                <dl className={styles.trace}>
                  <div><dt>Rewrite</dt><dd>{latestAssistant.metadata.trace.query_rewrite_strategy}</dd></div>
                  <div><dt>Retrieval</dt><dd>{latestAssistant.metadata.trace.retrieval_strategy}</dd></div>
                  <div><dt>Rerank</dt><dd>{latestAssistant.metadata.trace.rerank_strategy}</dd></div>
                  <div><dt>Answer</dt><dd>{latestAssistant.metadata.trace.answer_strategy}</dd></div>
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

function Message({
  message,
  pending = false,
}: {
  message: ConversationMessage;
  pending?: boolean;
}) {
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
        <p>{message.content || (pending ? "正在生成..." : "")}</p>
      </div>
    </article>
  );
}