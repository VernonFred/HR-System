#!/usr/bin/env python3
"""
创建1个用户做3种专业测评
"""
import sys
sys.path.insert(0, '/Users/Python项目/HR人事/backend')

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 创建候选人"赵六"
        cursor.execute("""
            INSERT INTO candidates (name, phone, gender, position, status, created_at)
            VALUES ('赵六', '13900139000', '男', 'AI算法工程师', 'active', datetime('now'))
        """)
        candidate_id = cursor.lastrowid
        print(f"✅ 创建候选人: 赵六 (ID: {candidate_id})")
        
        # 2. 创建3份测评提交记录
        now = datetime.now()
        
        # 2.1 EPQ测评
        epq_result = {
            "questionnaire_type": "EPQ",
            "epq_personality_trait": "内向稳定型",
            "epq_description": "性格内向，善于思考，情绪稳定",
            "epq_dimensions": {
                "E": {"label": "外向性", "value": 35, "t_score": 40, "level": "低"},
                "N": {"label": "神经质", "value": 40, "t_score": 45, "level": "中"},
                "P": {"label": "精神质", "value": 70, "t_score": 70, "level": "高"},
                "L": {"label": "掩饰性", "value": 60, "t_score": 60, "level": "中"}
            }
        }
        
        cursor.execute("""
            INSERT INTO submissions 
            (code, assessment_id, questionnaire_id, candidate_id,
             candidate_name, candidate_phone, gender, target_position,
             answers, scores, total_score, grade, result_details,
             status, started_at, submitted_at)
            VALUES (?, 1, 1, ?, '赵六', '13900139000', '男', 'AI算法工程师',
                    '{}', ?, 61, 'C', ?, 'completed', ?, ?)
        """, (
            f"EPQ-{now.strftime('%Y%m%d%H%M%S')}",
            candidate_id,
            json.dumps({"E": 35, "N": 40, "P": 70, "L": 60}),
            json.dumps(epq_result),
            (now - timedelta(hours=3)).isoformat(),
            (now - timedelta(hours=2, minutes=45)).isoformat()
        ))
        print(f"✅ EPQ测评提交 (ID: {cursor.lastrowid}, 61分)")
        
        # 2.2 DISC测评
        disc_result = {
            "questionnaire_type": "DISC",
            "disc_type": "S",
            "disc_description": "稳健型 - 耐心稳重，团队协作能力强",
            "disc_dimensions": {
                "D": {"label": "支配型", "value": 40},
                "I": {"label": "影响型", "value": 45},
                "S": {"label": "稳健型", "value": 75},
                "C": {"label": "谨慎型", "value": 68}
            }
        }
        
        cursor.execute("""
            INSERT INTO submissions 
            (code, assessment_id, questionnaire_id, candidate_id,
             candidate_name, candidate_phone, gender, target_position,
             answers, scores, total_score, grade, result_details,
             status, started_at, submitted_at)
            VALUES (?, 2, 2, ?, '赵六', '13900139000', '男', 'AI算法工程师',
                    '{}', ?, 70, 'B', ?, 'completed', ?, ?)
        """, (
            f"DISC-{now.strftime('%Y%m%d%H%M%S')}",
            candidate_id,
            json.dumps({"D": 40, "I": 45, "S": 75, "C": 68}),
            json.dumps(disc_result),
            (now - timedelta(hours=2)).isoformat(),
            (now - timedelta(hours=1, minutes=45)).isoformat()
        ))
        print(f"✅ DISC测评提交 (ID: {cursor.lastrowid}, 70分)")
        
        # 2.3 MBTI测评
        mbti_result = {
            "questionnaire_type": "MBTI",
            "mbti_type": "ISTJ",
            "mbti_description": "物流师 - 实际务实，注重细节，责任心强",
            "mbti_dimensions": {
                "E-I": {"tendency": "I", "label": "内向", "value": 68},
                "S-N": {"tendency": "S", "label": "感觉", "value": 72},
                "T-F": {"tendency": "T", "label": "思考", "value": 70},
                "J-P": {"tendency": "J", "label": "判断", "value": 75}
            }
        }
        
        cursor.execute("""
            INSERT INTO submissions 
            (code, assessment_id, questionnaire_id, candidate_id,
             candidate_name, candidate_phone, gender, target_position,
             answers, scores, total_score, grade, result_details,
             status, started_at, submitted_at)
            VALUES (?, 3, 3, ?, '赵六', '13900139000', '男', 'AI算法工程师',
                    '{}', ?, 85, 'A', ?, 'completed', ?, ?)
        """, (
            f"MBTI-{now.strftime('%Y%m%d%H%M%S')}",
            candidate_id,
            json.dumps({"E-I": 68, "S-N": 72, "T-F": 70, "J-P": 75}),
            json.dumps(mbti_result),
            (now - timedelta(hours=1)).isoformat(),
            (now - timedelta(minutes=40)).isoformat()
        ))
        print(f"✅ MBTI测评提交 (ID: {cursor.lastrowid}, 85分)")
        
        conn.commit()
        
        print()
        print("=" * 70)
        print(f"🎉 测试数据创建成功！候选人ID: {candidate_id}")
        print()
        print("📋 赵六的3份测评：")
        print("   1. EPQ人格测评 - 61分 (C级) - 内向稳定型")
        print("   2. DISC性格分析 - 70分 (B级) - 稳健型(S)")
        print("   3. MBTI性格测试 - 85分 (A级) - ISTJ物流师")
        print()
        print("💡 请在前端测试：")
        print("   1. 刷新人员画像页面")
        print("   2. 找到「赵六」的画像")
        print("   3. 点击右侧不同的测评记录，观察左侧图表是否正确切换")
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

