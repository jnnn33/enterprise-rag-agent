# 企业 RAG + Agent 零基础课程路线（44 课时）

项目功能已经完整实现，课程采用“从结果反推原理”的方式慢慢学习。每课只引入少量概念，并配合当前仓库中的真实代码练习。

## 第一部分：计算机与 Web 基础（1-6）

1. 前端、后端、服务器和浏览器分别是什么
2. URL、HTTP、API 与 JSON
3. 用 Postman / Swagger 调用第一个接口
4. Python 变量、字符串、列表和字典
5. 函数、参数、返回值与异常
6. 类、对象、模块和依赖注入

## 第二部分：FastAPI 后端（7-12）

7. FastAPI 应用入口和路由
8. Pydantic 请求与响应模型
9. Route、Service、Repository 分层
10. SQLite 表、行、主键和 SQL
11. Repository Protocol 与可替换实现
12. ApplicationContainer 如何组装系统

## 第三部分：知识库入库（13-17）

13. 文档上传与文件安全限制
14. TXT、Markdown、PDF、DOCX 解析
15. Chunk、窗口和重叠
16. 文档与 Chunk 持久化
17. 服务重启后恢复知识库

## 第四部分：检索与向量库（18-24）

18. 关键词检索与相关性
19. Embedding 向量的直观理解
20. 余弦相似度与 top_k
21. Qdrant Local 的集合和 Point
22. Milvus Schema、索引与检索
23. 关键词 + 向量混合检索
24. RRF 融合排名

## 第五部分：高级 RAG（25-30）

25. Prompt、System Message 与上下文
26. OpenAI-compatible Chat 和 Embedding 接口
27. Query Rewrite 查询改写
28. Reranker 二阶段重排
29. Answer、Citations 与 Trace
30. RAG 评测、命中率与回归测试

## 第六部分：Agent Runtime（31-38）

31. Agent、Skill 和 Tool 的区别
32. Router 如何选择 Skill
33. Planner 如何生成 Action
34. read、write、external 风险策略
35. Preview、Confirm、Execute 状态机
36. SQLite 持久化与审计事件
37. 失败、重试、幂等和乐观并发
38. 招聘 Skill 与工作项修改实战

## 第七部分：MCP 与实时交互（39-42）

39. MCP Server、Client、Transport 和 Tool Discovery
40. MCP Tool 接入审批与审计
41. SSE、事件流和 token 输出
42. Next.js 如何消费流并更新界面

## 第八部分：工程化与求职（43-44）

43. 自动化测试、Docker、配置和部署
44. 简历项目描述、架构讲解与面试演练

## 学习方式

每课按“先看现象 -> 画流程 -> 读少量代码 -> 自己改一处 -> 运行验证”进行。不会因为项目代码已经完成，就假设你已经掌握其中的知识。