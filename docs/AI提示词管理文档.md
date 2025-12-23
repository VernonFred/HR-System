# AI 提示词管理文档

> **版本**: v1.0  
> **更新日期**: 2025年12月12日  
> **适用对象**: 运维人员、产品经理、AI 工程师

---

## 📋 提示词文件位置

本系统的 AI 提示词（Prompt）**全部编写在 Python 代码中**，没有单独的 `.txt` 或 `.md` 配置文件。

### 核心提示词文件

| 文件路径 | 用途 | 包含的提示词 |
|---------|------|-------------|
| `backend/app/core/ai/prompt_builder.py` | **候选人画像生成**（核心功能） | • SYSTEM_PROMPT_NORMAL（基础版）<br>• SYSTEM_PROMPT_PRO（专业版，默认）<br>• SYSTEM_PROMPT_EXPERT（专家版） |
| `backend/app/api/resumes/parser.py` | 简历解析与分析 | • `_build_resume_parse_system_prompt()`<br>• 简历结构化提取提示词 |
| `backend/app/api/job_profiles/ai_helper.py` | 岗位画像配置 | • 简历分析提示词<br>• JD（Job Description）分析提示词 |
| `backend/app/api/assessments/questionnaire_parser.py` | 问卷文件解析 | • 问卷内容AI解析提示词 |

---

## 🎯 核心提示词详解

### 1. 候选人画像生成提示词（最重要）

**文件**: `backend/app/core/ai/prompt_builder.py`

#### 三个分析级别

| 级别 | 使用模型 | 变量名 | 适用场景 | 字数规模 |
|------|---------|--------|----------|---------|
| **Normal** | Qwen2.5-7B | `SYSTEM_PROMPT_NORMAL` | 快速批量分析、兜底模型 | 简洁版 |
| **Pro**（默认） | Qwen2.5-32B | `SYSTEM_PROMPT_PRO` | 日常使用、标准分析 | 标准版 |
| **Expert** | DeepSeek-R1 | `SYSTEM_PROMPT_EXPERT` | 重要候选人、深度洞察 | 详细版 |

#### 提示词位置

```python
# 文件: backend/app/core/ai/prompt_builder.py

# Normal 版（第 31-79 行）
SYSTEM_PROMPT_NORMAL = """你是一名经验丰富的HR专员..."""

# Pro 版（第 200-316 行，默认）
SYSTEM_PROMPT_PRO = """你是一名拥有 15 年经验的资深 HRBP..."""

# Expert 版（第 320-450 行）
SYSTEM_PROMPT_EXPERT = """你是一名顶级猎头公司的"人才洞察总监"..."""
```

#### 提示词核心要求

所有三个级别都遵循以下核心规则：

1. **禁止输出分数**：AI 生成的画像中不能出现任何数字分数（如"80分"、"75分"）
2. **禁止测评术语**：不能出现"DISC"、"MBTI"、"EPQ"等测评名称
3. **洞察 > 信息**：不要复述简历，要推断行为模式
4. **自然语言输出**：像资深HR和用人经理聊天，不是写报告
5. **JSON 格式输出**：必须返回合法的 JSON 结构

---

## 🔧 如何修改提示词

### 场景1: 调整画像分析风格

**需求示例**：希望 AI 分析更注重候选人的"创新能力"

**修改方法**：

1. 打开文件：`backend/app/core/ai/prompt_builder.py`
2. 找到对应级别的提示词（如 `SYSTEM_PROMPT_PRO`）
3. 在"你必须做到"章节添加：

```python
SYSTEM_PROMPT_PRO = """你是一名拥有 15 年经验的资深 HRBP...

【你必须做到】
1. 交叉验证：测评数据和简历经历是否一致？矛盾点说明什么？
2. 推断隐藏信息：从简历的"写了什么"和"没写什么"中推断候选人的特点
3. 预测行为模式：...
4. 识别风险信号：...
5. ⭐ 重点评估创新能力：从工作经历中识别候选人的创新实践，如主动优化流程、引入新方法、解决非常规问题等
"""
```

4. 重启后端服务：
```bash
systemctl restart talentlens-backend
```

---

### 场景2: 针对特定行业优化（如软件开发）

**需求示例**：公司主要招聘程序员、实施工程师、产品经理

**修改方法**：

在提示词中增加行业特定的分析维度：

```python
【行业特定关注点 - 软件研发公司】
1. 技术深度 vs 技术广度：是专精某一领域，还是多技术栈？
2. 技术学习能力：新技术的学习速度和主动性如何？
3. 工程化思维：是否有规范化、可维护性、团队协作的意识？
4. 问题解决能力：遇到复杂技术问题时的思考方式和解决路径
5. 产品思维：对于产品经理，是否能从技术视角理解产品需求？
```

**修改位置**：在 `SYSTEM_PROMPT_PRO` 的"核心原则"章节后添加

---

### 场景3: 修改输出结构

**需求示例**：增加"团队文化适配"字段

**修改方法**：

1. **修改提示词**（`prompt_builder.py`）：

```python
SYSTEM_PROMPT_PRO = """...

输出要求：
必须输出合法 JSON，不要包含任何解释性文字。JSON 结构如下：

{
  "summary_points": [...],
  "competencies": [...],
  "strengths": [...],
  "risks": [...],
  "suitable_positions": [...],
  "unsuitable_positions": [...],
  "interview_focus": [...],
  "quick_tags": [...],
  "team_culture_fit": {  # ⭐ 新增字段
    "preferred_culture": "候选人适合的团队文化类型（80-120字）",
    "culture_risks": "可能产生文化冲突的场景（60-80字）"
  }
}
"""
```

2. **修改数据模型**（`backend/app/api/ai/schemas.py`）：

```python
from pydantic import BaseModel

class TeamCultureFit(BaseModel):
    preferred_culture: str
    culture_risks: str

class PortraitResult(BaseModel):
    summary_points: List[str]
    competencies: List[CompetencyItem]
    strengths: List[str]
    risks: List[str]
    suitable_positions: List[str]
    unsuitable_positions: List[str]
    interview_focus: List[str]
    quick_tags: List[str]
    team_culture_fit: Optional[TeamCultureFit] = None  # ⭐ 新增
```

3. **修改前端显示**（`frontend/src/components/candidate/CandidatePortraitCard.vue`）

---

## 📦 提示词配置文件

### 岗位族配置

**文件**: `backend/app/core/ai/job_families.json`

这是一个 **JSON 配置文件**，定义了不同岗位族（如技术、产品、运营）的核心胜任力。

```json
{
  "job_families": {
    "technical": {
      "name": "技术研发",
      "keywords": ["开发", "程序员", "工程师", "架构师"],
      "core_competencies": [
        {"label": "技术深度", "weight": 1.2},
        {"label": "问题解决能力", "weight": 1.0},
        {"label": "代码质量意识", "weight": 0.8}
      ]
    },
    "product": {
      "name": "产品管理",
      "keywords": ["产品", "PM"],
      "core_competencies": [...]
    }
  }
}
```

**修改此文件后无需重启服务**（建议重启以确保生效）。

---

## 🚨 修改注意事项

### 1. 语法检查

修改提示词后，务必检查 Python 字符串语法：

```bash
cd /opt/talentlens/backend
python3 -m py_compile app/core/ai/prompt_builder.py
```

如果有语法错误，会报错提示。

### 2. 重启服务

修改提示词后必须重启后端服务：

```bash
# 开发环境
Ctrl+C（停止 uvicorn）
uvicorn app.main:app --reload

# 生产环境
systemctl restart talentlens-backend
```

### 3. 测试验证

修改后务必测试：

1. 创建一个测试候选人
2. 生成 AI 画像
3. 检查输出是否符合预期
4. 查看日志确认无错误

```bash
# 查看后端日志
tail -f /var/log/talentlens/error.log
```

### 4. 备份原提示词

修改前先备份：

```bash
cp backend/app/core/ai/prompt_builder.py backend/app/core/ai/prompt_builder.py.backup
```

---

## 🎨 提示词优化建议

### 1. 提示词工程最佳实践

#### ✅ 好的提示词特征
- **具体明确**：清晰定义任务目标和输出格式
- **结构化**：使用标题、列表、示例增强可读性
- **有约束**：明确禁止项（如"不要输出分数"）
- **有示例**：提供正确和错误的输出对比

#### ❌ 避免的问题
- 模糊指令：如"尽量分析"、"可能"
- 冗长啰嗦：重复表述相同要求
- 缺乏约束：没有明确输出格式
- 自相矛盾：前后要求冲突

### 2. 针对不同模型优化

| 模型 | 优化策略 |
|------|---------|
| Qwen2.5-7B (Normal) | 简化指令，减少复杂推理，明确输出结构 |
| Qwen2.5-32B (Pro) | 标准指令，平衡推理深度和性能 |
| DeepSeek-R1 (Expert) | 深度推理指令，鼓励多角度分析 |

### 3. 提示词版本管理

建议在提示词开头标注版本号：

```python
SYSTEM_PROMPT_PRO = """
【版本】v5.2 - 2025年12月12日更新
【更新内容】增强创新能力评估，优化团队适配分析

你是一名拥有 15 年经验的资深 HRBP...
"""
```

---

## 📊 提示词效果监控

### 1. 质量指标

建议定期评估 AI 输出质量：

| 指标 | 评估方法 | 目标 |
|------|---------|------|
| **输出格式正确率** | 检查是否返回合法 JSON | > 95% |
| **禁止项违规率** | 检查是否输出分数/术语 | < 5% |
| **内容洞察深度** | HR 主观评分（1-5分） | > 4.0 |
| **推荐准确性** | 用人经理反馈 | > 80% |

### 2. 日志分析

查看 AI 生成失败的案例：

```bash
# 查找 AI 解析错误
grep "AI portrait generation failed" /var/log/talentlens/error.log

# 查找 JSON 格式错误
grep "JSONDecodeError" /var/log/talentlens/error.log
```

---

## 🔐 安全建议

### 1. 提示词注入防护

当前系统已实现基础防护：

- 用户输入的简历内容会被清洗
- 禁止在简历中插入提示词指令
- API 限流防止滥用

### 2. 敏感信息处理

提示词中不要包含：

- ❌ 真实候选人信息
- ❌ 公司内部评价标准细节
- ❌ API 密钥或敏感配置

### 3. 合规性

确保提示词符合：

- 数据隐私法规（如 GDPR、个保法）
- 反歧视要求（避免基于年龄、性别的评价）
- 行业规范（如心理测评专业标准）

---

## 📞 技术支持

### 常见问题

**Q1: 修改提示词后 AI 输出变慢了？**
- **A**: 可能是提示词过长或要求过于复杂。建议精简指令，或降低 `max_tokens` 参数。

**Q2: AI 输出不符合 JSON 格式？**
- **A**: 检查提示词是否明确要求输出 JSON，且示例格式正确。增加"严格禁止输出任何解释性文字"的约束。

**Q3: 如何让 AI 更关注某个能力维度？**
- **A**: 在提示词中增加对应的分析要求，并在 `job_families.json` 中调整该能力的权重。

**Q4: 能否支持多语言提示词？**
- **A**: 可以。修改提示词为英文或其他语言，但需确保模型支持该语言。当前模型对中文优化最好。

---

## 📚 相关文档

- [大模型应用架构文档](./02_大模型应用架构文档.md) - 了解 AI 模型调用流程
- [AI画像分析文档](./03_AI画像分析文档.md) - 了解 AI 画像的可信性原理
- [API接口文档](./06_API接口文档.md) - 查看 AI 相关 API
- [后续维护文档](./05_后续维护文档.md) - 系统运维指南

---

**总结**：提示词是 AI 系统的"灵魂"，合理优化可以显著提升分析质量。建议在修改前充分测试，并做好版本管理和备份。🎯

