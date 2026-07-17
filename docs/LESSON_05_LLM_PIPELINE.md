# 第五课：Query Rewrite、Rerank 与引用回答

## 完整问答链路

~~~text
用户问题
  -> Query Rewriter
  -> Keyword + Vector Retrieval
  -> RRF 候选融合
  -> Heuristic Reranker
  -> Answer Generator
  -> Answer + Citations + Trace
~~~

## 1. Query Rewrite

用户表达不一定适合直接检索，例如口语、代词和冗余描述会干扰召回。

当前提供两种实现：

- IdentityQueryRewriter：原问题直接进入检索，完全离线。
- LLMQueryRewriter：调用模型生成简洁检索语句，保留名称、数字、日期和领域词。

默认关闭 LLM 改写，避免没有模型配置时项目无法运行。

## 2. Rerank

第一阶段检索追求召回更多候选，第二阶段 Rerank 再精排。

当前 HeuristicReranker 根据问题词与 Chunk 词的覆盖率调整 RRF 分数：

~~~text
final_score = rrf_score + query_token_coverage
~~~

它可解释、可离线测试，但不等于 Cross-Encoder。后续可以在同一个 Reranker 接口下换成 BGE Reranker。

## 3. Answer Generator

当前提供两种实现：

- ExtractiveAnswerGenerator：直接展示召回证据，适合离线开发和调试。
- LLMAnswerGenerator：把问题和编号 Context 发给模型，要求只依据上下文回答并输出 [1]、[2] 引用标记。

即使启用 LLM，API 仍然单独返回结构化 Citations，前端不需要从自然语言中猜测来源。

## 4. OpenAI-compatible ChatModel

OpenAICompatibleChatModel 调用：

~~~text
POST {LLM_BASE_URL}/chat/completions
~~~

配置示例：

~~~env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-chat-model
QUERY_REWRITE_ENABLED=true
RERANKER_PROVIDER=heuristic
~~~

没有模型密钥时保持 LLM_PROVIDER=extractive，完整系统仍能运行。

## 5. Trace

每次回答都会返回：

- original_query
- rewritten_query
- query_rewrite_strategy
- retrieval_strategy
- rerank_strategy
- answer_strategy
- candidate_count
- returned_count

Trace 的价值是让你知道答案经过了哪些步骤，也为后续评测和故障排查提供依据。
