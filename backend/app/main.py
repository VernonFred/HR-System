import os

# 加载 .env 环境变量（必须在其他导入之前）
# 注意：不覆盖已存在的环境变量，保留SQLite数据库配置
from dotenv import load_dotenv
load_dotenv(override=False)

# 确保使用SQLite（本地开发环境）
if not os.getenv("DATABASE_URL") or "postgres" in os.getenv("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite:///./hr.db"

# AI 统一使用 DeepSeek 单模型；强制覆盖历史 ModelScope / SiliconFlow 配置残留。
os.environ["AI_API_BASE"] = "https://api.deepseek.com"
os.environ["AI_MODEL"] = "deepseek-v4-pro"

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import enforce_authenticated_access, get_or_create_default_user
from app.db import ensure_tables
from app.default_questionnaires import _init_default_questionnaires
from app.api.ai.router import router as ai_router
from app.api.assessments.router import public_router as public_assessments_router
from app.api.assessments.router import router as assessments_router
from app.api.candidates.router import router as candidates_router
from app.api.job_positions.router import router as job_positions_router
from app.api.job_profiles.router import router as job_profiles_router
from app.api.legacy_auth import router as legacy_auth_router
from app.api.legacy_candidates import router as legacy_candidates_router
from app.api.legacy_questionnaires import router as legacy_questionnaires_router
from app.api.resumes.router import router as resumes_router
from app.api.spec_mock import router as spec_mock_router
from app.api.v2 import router as v2_router


app = FastAPI(
    title="HR Backend",
    version="0.1.0",
    dependencies=[Depends(enforce_authenticated_access)],
    # ⭐ 禁用尾部斜杠重定向，避免 307 问题
    redirect_slashes=False,
)

# CORS配置：允许所有来源（开发环境）
# 注意：allow_credentials=True 与 allow_origins=["*"] 不兼容
# 所以设置 allow_credentials=False 或者明确指定origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(ai_router, prefix="/api")
app.include_router(spec_mock_router)
app.include_router(v2_router)
app.include_router(job_positions_router)
app.include_router(job_profiles_router)
app.include_router(candidates_router)
app.include_router(resumes_router)
app.include_router(assessments_router)
app.include_router(public_assessments_router)
app.include_router(legacy_auth_router)
app.include_router(legacy_questionnaires_router)
app.include_router(legacy_candidates_router)


@app.on_event("startup")
def _startup() -> None:
    ensure_tables()
    # 确保默认用户存在（便于联调）
    get_or_create_default_user()
    # 初始化默认问卷数据
    _init_default_questionnaires()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}
