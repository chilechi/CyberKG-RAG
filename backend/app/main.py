from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.data import router as data_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.mock import router as mock_router
from app.api.overview import router as overview_router
from app.api.placeholders import router as placeholders_router
from app.api.qa import router as qa_router
from app.api.search import router as search_router


app = FastAPI(
    title="CyberKG-RAG API",
    description="基于知识图谱的网络安全知识问答系统后端 API",
    version="0.1.0",
)

# 开发阶段先放开本地跨域，方便 Vue 前端联调；正式部署时再收紧允许来源。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """健康检查接口，用于前后端联调和部署探活。"""
    return {"status": "ok", "service": "cyberkg-rag-backend"}


app.include_router(mock_router, prefix="/api/mock", tags=["mock"])
app.include_router(overview_router, prefix="/api/overview", tags=["overview"])
app.include_router(data_router, prefix="/api/data", tags=["data"])
app.include_router(placeholders_router, prefix="/api", tags=["reserved"])
app.include_router(graph_router, prefix="/api/graph", tags=["graph"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(qa_router, prefix="/api/qa", tags=["qa"])
app.include_router(health_router, prefix="/health", tags=["health"])
