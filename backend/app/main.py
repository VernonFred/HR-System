import json
import os
from typing import Generator, Optional
from uuid import uuid4

# 加载 .env 环境变量（必须在其他导入之前）
# 注意：不覆盖已存在的环境变量，保留SQLite数据库配置
from dotenv import load_dotenv
load_dotenv(override=False)

# 确保使用SQLite（本地开发环境）
if not os.getenv("DATABASE_URL") or "postgres" in os.getenv("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite:///./hr.db"

# 配置AI备用模型（硅基流动免费模型）
if not os.getenv("AI_FALLBACK_MODELS_SIMPLE"):
    os.environ["AI_FALLBACK_MODELS_SIMPLE"] = "THUDM/glm-4-9b-chat,THUDM/GLM-Z1-9B-0414,THUDM/GLM-4-9B-0414"

# ⭐ 配置 ModelScope API（魔塔空间 - 主力画像模型）
if not os.getenv("MODELSCOPE_API_KEY"):
    # 默认 API Key（长期有效）
    os.environ["MODELSCOPE_API_KEY"] = "ms-719ff9c2-52e9-43df-bf51-3226f0acdf78"
    os.environ["MODELSCOPE_API_KEY_EXPIRES"] = "2099-12-31"

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from app.auth import decode_and_validate_token, get_current_user
from app.db import ensure_tables, get_engine, get_session
from app.models import Question, SubmissionAnswer, User
from app.models_assessment import Questionnaire, Submission  # ⭐ 使用models_assessment中的模型
from app.auth import authenticate, get_or_create_default_user, issue_token
from app.scoring import ScoringError, score_submission, validate_answers
from app.config_scoring import QUESTIONNAIRE_SCORING_CONFIG
from app.security import hash_password, verify_password
from app.api.ai.router import router as ai_router
from app.api.job_positions.router import router as job_positions_router
from app.api.job_profiles.router import router as job_profiles_router
from app.api.candidates.router import router as candidates_router
from app.api.resumes.router import router as resumes_router
from app.api.assessments.router import router as assessments_router, public_router as public_assessments_router
from app.api.spec_mock import router as spec_mock_router
from app.api.v2 import router as v2_router
from app.schemas import (
    AnswerItem,
    AnalyticsSummary,
    CandidateOut,
    CandidateListResponse,
    PositionBucket,
    RadarIndicator,
    RadarSeries,
    SubmissionRequest,
    SubmissionResponse,
    SubmissionScore,
    TrendSeries,
)

class LoginRequest(SQLModel):
    username: str
    password: str


class LoginResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class RegisterRequest(SQLModel):
    username: str
    password: str
    role: str = "user"


class RefreshRequest(SQLModel):
    refresh_token: str
# ⚠️ Mock候选人数据 - 与数据库保持一致（3个候选人，对应EPQ/DISC/MBTI）
MOCK_CANDIDATES = [
    CandidateOut(
        id=1,
        name="张三",
        position="产品经理",          # EPQ测评
        phone="138****5678",
        score=85,
        grade="A",
        level="P6",
        status="已完成",
        tags=["外向型", "结构化分析"],
        updated_at="2025-12-02",
        dimensions=[
            SubmissionScore(dimension="E", score=85, grade="A", grade_label="外向性"),
            SubmissionScore(dimension="N", score=45, grade="B", grade_label="神经质"),
            SubmissionScore(dimension="P", score=68, grade="B", grade_label="精神质"),
            SubmissionScore(dimension="L", score=82, grade="A", grade_label="掩饰性"),
        ],
    ),
    CandidateOut(
        id=2,
        name="李四",
        position="实施工程师",        # DISC测评
        phone="139****5678",
        score=75,
        grade="B",
        level="P5",
        status="已完成",
        tags=["谨慎型", "注重细节"],
        updated_at="2025-12-03",
        dimensions=[
            SubmissionScore(dimension="D", score=72, grade="B", grade_label="支配型"),
            SubmissionScore(dimension="I", score=65, grade="B", grade_label="影响型"),
            SubmissionScore(dimension="S", score=78, grade="B", grade_label="稳健型"),
            SubmissionScore(dimension="C", score=85, grade="A", grade_label="谨慎型"),
        ],
    ),
    CandidateOut(
        id=3,
        name="王五",
        position="软件工程师",        # MBTI测评
        phone="137****9999",
        score=80,
        grade="A",
        level="P5",
        status="已完成",
        tags=["INTJ", "系统思维"],
        updated_at="2025-12-04",
    ),
    # ❌ 已删除赵六 - 只保留3个候选人对应EPQ/DISC/MBTI测评
]

MOCK_ANALYTICS = AnalyticsSummary(
    positionDistribution=[
        PositionBucket(name="产品", value=32),
        PositionBucket(name="后端", value=24),
        PositionBucket(name="前端", value=18),
        PositionBucket(name="数据", value=12),
    ],
    matchDistribution=[
        PositionBucket(name=">90", value=8),
        PositionBucket(name="80-90", value=14),
        PositionBucket(name="70-80", value=22),
        PositionBucket(name="<70", value=10),
    ],
    radarIndicators=[
        RadarIndicator(name="外向 E", max=24),
        RadarIndicator(name="神经 N", max=24),
        RadarIndicator(name="精神 P", max=24),
        RadarIndicator(name="掩饰 L", max=24),
    ],
    radarSeries=[
        RadarSeries(name="候选人 A", value=[18, 10, 12, 16]),
        RadarSeries(name="理想模型", value=[20, 12, 14, 18]),
    ],
    personalityPie=[
        PositionBucket(name="外向型", value=40),
        PositionBucket(name="内向型", value=32),
        PositionBucket(name="中性", value=18),
    ],
    dimensionTrendLabels=["近1周", "近1月", "近3月"],
    dimensionTrendSeries=[
        TrendSeries(name="外向 E", data=[16, 18, 19]),
        TrendSeries(name="神经 N", data=[8, 9, 10]),
        TrendSeries(name="精神 P", data=[10, 11, 12]),
        TrendSeries(name="掩饰 L", data=[14, 15, 15]),
    ],
    gradeCutoffs={"A": 18, "B": 12, "C": 8},
    totalCandidates=120,
    avgScore=79.6,
)

app = FastAPI(title="HR Backend", version="0.1.0")

# CORS配置：允许所有来源（开发环境）
# 注意：allow_credentials=True 与 allow_origins=["*"] 不兼容
# 所以设置 allow_credentials=False 或者明确指定origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=False,  # 不使用凭证时可以用 "*"
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
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


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    secret = os.getenv("JWT_SECRET", "change_me")
    # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
    access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
    refresh = issue_token(
        user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
    )
    return LoginResponse(access_token=access, refresh_token=refresh)


@app.post("/auth/register", response_model=LoginResponse, tags=["auth"])
def register(payload: RegisterRequest) -> LoginResponse:
    engine = get_engine()
    with Session(engine) as session:
        exists = session.exec(select(User).where(User.username == payload.username)).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
        session.add(user)
        session.commit()
        session.refresh(user)
        secret = os.getenv("JWT_SECRET", "change_me")
        # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
        access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
        refresh = issue_token(
            user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
        )
        return LoginResponse(access_token=access, refresh_token=refresh)


@app.post("/auth/refresh", response_model=LoginResponse, tags=["auth"])
def refresh(payload: RefreshRequest) -> LoginResponse:
    secret = os.getenv("JWT_SECRET", "change_me")
    data = decode_and_validate_token(payload.refresh_token, secret=secret, expected_type="refresh")
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == data.get("sub"))).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
        access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
        refresh_token = issue_token(
            user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
        )
        return LoginResponse(access_token=access, refresh_token=refresh_token)


class ChangePasswordRequest(SQLModel):
    current_password: str
    new_password: str


class UpdateUsernameRequest(BaseModel):
    new_username: str


@app.post("/api/auth/update-username", tags=["auth"])
def update_username(
    payload: UpdateUsernameRequest,
    user_id: int = Depends(get_current_user),
):
    """修改用户名（显示名称）"""
    new_username = payload.new_username.strip()
    if not new_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空")
    if len(new_username) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名长度不能超过50个字符")
    
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # 更新用户名
        user.username = new_username
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {"message": "用户名修改成功", "username": user.username}


@app.post("/auth/change-password", tags=["auth"])
def change_password(
    payload: ChangePasswordRequest,
    user_id: int = Depends(get_current_user),
):
    """修改用户密码"""
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # 验证当前密码
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
        
        # 更新密码
        user.password_hash = hash_password(payload.new_password)
        session.add(user)
        session.commit()
        
        return {"message": "密码修改成功"}


# ---- Token 更新 API ----
class UpdateTokenRequest(BaseModel):
    token: str
    expires: str | None = None  # 可选：用户指定过期时间（格式：YYYY-MM-DD）


@app.post("/api/settings/update-token", tags=["settings"])
def update_api_token(
    payload: UpdateTokenRequest,
    user_id: int = Depends(get_current_user),
):
    """更新 ModelScope API Token.
    
    将新的 Token 保存到环境变量和 .env 文件中。
    支持用户手动指定过期时间，如果不指定则默认30天。
    """
    new_token = payload.token.strip()
    if not new_token:
        raise HTTPException(status_code=400, detail="Token 不能为空")
    
    # 验证 Token 格式（简单检查）
    if not new_token.startswith("ms-") and len(new_token) < 20:
        raise HTTPException(status_code=400, detail="Token 格式不正确")
    
    try:
        # 1. 更新当前进程的环境变量
        os.environ["MODELSCOPE_API_KEY"] = new_token
        
        # 2. 设置过期时间：优先使用用户指定的，否则默认30天
        from datetime import datetime, timedelta
        if payload.expires and payload.expires.strip():
            # 验证日期格式
            try:
                datetime.strptime(payload.expires.strip(), "%Y-%m-%d")
                expires_date = payload.expires.strip()
            except ValueError:
                raise HTTPException(status_code=400, detail="过期时间格式不正确，请使用 YYYY-MM-DD 格式")
        else:
            # 默认30天
            expires_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        os.environ["MODELSCOPE_API_KEY_EXPIRES"] = expires_date
        
        # 3. 尝试更新 .env 文件（如果存在）
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        
        if os.path.exists(env_path):
            # 读取现有内容
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 更新或添加 Token 配置
            key_found = False
            expires_found = False
            new_lines = []
            
            for line in lines:
                if line.startswith("MODELSCOPE_API_KEY="):
                    new_lines.append(f"MODELSCOPE_API_KEY={new_token}\n")
                    key_found = True
                elif line.startswith("MODELSCOPE_API_KEY_EXPIRES="):
                    new_lines.append(f"MODELSCOPE_API_KEY_EXPIRES={expires_date}\n")
                    expires_found = True
                else:
                    new_lines.append(line)
            
            # 如果没找到，添加到末尾
            if not key_found:
                new_lines.append(f"\nMODELSCOPE_API_KEY={new_token}\n")
            if not expires_found:
                new_lines.append(f"MODELSCOPE_API_KEY_EXPIRES={expires_date}\n")
            
            # 写回文件
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        else:
            # 创建新的 .env 文件
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f"# ModelScope API 配置\n")
                f.write(f"MODELSCOPE_API_KEY={new_token}\n")
                f.write(f"MODELSCOPE_API_KEY_EXPIRES={expires_date}\n")
        
        return {
            "message": "Token 更新成功",
            "expires": expires_date
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token 更新失败: {str(e)}")


@app.get("/questionnaires", response_model=list[Questionnaire], tags=["questionnaires"])
def list_questionnaires(session: Session = Depends(get_session)) -> list[Questionnaire]:
    """List all questionnaires."""
    result = session.exec(select(Questionnaire).order_by(Questionnaire.id)).all()
    return result


@app.get(
    "/questionnaires/{code}",
    response_model=Questionnaire,
    tags=["questionnaires"],
)
def get_questionnaire(code: str, session: Session = Depends(get_session)) -> Questionnaire:
    """Get questionnaire by code."""
    q = session.exec(select(Questionnaire).where(Questionnaire.code == code)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return q


@app.get(
    "/questionnaires/{code}/questions",
    response_model=list[Question],
    tags=["questionnaires"],
)
def list_questions(code: str, session: Session = Depends(get_session)) -> list[Question]:
    """List questions of a questionnaire by code."""
    q = session.exec(select(Questionnaire).where(Questionnaire.code == code)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    rows = session.exec(
        select(Question).where(Question.questionnaire_id == q.id).order_by(Question.order)
    ).all()
    return rows


@app.post(
    "/submissions",
    response_model=SubmissionResponse,
    tags=["submissions"],
)
def submit_answers(
    payload: SubmissionRequest,
    user_id: int = Depends(get_current_user),
) -> SubmissionResponse:
    """提交并评分（当前简化算法，含必答校验；鉴权占位）."""
    engine = get_engine()
    with Session(engine) as session:
        qn = session.exec(
            select(Questionnaire).where(Questionnaire.code == payload.questionnaireCode)
        ).first()
        if not qn:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        # 鉴权占位：若需用户/候选人信息，可在此检查 payload.userId / candidateId
        # 如需强制登录，可在 get_current_user 中抛 401 或在此加判断 user_id/payload.userId
        _validate_weights(payload.weights)

        # 将答案转为 map，方便查找，并校验必答
        parsed_answers = []
        for a in payload.answers:
            try:
                parsed_answers.append(AnswerItem(questionId=int(a.get("questionId")), value=a.get("value")))
            except Exception:
                continue
        answers_map = {a.questionId: a.value for a in parsed_answers}
        q_rows = session.exec(
            select(Question).where(Question.questionnaire_id == qn.id)
        ).all()

        try:
            # 必答校验
            validate_answers(q_rows, {k: AnswerItem(questionId=k, value=v) for k, v in answers_map.items()})
            scoring_cfg = payload.scoring or QUESTIONNAIRE_SCORING_CONFIG.get(payload.questionnaireCode)
            scores, total = score_submission(
                q_rows,
                {k: AnswerItem(questionId=k, value=v) for k, v in answers_map.items()},
                weights=payload.weights,
                scoring_config=scoring_cfg,
            )
        except ScoringError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            )
        # 保存答案（仅保存已答题部分）
        answer_rows: list[SubmissionAnswer] = []
        for q in q_rows:
            if q.id not in answers_map:
                continue
            ans_val = answers_map[q.id]
            sc = next((s.score for s in scores if s.dimension == q.dimension), 0.0) if q.dimension else 0.0
            answer_rows.append(
                SubmissionAnswer(question_id=q.id, value=str(ans_val), score=sc)
            )

        submission_code = f"sub-{uuid4().hex[:8]}"
        submission = Submission(
            submission_code=submission_code,
            questionnaire_id=qn.id,
            total_score=total,
            summary="简化评分：基于答案匹配得分。",
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        # 回写 submission_id 到答案并批量保存
        for a in answer_rows:
            a.submission_id = submission.id
        session.add_all(answer_rows)
        session.commit()

        return SubmissionResponse(
            submissionId=submission_code,
            questionnaireCode=payload.questionnaireCode,
            scores=scores,
            totalScore=total,
            summary=submission.summary,
        )


def _score_question(q: Question, value: object, weights: Optional[dict] = None) -> float:
    """简化评分：yes/no 匹配正向得1分，choice 选 A 得1分，否则0；支持维度加权。"""
    base = 0.0
    v = str(value).lower()
    if q.answer_type == "yesno":
        if q.positive:
            base = 1.0 if v in {"yes", "true", "1"} else 0.0
        else:
            base = 1.0 if v in {"no", "false", "0"} else 0.0
    else:
        payload = q.payload or {}
        base = 1.0 if v == str(payload.get("optionA", "")).lower() else 0.0

    if weights and q.dimension:
        weight = float(weights.get(q.dimension, 1.0))
        return base * weight
    return base


def _validate_weights(weights: Optional[dict]) -> None:
    if not weights:
        return
    for k, v in weights.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid weight for dimension {k}",
            )
        if fv < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weight for dimension {k} must be non-negative",
            )


# ---- Candidates / Analytics (从数据库获取) ----
# ⭐ V46: 重写候选人列表接口，从 submissions 表聚合数据，解决人员画像和人员管理人数不统一问题
@app.get("/api/candidates", response_model=CandidateListResponse, tags=["candidates"])
def list_candidates(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
) -> CandidateListResponse:
    """从数据库获取候选人列表.
    
    V47更新：同时从 candidates 表和 submissions 表聚合数据，确保：
    1. 有候选人记录的人一定显示
    2. 有提交记录但无候选人记录的人也显示
    """
    from sqlmodel import select, or_, func
    from sqlalchemy import and_, distinct
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire
    
    candidate_map: dict[tuple[str, str], dict] = {}
    
    # ⭐ 步骤1：先从 candidates 表获取所有候选人
    all_candidates = session.exec(select(Candidate)).all()
    for c in all_candidates:
        key = (c.phone or '', c.name)
        candidate_map[key] = {
            'name': c.name,
            'phone': c.phone or '',
            'email': c.email,
            'gender': c.gender,
            'position': c.position,
            'submissions': [],
            'submission_types': set(),
            'latest_submitted_at': c.updated_at,
            'candidate_id': c.id,
            'has_resume': bool(c.resume_file_path),
            'status': c.status or 'new',
            'updated_at': c.updated_at,
        }
    
    # ⭐ 步骤2：从 submissions 表获取所有已完成的提交记录
    all_submissions = session.exec(
        select(Submission)
        .where(Submission.status == 'completed')
        .order_by(Submission.submitted_at.desc())
    ).all()
    
    # 按 (phone, name) 分组聚合
    for sub in all_submissions:
        key = (sub.candidate_phone, sub.candidate_name)
        
        if key not in candidate_map:
            # 新建记录（有提交但无候选人记录）
            candidate_map[key] = {
                'name': sub.candidate_name,
                'phone': sub.candidate_phone,
                'email': sub.candidate_email,
                'gender': sub.gender,
                'position': sub.target_position,
                'submissions': [],
                'submission_types': set(),
                'latest_submitted_at': sub.submitted_at,
                'candidate_id': sub.candidate_id,
                'has_resume': False,
                'status': 'new',
                'updated_at': sub.submitted_at,
            }
        
        candidate_map[key]['submissions'].append(sub)
    
        # 获取问卷类型
        questionnaire = session.get(Questionnaire, sub.questionnaire_id)
        if questionnaire:
            if questionnaire.category == 'professional':
                candidate_map[key]['submission_types'].add('professional')
            else:
                candidate_map[key]['submission_types'].add('survey')
        
        # 更新最新提交时间
        if sub.submitted_at and (not candidate_map[key]['latest_submitted_at'] or 
                                  sub.submitted_at > candidate_map[key]['latest_submitted_at']):
            candidate_map[key]['latest_submitted_at'] = sub.submitted_at
            candidate_map[key]['updated_at'] = sub.submitted_at
        
        # 更新性别和岗位（取第一个有效的）
        if not candidate_map[key]['gender'] and sub.gender:
            candidate_map[key]['gender'] = sub.gender
        if not candidate_map[key]['position'] and sub.target_position:
            candidate_map[key]['position'] = sub.target_position
    
    # ⭐ 步骤3：转换为列表并应用过滤
    candidates_list = list(candidate_map.values())
    
    # 关键词过滤
    if keyword:
        keyword_lower = keyword.lower()
        candidates_list = [
            c for c in candidates_list
            if (keyword_lower in (c['name'] or '').lower() or
                keyword_lower in (c['phone'] or '') or
                keyword_lower in (c['position'] or '').lower())
        ]
    
    # 岗位过滤
    if position:
        candidates_list = [
            c for c in candidates_list
            if position.lower() in (c['position'] or '').lower()
        ]
    
    # 状态过滤
    if status:
        candidates_list = [
            c for c in candidates_list
            if c['status'] == status
        ]
    
    # 按最新提交时间排序
    candidates_list.sort(key=lambda x: x['latest_submitted_at'] or datetime.min, reverse=True)
    
    # 获取总数
    total = len(candidates_list)
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paged_candidates = candidates_list[start:end]
    
    # ⭐ 步骤4：转换为 CandidateOut 格式
    items = []
    for idx, c in enumerate(paged_candidates):
        # 生成一个虚拟ID（如果没有 candidate_id）
        candidate_id = c['candidate_id'] or (10000 + start + idx)
        
        items.append(CandidateOut(
            id=candidate_id,
            name=c['name'],
            position=c['position'] or "未知岗位",
            phone=c['phone'] or "",
            score=80,  # 默认分数
            status=c['status'] or "待处理",
            grade="A",
            level="P5",
            tags=[],
            updated_at=c['updated_at'].strftime("%Y-%m-%d") if c['updated_at'] else "",
            submission_types=list(c['submission_types']),
            gender=c['gender']
        ))
    
    return CandidateListResponse(items=items, page=page, pageSize=page_size, total=total)


@app.get("/api/candidates/{candidate_id}", response_model=CandidateOut, tags=["candidates"])
def get_candidate(
    candidate_id: int,
    session: Session = Depends(get_session)
) -> CandidateOut:
    """从数据库获取候选人详情."""
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire
    
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # ⭐ 获取提交类型
    def get_submission_types() -> list[str]:
        types = set()
        
        # 通过candidate_id查询提交记录
        sub_stmt = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions = session.exec(sub_stmt).all()
        
        # 如果没有通过candidate_id找到，尝试通过手机号+姓名匹配
        if not submissions and candidate.phone and candidate.name:
            from sqlalchemy import and_
            sub_stmt = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone
                )
            )
            submissions = session.exec(sub_stmt).all()
        
        for sub in submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            if questionnaire:
                if questionnaire.category == 'professional':
                    types.add('professional')
                else:
                    types.add('survey')
        
        return list(types)
    
    return CandidateOut(
        id=candidate.id,
        name=candidate.name,
        position=getattr(candidate, 'position', None) or "未知岗位",
        phone=candidate.phone or "",
        score=80,
        status=candidate.status or "待处理",
        grade="A",
        level="P5",
        tags=[],
        updated_at=candidate.updated_at.strftime("%Y-%m-%d") if candidate.updated_at else "",
        submission_types=get_submission_types(),  # ⭐ 添加提交类型
        gender=getattr(candidate, 'gender', None)  # V45: 添加性别
    )


@app.delete("/api/candidates/{candidate_id}", tags=["candidates"])
def delete_candidate(
    candidate_id: int,
    session: Session = Depends(get_session)
) -> dict:
    """删除候选人及其相关数据."""
    from app.models import Candidate
    from sqlalchemy import text
    
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    try:
        # 使用原始SQL删除，按正确顺序处理外键约束
        conn = session.connection()
        
        # 1. 删除人员画像缓存
        conn.execute(text("DELETE FROM portrait_cache WHERE candidate_id = :cid"), {"cid": candidate_id})
        
        # 2. 删除岗位匹配记录（如果有的话）
        try:
            conn.execute(text("DELETE FROM profile_matches WHERE submission_id IN (SELECT id FROM submissions WHERE candidate_id = :cid)"), {"cid": candidate_id})
        except Exception:
            pass
        
        # 3. 清除候选人的 submission_id 引用
        conn.execute(text("UPDATE candidates SET submission_id = NULL WHERE id = :cid"), {"cid": candidate_id})
        
        # 4. 删除提交记录 (submissions 表)
        conn.execute(text("DELETE FROM submissions WHERE candidate_id = :cid"), {"cid": candidate_id})
    
        # 5. 删除候选人
        conn.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
        
        session.commit()
        
        return {"message": "删除成功", "id": candidate_id}
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.delete("/api/persons/by-phone/{phone}", tags=["candidates"])
def delete_person_by_phone(
    phone: str,
    session: Session = Depends(get_session)
) -> dict:
    """通过手机号删除人员及其相关数据."""
    from sqlalchemy import text
    
    try:
        conn = session.connection()
        
        # 1. 删除提交记录
        result = conn.execute(text("DELETE FROM submissions WHERE candidate_phone = :phone"), {"phone": phone})
        deleted_submissions = result.rowcount
        
        # 2. 删除候选人记录
        result = conn.execute(text("DELETE FROM candidates WHERE phone = :phone"), {"phone": phone})
        deleted_candidates = result.rowcount
        
        # 3. 删除画像缓存（通过候选人ID关联）
        conn.execute(text("""
            DELETE FROM portrait_cache 
            WHERE candidate_id IN (SELECT id FROM candidates WHERE phone = :phone)
        """), {"phone": phone})
        
        session.commit()
        
        return {
            "message": "删除成功", 
            "phone": phone,
            "deleted_submissions": deleted_submissions,
            "deleted_candidates": deleted_candidates
        }
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.delete("/api/persons/by-name/{name}", tags=["candidates"])
def delete_person_by_name(
    name: str,
    session: Session = Depends(get_session)
) -> dict:
    """通过姓名删除人员及其相关数据."""
    from sqlalchemy import text
    
    try:
        conn = session.connection()
        
        # 1. 删除提交记录
        result = conn.execute(text("DELETE FROM submissions WHERE candidate_name = :name"), {"name": name})
        deleted_submissions = result.rowcount
        
        # 2. 删除候选人记录
        result = conn.execute(text("DELETE FROM candidates WHERE name = :name"), {"name": name})
        deleted_candidates = result.rowcount
        
        # 3. 删除画像缓存
        conn.execute(text("""
            DELETE FROM portrait_cache 
            WHERE candidate_id IN (SELECT id FROM candidates WHERE name = :name)
        """), {"name": name})
        
        session.commit()
        
        return {
            "message": "删除成功", 
            "name": name,
            "deleted_submissions": deleted_submissions,
            "deleted_candidates": deleted_candidates
        }
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.delete("/api/admin/clear-all-data", tags=["admin"])
def clear_all_data(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> dict:
    """
    清除所有人员数据（仅管理员可用）。
    包括：候选人、提交记录、问卷答案等。
    不会删除：问卷模板、用户账号、岗位配置。
    """
    from app.models import Candidate, SubmissionAnswer
    from app.models_assessment import Submission
    from sqlalchemy import delete
    
    # 验证是否为管理员
    user = session.get(User, user_id)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    
    deleted_counts = {}
    
    # 1. 删除问卷答案
    try:
        result = session.exec(delete(SubmissionAnswer))
        deleted_counts["submission_answers"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["submission_answers"] = 0
    
    # 2. 删除提交记录
    try:
        result = session.exec(delete(Submission))
        deleted_counts["submissions"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["submissions"] = 0
    
    # 3. 删除候选人
    try:
        result = session.exec(delete(Candidate))
        deleted_counts["candidates"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["candidates"] = 0
    
    session.commit()
    
    return {
        "message": "所有人员数据已清除",
        "deleted": deleted_counts
    }


@app.get("/api/candidates/{candidate_id}/profile", tags=["candidates"])
def get_candidate_profile(candidate_id: int) -> dict:
    """
    获取候选人综合画像数据。
    整合简历数据、测评数据等多数据源。
    通过手机号+姓名双重校验关联数据。
    """
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire
    
    engine = get_engine()
    with Session(engine) as session:
        # 获取候选人基础数据
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="候选人不存在")
        
        # 查找该候选人的所有测评提交记录（通过candidate_id或手机号+姓名）
        submissions = []
        
        # 方式1: 通过candidate_id直接关联
        statement = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions.extend(list(session.exec(statement).all()))
        
        # 方式2: 通过手机号+姓名匹配（兼容未关联的旧数据）
        if candidate.phone and candidate.name:
            from sqlalchemy import and_
            statement = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone,
                    Submission.candidate_id == None  # 只查未关联的
                )
            )
            additional = list(session.exec(statement).all())
            submissions.extend(additional)
            
            # 自动关联这些记录
            for sub in additional:
                sub.candidate_id = candidate_id
                session.add(sub)
            if additional:
                session.commit()
        
        # 去重
        seen_ids = set()
        unique_submissions = []
        for sub in submissions:
            if sub.id not in seen_ids:
                seen_ids.add(sub.id)
                unique_submissions.append(sub)
        
        # 获取测评详情
        assessment_results = []
        for sub in unique_submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            assessment_results.append({
                "id": sub.id,
                "code": sub.code,
                "questionnaire_name": questionnaire.name if questionnaire else "未知问卷",
                "questionnaire_type": questionnaire.type if questionnaire else "CUSTOM",
                "total_score": sub.total_score,
                "grade": sub.grade,
                "scores": sub.scores,
                "status": sub.status,
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            })
        
        # 构建综合画像数据
        profile = {
            "id": candidate.id,
            "name": candidate.name,
            "phone": candidate.phone,
            "email": candidate.email,
            # 简历数据
            "has_resume": bool(candidate.resume_file_path),
            "resume_parsed_data": candidate.resume_parsed_data,
            # 测评数据
            "assessments": assessment_results,
            "assessment_count": len(assessment_results),
            "completed_count": len([a for a in assessment_results if a["status"] == "completed"]),
            # 最新测评结果（如果有）
            "latest_assessment": assessment_results[0] if assessment_results else None,
            # 状态
            "status": candidate.status,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
        }
        
        return profile


def _get_scale_label(score: int, scale_min: int, scale_max: int, min_label: str, max_label: str) -> str:
    """
    V46: 智能生成量表题的描述文本
    
    支持多种常见量表类型：
    1. 满意度量表：非常不满意 -> 非常满意
    2. 同意度量表：非常不同意 -> 非常同意
    3. 频率量表：从不 -> 总是
    4. 程度量表：完全不符合 -> 完全符合
    5. 评分量表：1-5分, 1-10分等
    """
    total_levels = scale_max - scale_min + 1
    position = score - scale_min  # 0-based position
    
    # 预定义的量表描述模板
    SCALE_TEMPLATES = {
        # 满意度类型
        ('满意', 5): ['非常不满意', '不太满意', '一般', '比较满意', '非常满意'],
        ('满意', 4): ['不满意', '一般', '满意', '非常满意'],
        ('满意', 3): ['不满意', '一般', '满意'],
        # 同意度类型
        ('同意', 5): ['非常不同意', '不同意', '一般', '同意', '非常同意'],
        ('同意', 4): ['不同意', '一般', '同意', '非常同意'],
        # 频率类型
        ('频率', 5): ['从不', '很少', '有时', '经常', '总是'],
        ('频率', 4): ['从不', '偶尔', '经常', '总是'],
        # 符合度类型
        ('符合', 5): ['完全不符合', '不太符合', '一般', '比较符合', '完全符合'],
        # 重要性类型
        ('重要', 5): ['非常不重要', '不太重要', '一般', '比较重要', '非常重要'],
        # 可能性类型
        ('可能', 5): ['非常不可能', '不太可能', '一般', '比较可能', '非常可能'],
    }
    
    # 根据 min_label 和 max_label 识别量表类型
    labels = None
    
    # 尝试匹配预定义模板
    for (keyword, levels), template in SCALE_TEMPLATES.items():
        if levels == total_levels:
            if keyword in min_label or keyword in max_label:
                labels = template
                break
    
    # 如果没有匹配到模板，尝试智能生成
    if not labels:
        if min_label and max_label:
            # 有明确的端点标签，生成中间描述
            if total_levels == 5:
                labels = [min_label, f'偏向{min_label[:2]}', '一般/中立', f'偏向{max_label[:2]}', max_label]
            elif total_levels == 4:
                labels = [min_label, f'偏{min_label[:2]}', f'偏{max_label[:2]}', max_label]
            elif total_levels == 3:
                labels = [min_label, '一般/中立', max_label]
            elif total_levels == 7:
                labels = [min_label, f'比较{min_label[:2]}', f'稍微{min_label[:2]}', '中立', 
                         f'稍微{max_label[:2]}', f'比较{max_label[:2]}', max_label]
            elif total_levels == 10:
                # 10分制：1-2差，3-4较差，5-6一般，7-8良好，9-10优秀
                score_labels = ['很差', '较差', '较差', '一般', '一般', '一般', '良好', '良好', '优秀', '优秀']
                if 0 <= position < len(score_labels):
                    return f"{score}分 ({score_labels[position]})"
                return f"{score}分"
            else:
                # 其他情况：只显示端点和分数
                if score == scale_min:
                    return f"{score}分 ({min_label})"
                elif score == scale_max:
                    return f"{score}分 ({max_label})"
                else:
                    return f"{score}分"
        else:
            # 没有标签，使用通用描述
            if total_levels == 5:
                labels = ['很低', '较低', '一般', '较高', '很高']
            elif total_levels == 10:
                score_labels = ['很差', '较差', '较差', '一般', '一般', '一般', '良好', '良好', '优秀', '优秀']
                if 0 <= position < len(score_labels):
                    return f"{score}分 ({score_labels[position]})"
                return f"{score}分"
            else:
                return f"{score}分"
    
    # 返回对应位置的标签
    if labels and 0 <= position < len(labels):
        return f"{score}分 ({labels[position]})"
    
    return f"{score}分"


@app.get("/api/candidates/{candidate_id}/survey-submissions", tags=["candidates"])
def get_candidate_survey_submissions(candidate_id: int) -> dict:
    """
    获取候选人的问卷调查提交记录（非专业测评）。
    包含完整的问题和答案详情。
    """
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire
    
    engine = get_engine()
    with Session(engine) as session:
        # 获取候选人基础数据
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="候选人不存在")
        
        # 查找该候选人的所有提交记录
        submissions = []
        
        # 方式1: 通过candidate_id直接关联
        statement = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions.extend(list(session.exec(statement).all()))
        
        # 方式2: 通过手机号+姓名匹配
        if candidate.phone and candidate.name:
            from sqlalchemy import and_
            statement = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone,
                    Submission.candidate_id == None
                )
            )
            additional = list(session.exec(statement).all())
            submissions.extend(additional)
        
        # 去重
        seen_ids = set()
        unique_submissions = []
        for sub in submissions:
            if sub.id not in seen_ids:
                seen_ids.add(sub.id)
                unique_submissions.append(sub)
        
        # 过滤出问卷调查类型的提交（非professional）
        survey_submissions = []
        for sub in unique_submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            if questionnaire and questionnaire.category != 'professional':
                # 获取问卷题目
                questions_data = questionnaire.questions_data.get('questions', [])
                
                # 构建答案详情
                answers_detail = []
                for q_idx, q in enumerate(questions_data):
                    q_id = str(q.get('id', ''))
                    answer_value = sub.answers.get(q_id) if sub.answers else None
                    
                    # 获取选项文本
                    answer_text = None
                    options = q.get('options', [])
                    q_type = q.get('type', 'single')
                    scale_config = q.get('scale', {})
                    
                    if answer_value is not None:
                        answer_str = str(answer_value)
                        
                        # V46: 处理量表题（scale类型）- 支持多种量表类型
                        if q_type in ('scale', 'rating') and scale_config:
                            try:
                                score_val = int(answer_value)
                                scale_min = scale_config.get('min', 1)
                                scale_max = scale_config.get('max', 5)
                                min_label = scale_config.get('minLabel', '')
                                max_label = scale_config.get('maxLabel', '')
                                
                                # 智能识别量表类型并生成对应描述
                                answer_text = _get_scale_label(score_val, scale_min, scale_max, min_label, max_label)
                            except (ValueError, TypeError):
                                answer_text = str(answer_value)
                        
                        # 处理有选项的题目
                        elif options:
                            # 遍历选项尝试匹配
                            for opt_idx, opt in enumerate(options):
                                if isinstance(opt, dict):
                                    opt_id = str(opt.get('id', ''))
                                    opt_value = str(opt.get('value', ''))
                                    opt_score = str(opt.get('score', ''))
                                    opt_text = opt.get('text', opt.get('label', ''))
                                    
                                    # 多种匹配方式
                                    if (answer_str == opt_id or 
                                        answer_str == opt_value or 
                                        answer_str == str(opt_idx) or
                                        answer_str == opt_score or
                                        answer_str == opt_text):
                                        answer_text = opt_text
                                        break
                                else:
                                    # 选项是简单字符串
                                    if answer_str == str(opt) or answer_str == str(opt_idx):
                                        answer_text = str(opt)
                                        break
                            
                            # 如果还没匹配到，尝试用数字索引匹配
                            if answer_text is None:
                                try:
                                    idx = int(answer_value)
                                    if 0 <= idx < len(options):
                                        opt = options[idx]
                                        if isinstance(opt, dict):
                                            answer_text = opt.get('text', opt.get('label', str(answer_value)))
                                        else:
                                            answer_text = str(opt)
                                except (ValueError, TypeError):
                                    pass
                        
                        # 最后fallback到原始值
                        if answer_text is None:
                            answer_text = str(answer_value)
                    
                    answers_detail.append({
                        'question_id': q_id,
                        'question_text': q.get('text', q.get('title', '')),
                        'question_type': q.get('type', 'single'),
                        'answer_value': answer_value,
                        'answer_text': answer_text,
                        'score': q.get('score', 0) if questionnaire.category == 'scored' else None
                    })
                
                survey_submissions.append({
                    'id': sub.id,
                    'code': sub.code,
                    'questionnaire_id': questionnaire.id,
                    'questionnaire_name': questionnaire.name,
                    'questionnaire_type': questionnaire.type,
                    'questionnaire_category': questionnaire.category,
                    'total_score': sub.total_score,
                    'max_score': sub.max_score,
                    'score_percentage': sub.score_percentage,
                    'grade': sub.grade,
                    'status': sub.status,
                    'started_at': sub.started_at.isoformat() if sub.started_at else None,
                    'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                    'answers': sub.answers,
                    'answers_detail': answers_detail,
                    'custom_data': sub.custom_data,
                })
        
        return {
            'candidate_id': candidate_id,
            'candidate_name': candidate.name,
            'candidate_phone': candidate.phone,
            'candidate_position': candidate.position,
            'candidate_gender': getattr(candidate, 'gender', None),
            'candidate_email': getattr(candidate, 'email', None),
            'submissions': survey_submissions,
            'total': len(survey_submissions)
        }


@app.get("/analytics/summary", response_model=AnalyticsSummary, tags=["analytics"])
def get_analytics_summary() -> AnalyticsSummary:
    """Mock analytics data for charts."""
    return MOCK_ANALYTICS


def _load_questionnaires_from_js():
    """从 questionnaires.js 加载真实题目数据."""
    import subprocess
    from pathlib import Path
    
    try:
        # __file__ 是 backend/app/main.py
        # parent 是 backend/app/
        # parent.parent 是 backend/
        # parent.parent.parent 是项目根目录
        backend_dir = Path(__file__).parent.parent  # backend/
        project_root = backend_dir.parent  # 项目根目录
        export_script = backend_dir / "scripts" / "export_questionnaires.js"
        
        if not export_script.exists():
            print(f"⚠️ 脚本不存在: {export_script}")
            return None
        
        result = subprocess.run(
            ["node", str(export_script), "--compact"],
            capture_output=True,
            text=True,
            cwd=project_root,  # 在项目根目录执行
            check=False
        )
        
        if result.returncode != 0:
            print(f"⚠️ 无法加载questionnaires.js: {result.stderr}")
            return None
        
        return json.loads(result.stdout)
    except Exception as e:
        print(f"⚠️ 加载questionnaires.js失败: {e}")
        return None


def _convert_js_questions_to_format(js_questions, answer_type):
    """转换JS格式的题目为数据库格式."""
    converted = []
    for q in js_questions:
        if answer_type == 'yesno':
            # EPQ: yes/no 格式
            converted.append({
                "id": q["id"],
                "text": q["text"],
                "options": [
                    {"label": "A", "text": "是", "score": 1 if q.get("positive") else 0},
                    {"label": "B", "text": "否", "score": 0 if q.get("positive") else 1}
                ],
                "dimension": q["dimension"]
            })
        elif answer_type == 'choice':
            # MBTI: 二选一格式
            converted.append({
                "id": q["id"],
                "text": q["text"],
                "options": [
                    {"label": "A", "text": q["optionA"], "score": 1},
                    {"label": "B", "text": q["optionB"], "score": 1}
                ],
                "dimension": q["dimension"]
            })
        elif answer_type == 'ranking':
            # DISC: 排序/多选一格式（每个选项对应不同维度）
            converted.append({
                "id": q["id"],
                "text": q["text"],
                "options": q.get("options", []),  # 直接使用原始options
                "dimension": "DISC"  # DISC题目使用统一标识
            })
        elif answer_type == 'likert':
            # 其他李克特量表格式
            converted.append({
                "id": q["id"],
                "text": q["text"],
                "options": [
                    {"label": "A", "text": "非常同意", "score": 5},
                    {"label": "B", "text": "同意", "score": 4},
                    {"label": "C", "text": "中立", "score": 3},
                    {"label": "D", "text": "不同意", "score": 2},
                    {"label": "E", "text": "非常不同意", "score": 1}
                ],
                "dimension": q.get("dimension", "")
            })
    return converted


def _init_default_questionnaires() -> None:
    """初始化默认问卷数据（从questionnaires.js加载真实题目）."""
    from app.models_assessment import Questionnaire
    
    engine = get_engine()
    with Session(engine) as session:
        # 检查是否已有问卷
        statement = select(Questionnaire)
        existing = session.exec(statement).first()
        
        if existing:
            print("✅ 问卷数据已存在，跳过初始化")
            return
        
        print("📝 开始初始化问卷数据...")
        
        # ⭐ 尝试从questionnaires.js加载真实题目
        js_data = _load_questionnaires_from_js()
        
        if js_data:
            print("   ✓ 从questionnaires.js加载题目")
            
            # EPQ问卷
            if 'epq' in js_data:
                epq_data = js_data['epq']
                epq_questions = _convert_js_questions_to_format(
                    epq_data['questions'], 
                    epq_data['answerType']
                )
                epq = Questionnaire(
                    name="EPQ人格测评",
                    type="EPQ",
                    questions_count=len(epq_questions),
                    estimated_minutes=epq_data.get('estimatedTime', 15),
                    questions_data={"questions": epq_questions},
                    scoring_rules={
                        "dimensions": {
                            "E": {"name": "外向性", "max_score": 24},
                            "N": {"name": "神经质", "max_score": 24},
                            "P": {"name": "精神质", "max_score": 24},
                            "L": {"name": "掩饰性", "max_score": 24},
                        }
                    },
                    description="艾森克人格问卷，评估外向性、神经质、精神质和掩饰性四个维度",
                    status="active",
                )
                session.add(epq)
                print(f"   ✓ EPQ: {len(epq_questions)}题")
            
            # DISC问卷
            if 'disc' in js_data:
                disc_data = js_data['disc']
                disc_questions = _convert_js_questions_to_format(
                    disc_data['questions'],
                    disc_data['answerType']
                )
                disc = Questionnaire(
                    name="DISC性格分析",
                    type="DISC",
                    questions_count=len(disc_questions),
                    estimated_minutes=disc_data.get('estimatedTime', 10),
                    questions_data={"questions": disc_questions},
                    scoring_rules={
                        "dimensions": {
                            "D": {"name": "支配型", "max_score": 28},
                            "I": {"name": "影响型", "max_score": 28},
                            "S": {"name": "稳健型", "max_score": 28},
                            "C": {"name": "谨慎型", "max_score": 28},
                        }
                    },
                    description="DISC行为风格测评，评估支配型、影响型、稳健型、谨慎型四种风格",
                    status="active",
                )
                session.add(disc)
                print(f"   ✓ DISC: {len(disc_questions)}题")
            
            # MBTI问卷
            if 'mbti' in js_data:
                mbti_data = js_data['mbti']
                mbti_questions = _convert_js_questions_to_format(
                    mbti_data['questions'],
                    mbti_data['answerType']
                )
                mbti = Questionnaire(
                    name="MBTI性格测试",
                    type="MBTI",
                    questions_count=len(mbti_questions),
                    estimated_minutes=mbti_data.get('estimatedTime', 20),
                    questions_data={"questions": mbti_questions},
                    scoring_rules={
                        "dimensions": {
                            "EI": {"name": "外向/内向", "options": ["E", "I"]},
                            "SN": {"name": "实感/直觉", "options": ["S", "N"]},
                            "TF": {"name": "思考/情感", "options": ["T", "F"]},
                            "JP": {"name": "判断/知觉", "options": ["J", "P"]},
                        }
                    },
                    description="迈尔斯-布里格斯类型指标，识别16种人格类型",
                    status="active",
                )
                session.add(mbti)
                print(f"   ✓ MBTI: {len(mbti_questions)}题")
        else:
            print("   ⚠️ questionnaires.js加载失败，使用简化版初始化")
            # 降级：创建基本框架（但明确标注为待完善）
            epq = Questionnaire(
                name="EPQ人格测评（待完善）",
                type="EPQ",
                questions_count=0,
                estimated_minutes=15,
                questions_data={"questions": []},
                scoring_rules={},
                description="艾森克人格问卷（需要管理员导入题目）",
                status="inactive",
            )
            session.add(epq)
        
        session.commit()
        print("✅ 问卷数据初始化完成！")
