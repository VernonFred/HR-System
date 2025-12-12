#!/usr/bin/env python3
"""
为3个候选人创建真实的提交记录（用于测试画像卡片导出）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime, timedelta
import json
import random

DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

# 3个候选人的测试数据
test_candidates = [
    {
        "name": "张三",
        "phone": "13800138001",
        "position": "Python开发工程师",
        "gender": "男",
        "score": 85,
        "grade": "B",
        "result_details": {
            "dimensions": {
                "技术能力": 90,
                "项目经验": 85,
                "团队协作": 80,
                "学习能力": 85,
                "沟通能力": 82
            },
            "summary": "技术能力突出，具备扎实的Python开发功底和丰富的项目经验。团队协作和学习能力良好。"
        },
        "answers": {
            "q1": "5年Python开发经验",
            "q2": 4,
            "q3": 5,
            "q4": ["Django", "FastAPI", "Flask"],
            "q5": "精通后端开发，熟悉微服务架构"
        }
    },
    {
        "name": "李四",
        "phone": "13800138002",
        "position": "前端开发工程师",
        "gender": "女",
        "score": 78,
        "grade": "C",
        "result_details": {
            "dimensions": {
                "技术能力": 80,
                "项目经验": 75,
                "团队协作": 82,
                "学习能力": 76,
                "沟通能力": 77
            },
            "summary": "前端技术扎实，UI/UX理解深入。团队协作能力出色，有良好的学习态度。"
        },
        "answers": {
            "q1": "3年Vue/React开发经验",
            "q2": 4,
            "q3": 4,
            "q4": ["Vue", "React", "TypeScript"],
            "q5": "擅长组件化开发和性能优化"
        }
    },
    {
        "name": "王五",
        "phone": "13800138003",
        "position": "数据分析师",
        "gender": "男",
        "score": 92,
        "grade": "A",
        "result_details": {
            "dimensions": {
                "技术能力": 95,
                "项目经验": 90,
                "团队协作": 88,
                "学习能力": 95,
                "沟通能力": 92
            },
            "summary": "数据分析能力出众，具备深厚的技术功底和丰富的大数据项目经验。综合能力优秀。"
        },
        "answers": {
            "q1": "7年数据分析经验",
            "q2": 5,
            "q3": 5,
            "q4": ["Python", "SQL", "Tableau", "PowerBI"],
            "q5": "擅长机器学习模型构建和数据可视化"
        }
    }
]

def main():
    print("=" * 70)
    print("为3个候选人创建完整的提交记录（用于测试画像卡片导出）")
    print("=" * 70)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 获取一个可用的assessment（优先选择最新的）
        cursor.execute("""
            SELECT id, name, questionnaire_id 
            FROM assessments 
            ORDER BY id DESC 
            LIMIT 1
        """)
        assessment = cursor.fetchone()
        
        if not assessment:
            print("❌ 没有找到可用的分发链接，请先在前端创建一个分发链接")
            return
        
        assessment_id, assessment_name, questionnaire_id = assessment
        print(f"✅ 使用分发链接: {assessment_name}")
        print(f"   Assessment ID: {assessment_id}")
        print(f"   Questionnaire ID: {questionnaire_id}")
        print()
        
        # 2. 为每个候选人创建提交记录
        created_count = 0
        now = datetime.now()
        
        for idx, data in enumerate(test_candidates, 1):
            print(f"[{idx}/3] 创建提交记录: {data['name']} - {data['position']}")
            
            # 生成唯一的提交码
            code = f"SUB-{data['name'][:1].upper()}-{now.strftime('%Y%m%d%H%M%S')}-{idx}"
            
            # 检查是否已存在（根据手机号和assessment_id）
            cursor.execute("""
                SELECT id FROM submissions 
                WHERE assessment_id = ? AND candidate_phone = ?
            """, (assessment_id, data['phone']))
            existing = cursor.fetchone()
            
            started_at = (now - timedelta(minutes=random.randint(10, 30))).isoformat()
            submitted_at = now.isoformat()
            
            if existing:
                # 更新现有记录
                cursor.execute("""
                    UPDATE submissions 
                    SET candidate_name = ?, gender = ?, target_position = ?,
                        answers = ?, total_score = ?, grade = ?, 
                        result_details = ?, status = 'completed',
                        submitted_at = ?
                    WHERE id = ?
                """, (
                    data['name'], data['gender'], data['position'],
                    json.dumps(data['answers']), data['score'], data['grade'],
                    json.dumps(data['result_details']), submitted_at,
                    existing[0]
                ))
                submission_id = existing[0]
                print(f"  ✅ 更新现有提交记录 (ID: {submission_id})")
            else:
                # 创建新提交记录
                cursor.execute("""
                    INSERT INTO submissions 
                    (code, assessment_id, questionnaire_id,
                     candidate_name, candidate_phone, gender, target_position,
                     answers, total_score, grade, result_details,
                     status, started_at, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    code, assessment_id, questionnaire_id,
                    data['name'], data['phone'], data['gender'], data['position'],
                    json.dumps(data['answers']), data['score'], data['grade'],
                    json.dumps(data['result_details']),
                    'completed', started_at, submitted_at
                ))
                submission_id = cursor.lastrowid
                print(f"  ✅ 创建新提交记录 (ID: {submission_id}, Code: {code})")
            
            # 3. 更新候选人表（关联提交记录）- 这里我们不使用submission_id，而是通过候选人表直接查询
            cursor.execute("""
                UPDATE candidates 
                SET status = 'completed', updated_at = ?
                WHERE phone = ?
            """, (now.isoformat(), data['phone']))
            
            created_count += 1
            print()
        
        conn.commit()
        
        # 4. 验证结果
        print("=" * 70)
        print(f"✅ 成功创建/更新 {created_count} 个提交记录")
        print()
        
        # 显示所有提交记录
        cursor.execute("""
            SELECT s.id, s.code, s.candidate_name, s.target_position, 
                   s.total_score, s.grade, s.status
            FROM submissions s
            WHERE s.assessment_id = ?
            ORDER BY s.id
        """, (assessment_id,))
        
        print("📋 当前分发链接下的所有提交记录:")
        for row in cursor.fetchall():
            print(f"  {row[0]}. {row[1]} | {row[2]} - {row[3]} | {row[4]}分 ({row[5]}级) | {row[6]}")
        
        print()
        print("=" * 70)
        print("🎉 测试数据创建完成！")
        print()
        print("💡 现在可以测试画像卡片导出了：")
        print()
        print("   1. 访问前端: http://localhost:5173/")
        print()
        print("   2. 进入「人员画像」页面")
        print("      - 应该能看到 4 个候选人（王力宏 + 新增的3个）")
        print()
        print("   3. 进入「问卷中心」页面")
        print("      - 应该能看到新增的 3 条提交记录")
        print()
        print("   4. 点击任意候选人的「导出」按钮")
        print("      - 测试画像卡片的图片导出功能")
        print()
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()

