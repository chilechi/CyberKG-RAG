# CyberKG-RAG

基于知识图谱的网络安全知识问答系统。本项目围绕 CVE、CWE、CAPEC、MITRE ATT&CK 等公开安全知识数据，构建网络安全知识图谱，并结合 Neo4j 图谱检索、Milvus 向量检索、PostgreSQL 结构化存储、知识图谱补全模型和大语言模型，实现可追溯的 KG-RAG 安全问答。

## 代码组织

正式项目代码统一放在当前目录 `code/` 下，后端和前端分开维护：

```text
code/
  backend/      # FastAPI 后端、数据处理、KG-RAG、图谱补全
  frontend/     # Vue3 前端、ECharts 图谱可视化
  data/         # 原始数据、处理后数据、样例数据
  scripts/      # 数据导入、初始化、实验辅助脚本
  experiments/  # 图谱补全实验、问答评估
  docs/         # 项目内部说明文档
```

## 运行环境

### 操作系统

推荐环境：

- Windows 10/11 + Docker Desktop
- Ubuntu 20.04/22.04
- macOS 13+

开发和演示阶段建议优先使用 Docker Compose 启动 PostgreSQL、Neo4j、Milvus 等基础服务，减少本机环境差异。

### Python 版本

推荐版本：

```text
Python 3.10+
```

建议使用虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS：

```bash
source .venv/bin/activate
```

### Node.js 版本

如果运行前端 Demo，推荐：

```text
Node.js 18+
pnpm 8+ 或 npm 9+
```

### 基础服务

计划使用以下服务：

| 服务 | 用途 |
|---|---|
| PostgreSQL | 存储原始数据、结构化实体、文档片段、实验结果、问答日志 |
| Neo4j | 存储知识图谱节点和关系，支持多跳路径查询 |
| Milvus | 存储文本向量，支持语义检索 |
| FastAPI | 后端 API 服务 |
| Vue3 | 前端可视化 Demo |

## 依赖库

后端主要依赖计划如下：

```text
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy
psycopg2-binary
neo4j
pymilvus
pandas
numpy
pykeen
torch
sentence-transformers
httpx
python-dotenv
pytest
```

前端主要依赖计划如下：

```text
vue
vite
typescript
echarts
axios
pinia
vue-router
```

最终依赖以后续 `requirements.txt`、`pyproject.toml`、`package.json` 为准。

## 数据来源

本项目计划使用公开网络安全知识库，不采集真实系统的敏感日志或未授权数据。

| 数据源 | 内容 | 用途 |
|---|---|---|
| NVD / CVE | 漏洞编号、描述、CVSS、CWE 映射 | 构建漏洞实体和漏洞属性 |
| CWE | 软件弱点类型、描述、层级关系 | 构建弱点实体 |
| CAPEC | 攻击模式、攻击步骤、相关弱点 | 构建攻击模式实体 |
| MITRE ATT&CK | 攻击技术、战术、缓解措施、检测建议 | 构建攻击技术、战术和防护知识 |

参考链接：

- NVD API: https://nvd.nist.gov/developers/vulnerabilities
- MITRE CWE: https://cwe.mitre.org/
- MITRE CAPEC: https://capec.mitre.org/
- MITRE ATT&CK: https://attack.mitre.org/
- MITRE CTI: https://github.com/mitre/cti

## 运行步骤

当前项目仍处于规划和初始化阶段。下面是目标运行方式，后续代码完成后按此流程执行。

### 1. 克隆项目

```bash
git clone <repo-url>
cd CyberKG-RAG
```

### 2. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

需要配置的核心变量包括：

```text
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=

MILVUS_HOST=
MILVUS_PORT=

DEEPSEEK_API_KEY=
```

### 3. 启动基础服务

```bash
docker compose up -d
```

计划启动：

- PostgreSQL
- Neo4j
- Milvus

### 4. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 5. 初始化数据

```bash
python scripts/import_postgres.py
python scripts/import_neo4j.py
python scripts/import_milvus.py
```

### 6. 启动后端

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```text
http://localhost:8000/health
```

### 7. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

## 预期功能

1. 图谱实体查询。
2. 图谱邻居和多跳路径可视化。
3. KG-RAG 安全问答。
4. 知识图谱补全预测。
5. TransE、ComplEx、RotatE 实验结果展示。

## 项目状态

当前状态：

```text
规划阶段 / 初始化阶段
```

已完成：

1. B 题技术方案。
2. B 题开发计划。
3. README 初版运行说明。

待完成：

1. 项目工程结构初始化。
2. Docker Compose 编写。
3. 数据采集与清洗脚本。
4. 后端 API。
5. 前端 Demo。
6. 图谱补全实验。

## 相关文档

- `文档/B题技术方案.md`
- `文档/B题开发计划.md`
