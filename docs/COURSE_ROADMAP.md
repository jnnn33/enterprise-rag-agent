# 企业 RAG + Agent 学习路线

第一项目安排 30 课时，按照零基础节奏学习。项目开发可以领先课程，但每一课只引入少量新概念。第二个 NL2SQL 数据分析 Agent 项目预计另设 20 课时，两项合计约 50 课时。

## 第一部分：认识后端与 Python

1. 前端、后端、服务器、API、JSON 与 RAG
2. Pydantic 字段类型与参数校验
3. FastAPI 路由与接口地址
4. 函数调用与 Route、Service 分工
5. Python 变量、函数、类与对象
6. ApplicationContainer 与依赖注入

## 第二部分：知识库入库链路

7. 文档录入 API 与领域模型
8. SQLite 数据库和持久化
9. 文件上传、大小限制与异常处理
10. TXT、Markdown、PDF、DOCX 解析
11. Chunk 文本切分与重叠窗口

## 第三部分：检索系统

12. 关键词检索和相关性
13. Embedding 向量的直观理解
14. 相似度与向量召回
15. Qdrant 向量数据库
16. 关键词与向量混合检索
17. RRF 融合排序
18. Rerank 二阶段重排

## 第四部分：大模型 RAG 链路

19. Prompt、System Message 与上下文
20. OpenAI-compatible 模型接口
21. Query Rewrite 查询改写
22. Answer、Citations 与 Trace

## 第五部分：Agent Runtime

23. Agent、Skill、Tool 三个角色
24. preview、confirm、execute 状态机
25. Agent 任务持久化与审计事件
26. 失败处理、重试、权限和安全边界

## 第六部分：前端与上线

27. Next.js、TypeScript 与基础页面
28. SSE 流式响应与任务状态同步
29. RAG 评测、自动化测试与质量指标
30. Docker、部署、简历表述与面试演练

当前学习进度：已完成第 3 课。下一课学习 `chat()` 如何调用 `RagService`，以及接口层与业务层为什么要分开。
