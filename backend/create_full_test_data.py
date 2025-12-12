#!/usr/bin/env python3
"""
为3个测试候选人创建完整的测评数据（包括提交记录）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from datetime import datetime
import uuid
import json

# 数据库路径
DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

def main():
    print("=" * 60)
    print("创建完整的测评数据（候选人 + 提交记录）")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 获取可用的问卷
        cursor.execute("SELECT id, code, name FROM questionnaire LIMIT 1")
        questionnaire = cursor.fetchone()
        
        if not questionnaire:
            print("❌ 数据库中没有问卷，请先创建问卷")
            return
        
        q_id, q_code, q_name = questionnaire
        print(f"✅ 使用问卷: {q_name} (ID: {q_id}, Code: {q_code})")
        print()
        
        # 2. 测试数据
        test_candidates = [
            {
                "name": "张三",
                "phone": "13800138001",
                "position": "Python开发工程师",
                "gender": "男",
                "score": 85.0,
                "result_details": {
                    "total_score": 85.0,
                    "dimensions": {
                        "技术能力": 90,
                        "项目经验": 85,
                        "团队协作": 80,
                        "学习能力": 85
                    }
                },
                "summary": "具备扎实的Python开发能力和丰富的项目经验，技术能力突出。"
            },
            {
                "name": "李四",
                "phone": "13800138002",
                "position": "前端开发工程师",
                "gender": "女",
                "score": 78.0,
                "result_details": {
                    "total_score": 78.0,
                    "dimensions": {
                        "技术能力": 80,
                        "项目经验": 75,
                        "团队协作": 82,
                        "学习能力": 75
                    }
                },
                "summary": "前端技术扎实，有良好的团队协作能力，UI/UX理解深入。"
            },
            {
                "name": "王五",
                "phone": "13800138003",
                "position": "数据分析师",
                "gender": "男",
                "score": 92.0,
                "result_details": {
                    "total_score": 92.0,
                    "dimensions": {
                        "技术能力": 95,
                        "项目经验": 90,
                        "团队协作": 88,
                        "学习能力": 95
                    }
                },
                "summary": "数据分析能力出众，具备深厚的技术功底和丰富的项目经验。"
            }
        ]
        
        created_count = 0
        
        for idx, data in enumerate(test_candidates, 1):
            print(f"[{idx}/3] 处理: {data['name']} - {data['position']}")
            
            now = datetime.utcnow().isoformat()
            
            # 检查候选人是否存在
            cursor.execute("SELECT id, submission_id FROM candidates WHERE phone = ?", (data['phone'],))
            candidate = cursor.fetchone()
            
            if not candidate:
                print(f"  ⚠️  候选人不存在，跳过")
                continue
            
            candidate_id = candidate[0]
            existing_submission_id = candidate[1]
            
            # 如果已有submission，更新它
            if existing_submission_id:
                cursor.execute("""
                    UPDATE submission 
                    SET total_score = ?, result_details = ?, summary = ?
                    WHERE id = ?
                """, (
                    data['score'],
                    json.dumps(data['result_details']),
                    data['summary'],
                    existing_submission_id
                ))
                submission_id = existing_submission_id
                print(f"  ✅ 更新现有提交记录 (ID: {submission_id})")
            else:
                # 创建新的submission
                submission_code = f"SUB_{uuid.uuid4().hex[:8].upper()}"
                cursor.execute("""
                    INSERT INTO submission 
                    (submission_code, questionnaire_id, total_score, result_details, summary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    submission_code,
                    q_id,
                    data['score'],
                    json.dumps(data['result_details']),
                    data['summary'],
                    now
                ))
                submission_id = cursor.lastrowid
                print(f"  ✅ 创建提交记录 (ID: {submission_id}, Code: {submission_code})")
                
                # 更新候选人的submission_id
                cursor.execute("""
                    UPDATE candidates 
                    SET submission_id = ?, updated_at = ?
                    WHERE id = ?
                """, (submission_id, now, candidate_id))
                print(f"  ✅ 关联候选人与提交记录")
            
            created_count += 1
            print()
        
        conn.commit()
        
        # 验证结果
        print("=" * 60)
        print(f"✅ 成功处理 {created_count} 个候选人")
        print()
        
        # 显示所有有提交记录的候选人
        cursor.execute("""
            SELECT c.id, c.name, c.position, c.gender, s.submission_code, s.total_score
            FROM candidates c
            LEFT JOIN submission s ON c.submission_id = s.id
            WHERE c.submission_id IS NOT NULL
            ORDER BY c.id
        """)
        
        print("📋 所有有提交记录的候选人:")
        for row in cursor.fetchall():
            print(f"  {row[0]}. {row[1]} - {row[2]} - {row[3]} | 提交码: {row[4]} | 分数: {row[5]}")
        
        print()
        print("💡 现在可以测试了：")
        print("   1. 访问 http://localhost:5173/")
        print("   2. 「人员画像」- 查看候选人和导出功能")
        print("   3. 「问卷中心」- 查看提交记录")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()

