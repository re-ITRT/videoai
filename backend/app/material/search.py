"""素材检索服务 — M6/M7

流程：
1. 调 material-search 工作流（query → embeddings[]）
2. 遍历每个 embedding，pgvector <=> 余弦相似度 + 阈值筛选
3. 合并/去重/排序结果
"""
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.material.models import Material, MaterialSlice
from app.workers.workflow import call_workflow


async def search_materials(
    db: AsyncSession,
    user_id: str,
    query: str,
    threshold: float = 0.6,
    max_results: int = 50,
    search_level: str = "material",
) -> list[dict]:
    """
    语义检索：调 material-search 工作流 → pgvector 阈值筛选
    
    返回: [{id, similarity, image_url, text_content, tags}, ...]
    """
    # 1. 调 material-search 工作流获取向量
    workflow_payload = {
        "product_queries": [query],
        "general_queries": [],
    }
    try:
        workflow_result = await call_workflow("material-search", workflow_payload)
        embeddings = workflow_result.get("product_embeddings", [])
    except Exception:
        embeddings = []

    if not embeddings:
        return []

    # 2. 遍历每个 embedding，做 pgvector 查询
    seen_ids = set()
    results = []

    for emb in embeddings:
        vector = emb.get("embedding", [])
        if not vector:
            continue

        vec_str = "[" + ",".join(str(v) for v in vector) + "]"

        if search_level == "slice":
            sql = text("""
                SELECT ms.id, ms.material_id,
                       1 - (ms.embedding <=> :vec) AS similarity,
                       ms.image_url, ms.description AS text_content, ms.tags
                FROM material_slices ms
                WHERE 1 - (ms.embedding <=> :vec) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            params = {"vec": vec_str, "threshold": threshold, "limit": max_results}
        else:
            sql = text("""
                SELECT m.id,
                       1 - (m.embedding <=> :vec) AS similarity,
                       m.image_url, m.text_content, m.tags
                FROM materials m
                WHERE m.user_id = :user_id
                  AND 1 - (m.embedding <=> :vec) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            params = {"vec": vec_str, "threshold": threshold, "limit": max_results, "user_id": user_id}

        try:
            rows = await db.execute(sql, params)
            for row in rows.mappings().all():
                rid = row["id"]
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    results.append(dict(row))
        except Exception:
            pass

    # 3. 按相似度排序
    results.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    return results[:max_results]


async def search_materials_fallback(
    db: AsyncSession,
    user_id: str,
    query: str,
    max_results: int = 50,
) -> list[dict]:
    """
    文本回退搜索 — tags + text_content LIKE
    当 pgvector 不可用时使用
    """
    sql = text("""
        SELECT id, image_url, text_content, tags,
               1.0 AS similarity
        FROM materials
        WHERE user_id = :user_id
          AND (
              CAST(tags AS TEXT) LIKE :q
              OR text_content LIKE :q
          )
        ORDER BY id DESC
        LIMIT :limit
    """)
    q = f"%{query}%"
    rows = await db.execute(sql, {"user_id": user_id, "q": q, "limit": max_results})
    return [dict(row) for row in rows.mappings().all()]
