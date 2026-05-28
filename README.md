# CyberKG-RAG

CyberKG-RAG 是一个面向网络安全知识的知识图谱增强问答系统。项目围绕 CVE、CWE、CAPEC、MITRE ATT&CK、缓解措施和安全文档片段构建知识库，并结合 PostgreSQL、Neo4j、Milvus、DeepSeek 和阿里云 DashScope Embedding 实现可溯源问答、图谱查询、问答对比实验和知识补全演示。

## 项目结构

```text
code/
  backend/        FastAPI 后端接口、检索服务、问答服务
  frontend/       Vue3 + Vite 前端页面
  docker/         PostgreSQL、Neo4j、Milvus、Attu 等容器编排
  data/
    samples/      项目内置样例实体、关系、文本片段
    raw/          原始数据输入目录，默认只保留示例文件
    eval/         问答评测集
  scripts/        数据导入、检查、评测、Obsidian 导出脚本
  experiments/    问答评测结果
  docs/           项目内部说明
```

## 运行环境

推荐环境：

- Windows 10/11 + PowerShell
- Docker Desktop
- Python 3.10+
- Node.js 18+，npm 9+

后端主要依赖见 [backend/requirements.txt](backend/requirements.txt)，前端依赖见 [frontend/package.json](frontend/package.json)。

## 数据来源

当前项目使用两类数据：

- 内置样例数据：`data/samples/entities.json`、`relations.json`、`doc_chunks.json`
- 原始数据示例：`data/raw/security_records.example.json`

数据内容围绕公开安全知识组织，包括：

- CVE / NVD 漏洞信息
- CWE 弱点类型
- CAPEC 攻击模式
- MITRE ATT&CK 技术和战术
- 安全缓解措施、产品、文本证据片段

项目只使用公开安全知识数据，不采集未授权目标或真实敏感日志。

## 三库存储说明

PostgreSQL 保存结构化业务数据：

- `entities`：图谱实体，如 CVE、CWE、CAPEC、ATT&CK 技术、产品、缓解措施
- `relations`：实体之间的关系三元组
- `doc_chunks`：文本证据片段
- `qa_history`：智能问答历史记录

Neo4j 保存知识图谱：

- 节点：实体
- 边：实体关系，如 `HAS_WEAKNESS`、`USES_TECHNIQUE`、`HAS_MITIGATION`

Milvus 保存文本向量：

- collection 默认为 `cyber_doc_chunks`
- 用于普通 RAG 和 KG-RAG 的语义检索

Attu 用于查看 Milvus：

```text
http://localhost:8001
```

## 环境变量

复制模板：

```powershell
Copy-Item .env.example .env
```

核心变量：

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cyberkg
POSTGRES_USER=cyberkg
POSTGRES_PASSWORD=cyberkg

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=cyber_doc_chunks

EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
DASHSCOPE_API_KEY=

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=60
```

说明：

- `EMBEDDING_PROVIDER=mock` 时使用本地确定性向量，方便无 Key 跑通链路。
- 使用阿里云文本向量时，将 `EMBEDDING_PROVIDER` 改为 `dashscope` 并填写 `DASHSCOPE_API_KEY`。
- `.env` 已加入 `.gitignore`，不要提交真实 Key。

## 启动基础服务

在 `code/` 目录执行：

```powershell
docker compose -f docker\docker-compose.yml --env-file .env up -d
```

查看容器状态：

```powershell
docker compose -f docker\docker-compose.yml --env-file .env ps
```

服务端口：

```text
PostgreSQL  localhost:5432
Neo4j       http://localhost:7474 / bolt://localhost:7687
Milvus      localhost:19530
Attu        http://localhost:8001
MinIO       http://localhost:9001
```

## 安装依赖

后端：

```powershell
cd backend
pip install -r requirements.txt
cd ..
```

前端：

```powershell
cd frontend
npm install
cd ..
```

## 初始化数据

在 `code/` 目录执行：

```powershell
python scripts\import_postgres.py
python scripts\import_neo4j.py
python scripts\import_milvus.py
```

查看数据结构和内容：

```powershell
# PostgreSQL 查询脚本
psql -h localhost -p 5432 -U cyberkg -d cyberkg -f scripts\inspect_postgres.sql

# Neo4j Cypher 示例
Get-Content scripts\inspect_neo4j.cypher

# Milvus collection 检查
python scripts\inspect_milvus.py
```

## 启动后端

在 `code/backend` 目录执行：

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```text
http://localhost:8000/health
http://localhost:8000/health/dependencies
```

## 启动前端

在 `code/frontend` 目录执行：

```powershell
npm run dev
```

访问：

```text
http://localhost:5173
```

如果前端出现接口错误，先确认后端 `http://localhost:8000` 已启动。

## 已实现页面

- 系统总览：三库状态、实体/关系/文档数量、数据来源概览
- 知识图谱查询：按实体 ID 查询 Neo4j 邻居图
- 智能问答：支持普通 LLM、普通 RAG、KG-RAG 三种模式切换
- 问答对比实验：一次性对比普通 LLM、普通 RAG、KG-RAG，并展示离线评测结果
- 知识补全实验：基于图谱三元组的 Top-K 补全演示和指标展示
- 数据管理：展示数据来源、导入流程和三库存储数量
- 问答历史：查看和删除历史问答记录
- 系统设置：查看模型配置状态和三库连接状态

## 问答模式

智能问答页支持三种模式：

- 普通 LLM：直接调用 DeepSeek，不使用检索证据
- 普通 RAG：检索 Milvus 文本证据，再调用 DeepSeek
- KG-RAG：识别实体，查询 Neo4j 图谱路径，检索 Milvus 文本证据，再调用 DeepSeek

DeepSeek 输出要求为 Markdown，前端会渲染标题、列表、加粗、行内代码和代码块。

## 问答评测

评测集：

```text
data/eval/qa_eval.json
```

运行评测：

```powershell
python scripts\evaluate_qa.py
```

输出结果：

```text
experiments/qa_eval/results.json
experiments/qa_eval/summary.json
```

问答对比实验页面会读取这些结果展示平均综合分、实体命中率、关系命中率、关键词覆盖率和平均耗时。

## Obsidian 导出

将图谱实体和关系导出到 Obsidian vault：

```powershell
python scripts\export_obsidian.py
```

当前导出目标：

```text
D:\enviroment\obsidian\myresposity\cyberkg
```

导出内容包括实体 Markdown 笔记、索引页和 JSON Canvas 图谱。

## 项目检查

执行整体检查：

```powershell
python scripts\check_project.py
```

检查内容包括：

- PostgreSQL / Neo4j / Milvus 连通性
- PostgreSQL 表数据
- 系统总览接口
- Neo4j 图谱查询
- Milvus 文本检索
- 知识补全实验
- KG-RAG 智能问答
- 问答对比实验

前端构建检查：

```powershell
cd frontend
npm run build
```

## 常用 Git 提交

不要提交 `.env` 和 `codeguard.db`。

```powershell
git status
git add backend/app frontend/src data/eval/qa_eval.json experiments/qa_eval/results.json experiments/qa_eval/summary.json scripts/evaluate_qa.py scripts/export_obsidian.py README.md
git commit -m "完善项目功能和运行说明"
git push
```
