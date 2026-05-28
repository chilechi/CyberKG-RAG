// CyberKG-RAG Neo4j 图谱结构说明与查看 Cypher
// 使用方式：
// 1. 打开 http://localhost:7474
// 2. 登录 Neo4j
// 3. 复制本文件中的 Cypher 分段执行

// ============================================================
// 1. Neo4j 保存什么
// ============================================================
// Neo4j 保存知识图谱结构：
// - PostgreSQL entities 表中的每条实体，在 Neo4j 中是一个节点。
// - PostgreSQL relations 表中的每条三元组，在 Neo4j 中是一条边。
//
// 节点属性：
// - id          实体 ID，例如 CVE-2021-44228、CWE-502、T1190。
// - name        实体名称。
// - type        实体类型。
// - description 实体描述。
//
// 边类型：
// - HAS_WEAKNESS
// - USES_TECHNIQUE
// - HAS_MITIGATION
// - AFFECTS_PRODUCT
// - RELATED_TO_CAPEC
// - BELONGS_TO_TACTIC

// 查看节点数量
MATCH (n)
RETURN count(n) AS node_count;

// 查看关系数量
MATCH ()-[r]->()
RETURN count(r) AS relationship_count;

// 按节点类型统计
MATCH (n)
RETURN n.type AS type, count(n) AS count
ORDER BY count DESC, type;

// 按关系类型统计
MATCH ()-[r]->()
RETURN type(r) AS relation, count(r) AS count
ORDER BY count DESC, relation;

// 查看部分节点
MATCH (n)
RETURN n.id AS id, n.name AS name, n.type AS type, n.description AS description
ORDER BY n.type, n.id
LIMIT 30;

// 查看部分三元组
MATCH (s)-[r]->(t)
RETURN
  s.id AS source_id,
  s.name AS source_name,
  type(r) AS relation,
  t.id AS target_id,
  t.name AS target_name,
  t.type AS target_type
ORDER BY source_id, relation, target_id
LIMIT 30;

// ============================================================
// 2. 以 Log4Shell 为例查看图谱路径
// ============================================================

// 查看 Log4Shell 一跳邻居
MATCH (n {id: "CVE-2021-44228"})-[r]-(m)
RETURN n, r, m;

// 查看 Log4Shell 两跳路径
MATCH p=(n {id: "CVE-2021-44228"})-[*1..2]-(m)
RETURN p
LIMIT 50;

// 查看 Log4Shell 的弱点、技术、缓解措施、影响产品
MATCH (v {id: "CVE-2021-44228"})-[r]->(m)
RETURN type(r) AS relation, m.id AS target_id, m.name AS target_name, m.type AS target_type
ORDER BY relation, target_id;

// ============================================================
// 3. Neo4j 与 PostgreSQL 的关联
// ============================================================
// Neo4j 节点 id 对应 PostgreSQL entities.id。
// Neo4j 关系 (source)-[relation]->(target) 对应 PostgreSQL relations：
// - source = 起点节点 id
// - relation = 边类型
// - target = 终点节点 id
//
// Milvus 向量记录中的 entity_id 也对应 Neo4j 节点 id。
