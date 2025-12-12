#!/usr/bin/env python3
"""
创建3个候选人，每人做一种专业测评
- 张三：只做 EPQ
- 李四：只做 DISC
- 王五：只做 MBTI
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime, timedelta
import json
import random

DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

# 3个候选人，每人一种测评
candidates_data = [
    {
        "name": "张三",
        "phone": "13800138001",
        "position": "Python开发工程师",
        "gender": "男",
        "assessment_type": "EPQ",  # 只做EPQ
        "questionnaire_id": 1,
        "score": 75,
        "grade": "B",
        "result_details": {
            "type": "EPQ",
            "dimensions": {
                "E": 65,  # 外向性
                "N": 45,  # 神经质
                "P": 55,  # 精神质
                "L": 70   # 掩饰性
            },
            "personality_type": "外向稳定型",
            "description": "性格开朗，情绪稳定，善于交际，适应能力强。"
        }
    },
    {
        "name": "李四",
        "phone": "13800138002",
        "position": "前端开发工程师",
        "gender": "女",
        "assessment_type": "DISC",  # 只做DISC
        "questionnaire_id": 2,
        "score": 72,
        "grade": "C",
        "result_details": {
            "type": "DISC",
            "D": 55,  # 支配性
            "I": 60,  # 影响性
            "S": 65,  # 稳定性
            "C": 70,  # 服从性
            "primary_type": "C",
            "personality_type": "谨慎型",
            "description": "注重细节，工作严谨，追求完美，逻辑思维能力强。"
        }
    },
    {
        "name": "王五",
        "phone": "13800138003",
        "position": "数据分析师",
        "gender": "男",
        "assessment_type": "MBTI",  # 只做MBTI
        "questionnaire_id": 3,
        "score": 88,
        "grade": "A",
        "result_details": {
            "type": "ENTJ",
            "personality_type": "ENTJ - 指挥官",
            "dimensions": {
                "E": 72,  # 外向
                "N": 75,  # 直觉
                "T": 78,  # 思考
                "J": 80   # 判断
            },
            "description": "天生的领导者，战略思维强，善于组织和指挥，目标明确。"
        }
    }
]

def main():
    print("=" * 70)
    print("重新创建测试数据：每人一种专业测评")
    print("=" * 70)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 获取3个专业测评的assessment
        assessments = {}
        for test_type in ['EPQ', 'DISC', 'MBTI']:
            cursor.execute("""
                SELECT a.id, a.questionnaire_id
                FROM assessments a
                JOIN questionnaires q ON a.questionnaire_id = q.id
                WHERE q.type = ?
                LIMIT 1
            """, (test_type,))
            result = cursor.fetchone()
            if result:
                assessments[test_type] = {'assessment_id': result[0], 'questionnaire_id': result[1]}
        
        if len(assessments) < 3:
            print(f"❌ 只找到 {len(assessments)} 个专业测评分发链接")
            return
        
        print(f"✅ 找到3个专业测评分发链接")
        print()
        
        now = datetime.now()
        created_count = 0
        
        for idx, data in enumerate(candidates_data, 1):
            test_type = data['assessment_type']
            assessment = assessments[test_type]
            
            print(f"[{idx}/3] 创建: {data['name']} - {test_type}测评")
            
            # 生成提交码
            code = f"SUB-{data['name']}-{test_type}-{now.strftime('%Y%m%d')}"
            
            # 模拟答案
            answers = {f"q{i}": random.randint(1, 5) for i in range(1, 21)}
            
            started_at = (now - timedelta(minutes=random.randint(30, 60))).isoformat()
            submitted_at = (now - timedelta(minutes=random.randint(5, 25))).isoformat()
            
            # 获取candidate_id
            cursor.execute("SELECT id FROM candidates WHERE phone = ?", (data['phone'],))
            candidate = cursor.fetchone()
            candidate_id = candidate[0] if candidate else None
            
            # 创建提交记录
            cursor.execute("""
                INSERT INTO submissions 
                (code, assessment_id, questionnaire_id, candidate_id,
                 candidate_name, candidate_phone, gender, target_position,
                 answers, total_score, grade, result_details,
                 status, started_at, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code,
                assessment['assessment_id'],
                assessment['questionnaire_id'],
                candidate_id,
                data['name'], data['phone'], data['gender'], data['position'],
                json.dumps(answers), data['score'], data['grade'],
                json.dumps(data['result_details']),
                'completed', started_at, submitted_at
            ))
            
            submission_id = cursor.lastrowid
            print(f"  ✅ 创建成功 (ID: {submission_id}, {data['score']}分, {data['grade']}级)")
            created_count += 1
            print()
        
        conn.commit()
        
        # 验证结果
        print("=" * 70)
        print(f"✅ 成功创建 {created_count} 份测评数据")
        print()
        print("📋 测评分布:")
        
        for data in candidates_data:
            print(f"  {data['name']} - {data['assessment_type']}测评 - {data['score']}分 ({data['grade']}级)")
        
        print()
        print("=" * 70)
        print("🎉 数据创建完成！")
        print()
        print("💡 现在可以测试画像卡片导出了：")
        print()
        print("   1. 刷新前端: http://localhost:5173/")
        print()
        print("   2. 进入「人员画像」页面")
        print()
        print("   3. 分别查看3个候选人：")
        print("      - 张三：会显示 EPQ 圆环图")
        print("      - 李四：会显示 DISC 四色象限图")
        print("      - 王五：会显示 MBTI 进度条图")
        print()
        print("   4. 测试导出功能，检查三种图表是否都能正常显示")
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

