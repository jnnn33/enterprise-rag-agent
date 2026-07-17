# 第三课：Embedding、Qdrant 与混合检索

## 1. Embedding 是什么

Embedding 的作用是把一段文字转换成一组数字：

~~~text
"市内交通报销上限"
        ↓
[0.12, -0.03, 0.44, ...]
~~~

这组数字叫向量。真正的语义模型会让含义接近的文字在向量空间中距离更近。

当前项目使用 HashingEmbeddingProvider 跑通离线开发和自动化测试。它具有确定性，但不具备完整语义理解能力。后面替换成 BGE 或云端 Embedding 时，只替换 Provider。

## 2. Qdrant 保存什么

每个 Chunk 在 Qdrant 中对应一个 Point：

~~~text
Point
├── id：Chunk ID
├── vector：Embedding 向量
└── payload：原文、文档标题、来源、位置
~~~

SQLite 仍然是业务数据的主存储，Qdrant 是为了检索建立的索引。两者职责不同：

- SQLite：保存 Document 和 Chunk，保证业务数据持久化。
- Qdrant：保存向量和检索所需的 Payload，快速寻找相似 Chunk。

## 3. 为什么同时保留关键词检索

向量检索擅长语义近似，但订单号、金额、缩写和专有名词通常更适合关键词检索。

因此当前项目同时执行：

~~~text
用户问题
├── KeywordRetriever
└── QdrantVectorIndex
         ↓
    Reciprocal Rank Fusion
         ↓
      Top-K Chunks
~~~

## 4. RRF 是什么

RRF 不直接比较两种检索器的原始分数，而是根据排名融合：

~~~text
score = 1 / (k + rank)
~~~

如果同一个 Chunk 在关键词结果和向量结果中都排名靠前，它会获得两次加分。

这样可以避免关键词分数和向量相似度不在同一尺度的问题。

## 5. 当前代码位置

- services/embeddings.py：文字转向量。
- repositories/qdrant_index.py：向量写入和查询。
- services/hybrid_retrieval.py：RRF 融合。
- services/knowledge.py：文档入库时同步建立向量索引。
- core/container.py：组装所有组件，并在启动时恢复已有索引。

## 6. 你现在要记住的三句话

1. Chunk 是检索的最小单位。
2. Embedding 把 Chunk 转换成向量。
3. Qdrant 根据问题向量召回相似 Chunk。

## 7. 切换真实语义模型

将环境变量改为：

~~~env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSION=模型实际输出维度
~~~

服务启动时，Container 会创建 OpenAICompatibleEmbeddingProvider。知识服务、Qdrant 和混合检索不需要修改。

代码会校验：

- 返回向量数量是否等于输入文本数量
- 返回向量维度是否与配置一致
- 向量元素是否都是数字

## 8. 下一步

下一阶段会使用一组固定问题比较：

- 纯关键词检索
- 纯向量检索
- RRF 混合检索

只有评测结果能证明哪种检索方案更好，技术名称本身不能。
