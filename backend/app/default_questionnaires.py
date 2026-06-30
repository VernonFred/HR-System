import json
import subprocess
from pathlib import Path

from sqlmodel import Session, select

from app.db import get_engine
from app.models_assessment import Questionnaire

def _load_questionnaires_from_js():
    """从 questionnaires.js 加载真实题目数据."""

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
    """初始化默认问卷数据（优先从JSON文件加载）."""
    from app.models_assessment import Questionnaire
    from pathlib import Path

    engine = get_engine()
    with Session(engine) as session:
        # 检查是否已有专业测评问卷
        statement = select(Questionnaire).where(Questionnaire.category == "professional")
        existing_professional = session.exec(statement).first()

        if existing_professional:
            print("✅ 专业测评问卷已存在，跳过初始化")
            return

        print("📝 开始初始化专业测评问卷...")

        # ⭐ 优先从 JSON 文件加载（不依赖 Node.js）
        json_path = Path(__file__).parent / "professional_questionnaires.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    questionnaires_data = json.load(f)

                for q_data in questionnaires_data:
                    q = Questionnaire(
                        name=q_data["name"],
                        type=q_data["type"],
                        category="professional",
                        questions_count=q_data["questions_count"],
                        estimated_minutes=q_data["estimated_minutes"],
                        questions_data=q_data["questions_data"],
                        scoring_rules=q_data["scoring_rules"],
                        description=q_data["description"],
                        status="active",
                    )
                    session.add(q)
                    print(f"   ✓ {q.name}: {q.questions_count}题")

                session.commit()
                print("✅ 专业测评问卷初始化完成！")
                return
            except Exception as e:
                print(f"⚠️ 从JSON加载失败: {e}")

        # 备选：尝试从questionnaires.js加载真实题目
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
                    category="professional",  # ⭐ 专业测评分类
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
                    category="professional",  # ⭐ 专业测评分类
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
                    category="professional",  # ⭐ 专业测评分类
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
