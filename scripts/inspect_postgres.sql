-- CyberKG-RAG PostgreSQL 表结构说明与查看 SQL
-- 使用方式：
-- docker exec -it cyberkg-postgres psql -U cyberkg -d cyberkg -f /path/in/container/inspect_postgres.sql
-- 或进入 psql 后复制本文件里的 SQL 分段执行。

-- ============================================================
-- 1. entities：实体表
-- ============================================================
-- 作用：
--   保存知识图谱中的所有实体，也就是图谱里的“点”。
--
-- 字段含义：
--   id          实体唯一 ID，例如 CVE-2021-44228、CWE-502、T1190。
--   name        实体名称，例如 Log4Shell、Deserialization of Untrusted Data。
--   type        实体类型，例如 Vulnerability、Weakness、Technique、Mitigation。
--   description 实体描述，用于页面展示和问答解释。
--
-- 关联关系：
--   entities.id = relations.source
--   entities.id = relations.target
--   entities.id = doc_chunks.entity_id

SELECT COUNT(*) AS entities_count FROM entities;

SELECT id, name, type, description
FROM entities
ORDER BY type, id
LIMIT 20;

SELECT type, COUNT(*) AS count
FROM entities
GROUP BY type
ORDER BY count DESC, type;

-- ============================================================
-- 2. relations：关系表
-- ============================================================
-- 作用：
--   保存实体之间的关系三元组，也就是图谱里的“边”。
--
-- 字段含义：
--   source   起点实体 ID，关联 entities.id。
--   relation 关系类型，例如 HAS_WEAKNESS、USES_TECHNIQUE、HAS_MITIGATION。
--   target   终点实体 ID，关联 entities.id。
--
-- 三元组示例：
--   CVE-2021-44228 --HAS_WEAKNESS--> CWE-502
--   CVE-2021-44228 --USES_TECHNIQUE--> T1190

SELECT COUNT(*) AS relations_count FROM relations;

SELECT source, relation, target
FROM relations
ORDER BY source, relation, target
LIMIT 30;

SELECT relation, COUNT(*) AS count
FROM relations
GROUP BY relation
ORDER BY count DESC, relation;

-- 关联实体名称后查看三元组，更适合理解数据含义。
SELECT
    s.id AS source_id,
    s.name AS source_name,
    s.type AS source_type,
    r.relation,
    t.id AS target_id,
    t.name AS target_name,
    t.type AS target_type
FROM relations r
JOIN entities s ON r.source = s.id
JOIN entities t ON r.target = t.id
ORDER BY r.source, r.relation, r.target
LIMIT 30;

-- ============================================================
-- 3. doc_chunks：文档片段表
-- ============================================================
-- 作用：
--   保存和实体相关的文本证据。Milvus 向量库中的文本向量就来自这里的 text 字段。
--
-- 字段含义：
--   chunk_id    文档片段唯一 ID。
--   entity_id   文档片段关联的实体 ID，关联 entities.id。
--   entity_type 文档片段关联实体的类型，冗余保存，方便检索展示。
--   source      文本来源，例如 NVD、MITRE CWE、Security Advisory。
--   text        文本片段内容，用于 embedding 和 RAG 证据。
--   score       样例初始分数或来源可信度分数。

SELECT COUNT(*) AS doc_chunks_count FROM doc_chunks;

SELECT chunk_id, entity_id, entity_type, source, score, LEFT(text, 120) AS text_preview
FROM doc_chunks
ORDER BY chunk_id
LIMIT 20;

SELECT source, COUNT(*) AS count
FROM doc_chunks
GROUP BY source
ORDER BY count DESC, source;

-- 查看实体与文本片段的关联。
SELECT
    e.id,
    e.name,
    e.type,
    d.source,
    d.score,
    LEFT(d.text, 120) AS text_preview
FROM doc_chunks d
JOIN entities e ON d.entity_id = e.id
ORDER BY d.chunk_id
LIMIT 20;

-- ============================================================
-- 4. qa_history：问答历史表
-- ============================================================
-- 作用：
--   保存用户每次问答记录和运行指标，用于问答历史页、统计页和后续评估。
--
-- 字段含义：
--   id                  自增主键。
--   question            用户问题。
--   answer              系统回答。
--   mode                问答模式，例如 KG-RAG。
--   confidence          回答置信度。
--   elapsed_ms          问答耗时，单位毫秒。
--   graph_path_count    使用的图谱路径数量。
--   text_evidence_count 使用的文本证据数量。
--   graph_paths         本次问答使用的图谱路径明细，JSON 数组。
--   text_evidence       本次问答使用的文本证据明细，JSON 数组。
--   created_at          创建时间。

SELECT COUNT(*) AS qa_history_count FROM qa_history;

SELECT
    id,
    mode,
    confidence,
    elapsed_ms,
    graph_path_count,
    text_evidence_count,
    graph_paths,
    text_evidence,
    created_at,
    LEFT(question, 80) AS question_preview,
    LEFT(answer, 120) AS answer_preview
FROM qa_history
ORDER BY created_at DESC
LIMIT 20;

-- ============================================================
-- 5. 表之间的关联完整性检查
-- ============================================================
-- 正常情况下，以下三个结果都应该是 0。

SELECT COUNT(*) AS missing_relation_source
FROM relations r
LEFT JOIN entities e ON r.source = e.id
WHERE e.id IS NULL;

SELECT COUNT(*) AS missing_relation_target
FROM relations r
LEFT JOIN entities e ON r.target = e.id
WHERE e.id IS NULL;

SELECT COUNT(*) AS missing_doc_chunk_entity
FROM doc_chunks d
LEFT JOIN entities e ON d.entity_id = e.id
WHERE e.id IS NULL;

-- ============================================================
-- 6. 以 Log4Shell 为例查看 PG 中的数据联动
-- ============================================================

SELECT *
FROM entities
WHERE id = 'CVE-2021-44228' OR name ILIKE '%Log4Shell%';

SELECT
    s.id AS source_id,
    s.name AS source_name,
    r.relation,
    t.id AS target_id,
    t.name AS target_name,
    t.type AS target_type
FROM relations r
JOIN entities s ON r.source = s.id
JOIN entities t ON r.target = t.id
WHERE r.source = 'CVE-2021-44228'
ORDER BY r.relation, r.target;

SELECT chunk_id, source, score, text
FROM doc_chunks
WHERE entity_id = 'CVE-2021-44228'
ORDER BY score DESC;
