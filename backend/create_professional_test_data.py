#!/usr/bin/env python3
"""
为3个候选人创建专业测评（EPQ/DISC/MBTI）的完整提交记录
用于测试画像卡片导出功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime, timedelta
import json
import random

DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

# 3个候选人
candidates = [
    {"name": "张三", "phone": "13800138001", "position": "Python开发工程师", "gender": "男"},
    {"name": "李四", "phone": "13800138002", "position": "前端开发工程师", "gender": "女"},
    {"name": "王五", "phone": "13800138003", "position": "数据分析师", "gender": "男"}
]

# 3个专业测评的模拟结果数据
professional_results = {
    "EPQ": [
        {  # 张三 - EPQ结果
            "score": 75,
            "grade": "B",
            "result_details": {
                "E": 65,  # 外向性
                "N": 45,  # 神经质
                "P": 55,  # 精神质
                "L": 70,  # 掩饰性
                "personality_type": "外向稳定型",
                "description": "性格开朗，情绪稳定，善于交际，适应能力强。"
            }
        },
        {  # 李四 - EPQ结果
            "score": 68,
            "grade": "C",
            "result_details": {
                "E": 58,
                "N": 52,
                "P": 48,
                "L": 65,
                "personality_type": "中间型",
                "description": "性格较为平衡，既有外向特质也有内向特质，情绪较稳定。"
            }
        },
        {  # 王五 - EPQ结果
            "score": 82,
            "grade": "A",
            "result_details": {
                "E": 72,
                "N": 35,
                "P": 50,
                "L": 75,
                "personality_type": "外向稳定型",
                "description": "性格外向开朗，情绪非常稳定，抗压能力强，领导潜质突出。"
            }
        }
    ],
    "DISC": [
        {  # 张三 - DISC结果
            "score": 78,
            "grade": "B",
            "result_details": {
                "D": 65,  # 支配性
                "I": 70,  # 影响性
                "S": 55,  # 稳定性
                "C": 60,  # 服从性
                "primary_type": "I",
                "personality_type": "影响型",
                "description": "善于影响他人，热情开朗，擅长团队协作和沟通。"
            }
        },
        {  # 李四 - DISC结果
            "score": 72,
            "grade": "C",
            "result_details": {
                "D": 55,
                "I": 60,
                "S": 65,
                "C": 70,
                "primary_type": "C",
                "personality_type": "谨慎型",
                "description": "注重细节，工作严谨，追求完美，逻辑思维能力强。"
            }
        },
        {  # 王五 - DISC结果
            "score": 85,
            "grade": "A",
            "result_details": {
                "D": 75,
                "I": 68,
                "S": 58,
                "C": 72,
                "primary_type": "D",
                "personality_type": "支配型",
                "description": "果断决策，目标导向，执行力强，具有领导才能。"
            }
        }
    ],
    "MBTI": [
        {  # 张三 - MBTI结果
            "score": 80,
            "grade": "B",
            "result_details": {
                "type": "ENFP",
                "dimensions": {
                    "E": 65,  # 外向
                    "N": 70,  # 直觉
                    "F": 60,  # 情感
                    "P": 68   # 感知
                },
                "personality_type": "ENFP - 倡导者",
                "description": "充满热情和创造力，善于发现新机会，重视人际关系。"
            }
        },
        {  # 李四 - MBTI结果
            "score": 75,
            "grade": "C",
            "result_details": {
                "type": "ISTJ",
                "dimensions": {
                    "I": 58,
                    "S": 65,
                    "T": 62,
                    "J": 70
                },
                "personality_type": "ISTJ - 检查员",
                "description": "务实可靠，注重细节，有强烈的责任感，做事有条理。"
            }
        },
        {  # 王五 - MBTI结果
            "score": 88,
            "grade": "A",
            "result_details": {
                "type": "ENTJ",
                "dimensions": {
                    "E": 72,
                    "N": 75,
                    "T": 78,
                    "J": 80
                },
                "personality_type": "ENTJ - 指挥官",
                "description": "天生的领导者，战略思维强，善于组织和指挥，目标明确。"
            }
        }
    ]
}

def main():
    print("=" * 70)
    print("为3个候选人创建专业测评提交记录（EPQ + DISC + MBTI）")
    print("=" * 70)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 获取3个专业测评问卷
        cursor.execute("""
            SELECT id, name, type 
            FROM questionnaires 
            WHERE category = 'professional'
            ORDER BY id
        """)
        questionnaires = cursor.fetchall()
        
        if len(questionnaires) < 3:
            print(f"❌ 只找到 {len(questionnaires)} 个专业测评问卷，需要3个（EPQ/DISC/MBTI）")
            return
        
        print(f"✅ 找到 {len(questionnaires)} 个专业测评问卷:")
        for q in questionnaires:
            print(f"   - {q[1]} (ID: {q[0]}, Type: {q[2]})")
        print()
        
        # 2. 为每个问卷创建或获取分发链接
        assessments = {}
        now = datetime.now()
        
        for q_id, q_name, q_type in questionnaires:
            # 检查是否已有分发链接
            cursor.execute("""
                SELECT id FROM assessments 
                WHERE questionnaire_id = ?
                LIMIT 1
            """, (q_id,))
            existing = cursor.fetchone()
            
            if existing:
                assessment_id = existing[0]
                print(f"✅ 使用现有分发链接: {q_name} (Assessment ID: {assessment_id})")
            else:
                # 创建新的分发链接
                assessment_name = f"{q_name} - 测试分发链接"
                assessment_code = f"TEST-{q_type}-{now.strftime('%Y%m%d')}"
                
                cursor.execute("""
                    INSERT INTO assessments 
                    (name, code, questionnaire_id, valid_from, valid_until,
                     link_type, channel, allow_repeat, repeat_check_by,
                     repeat_interval_hours, max_submissions, view_count, start_count,
                     require_verification, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    assessment_name, assessment_code, q_id,
                    now.isoformat(), (now + timedelta(days=365)).isoformat(),
                    'permanent', 'public_link', True, 'phone',
                    0, 0, 0, 0, False,
                    now.isoformat(), now.isoformat()
                ))
                assessment_id = cursor.lastrowid
                print(f"✅ 创建新分发链接: {assessment_name} (Assessment ID: {assessment_id})")
            
            assessments[q_type] = {
                'id': assessment_id,
                'questionnaire_id': q_id,
                'name': q_name,
                'type': q_type
            }
        
        print()
        conn.commit()
        
        # 3. 为每个候选人创建3份提交记录（EPQ + DISC + MBTI）
        total_created = 0
        
        for cand_idx, candidate in enumerate(candidates):
            print(f"\n{'='*70}")
            print(f"处理候选人 [{cand_idx+1}/3]: {candidate['name']} - {candidate['position']}")
            print(f"{'='*70}\n")
            
            for test_type in ['EPQ', 'DISC', 'MBTI']:
                assessment = assessments[test_type]
                result_data = professional_results[test_type][cand_idx]
                
                print(f"  [{test_type}] 创建提交记录...")
                
                # 生成唯一的提交码
                code = f"SUB-{candidate['name'][:1].upper()}-{test_type}-{now.strftime('%Y%m%d%H%M%S')}"
                
                # 检查是否已存在
                cursor.execute("""
                    SELECT id FROM submissions 
                    WHERE assessment_id = ? AND candidate_phone = ?
                """, (assessment['id'], candidate['phone']))
                existing = cursor.fetchone()
                
                started_at = (now - timedelta(minutes=random.randint(30, 60))).isoformat()
                submitted_at = (now - timedelta(minutes=random.randint(5, 25))).isoformat()
                
                # 构造答案数据（模拟）
                answers = {f"q{i}": random.randint(1, 5) for i in range(1, 21)}
                
                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE submissions 
                        SET candidate_name = ?, gender = ?, target_position = ?,
                            answers = ?, total_score = ?, grade = ?, 
                            result_details = ?, status = 'completed',
                            submitted_at = ?
                        WHERE id = ?
                    """, (
                        candidate['name'], candidate['gender'], candidate['position'],
                        json.dumps(answers), result_data['score'], result_data['grade'],
                        json.dumps(result_data['result_details']), submitted_at,
                        existing[0]
                    ))
                    print(f"    ✅ 更新 (ID: {existing[0]}, 分数: {result_data['score']}, 等级: {result_data['grade']})")
                else:
                    # 创建
                    cursor.execute("""
                        INSERT INTO submissions 
                        (code, assessment_id, questionnaire_id,
                         candidate_name, candidate_phone, gender, target_position,
                         answers, total_score, grade, result_details,
                         status, started_at, submitted_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        code, assessment['id'], assessment['questionnaire_id'],
                        candidate['name'], candidate['phone'], candidate['gender'], candidate['position'],
                        json.dumps(answers), result_data['score'], result_data['grade'],
                        json.dumps(result_data['result_details']),
                        'completed', started_at, submitted_at
                    ))
                    submission_id = cursor.lastrowid
                    print(f"    ✅ 创建 (ID: {submission_id}, Code: {code}, 分数: {result_data['score']}, 等级: {result_data['grade']})")
                
                total_created += 1
        
        conn.commit()
        
        # 4. 显示统计
        print()
        print("=" * 70)
        print(f"✅ 成功创建/更新 {total_created} 份专业测评提交记录")
        print()
        
        # 按候选人分组显示
        for candidate in candidates:
            print(f"📋 {candidate['name']}:")
            cursor.execute("""
                SELECT q.type, s.total_score, s.grade
                FROM submissions s
                JOIN questionnaires q ON s.questionnaire_id = q.id
                WHERE s.candidate_phone = ? AND q.category = 'professional'
                ORDER BY q.id
            """, (candidate['phone'],))
            for row in cursor.fetchall():
                print(f"   - {row[0]}: {row[1]}分 ({row[2]}级)")
            print()
        
        print("=" * 70)
        print("🎉 专业测评数据创建完成！")
        print()
        print("💡 现在可以测试画像卡片导出了：")
        print()
        print("   1. 访问前端: http://localhost:5173/")
        print()
        print("   2. 进入「人员画像」页面")
        print("      - 每个候选人都有完整的专业测评数据")
        print()
        print("   3. 点击候选人的「导出」按钮")
        print("      - 测试画像卡片是否包含 EPQ/DISC/MBTI 的结果")
        print("      - 测试图片是否能正常显示")
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

