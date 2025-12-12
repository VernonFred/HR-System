#!/usr/bin/env python3
"""
用正确的格式重新创建3个候选人的专业测评数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
import json

DB_PATH = "/Users/Python项目/HR人事/backend/hr.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 张三 - EPQ测评（标准格式）
        epq_result = {
            "questionnaire_type": "EPQ",
            "epq_personality_trait": "外向稳定型",
            "epq_description": "性格开朗，情绪稳定，善于交际，适应能力强",
            "epq_dimensions": {
                "E": {"label": "外向性", "value": 65, "t_score": 65, "level": "中"},
                "N": {"label": "神经质", "value": 45, "t_score": 45, "level": "中"},
                "P": {"label": "精神质", "value": 55, "t_score": 55, "level": "中"},
                "L": {"label": "掩饰性", "value": 70, "t_score": 70, "level": "高"}
            }
        }
        
        cursor.execute("""
            UPDATE submissions 
            SET result_details = ?
            WHERE candidate_phone = '13800138001'
        """, (json.dumps(epq_result),))
        print("✅ 张三 - EPQ数据 (65/45/55/70)")
        
        # 李四 - DISC测评（标准格式）
        disc_result = {
            "questionnaire_type": "DISC",
            "disc_type": "C",
            "disc_description": "谨慎型 - 注重细节，工作严谨，追求完美",
            "disc_dimensions": {
                "D": {"label": "支配型", "value": 55},
                "I": {"label": "影响型", "value": 60},
                "S": {"label": "稳健型", "value": 65},
                "C": {"label": "谨慎型", "value": 70}
            }
        }
        
        cursor.execute("""
            UPDATE submissions 
            SET result_details = ?
            WHERE candidate_phone = '13800138002'
        """, (json.dumps(disc_result),))
        print("✅ 李四 - DISC数据 (D:55/I:60/S:65/C:70)")
        
        # 王五 - MBTI测评（标准格式）
        mbti_result = {
            "questionnaire_type": "MBTI",
            "mbti_type": "ENTJ",
            "mbti_description": "指挥官 - 天生的领导者，战略思维强",
            "mbti_dimensions": {
                "E-I": {"tendency": "E", "label": "外向", "value": 72},
                "S-N": {"tendency": "N", "label": "直觉", "value": 75},
                "T-F": {"tendency": "T", "label": "思考", "value": 78},
                "J-P": {"tendency": "J", "label": "判断", "value": 80}
            }
        }
        
        cursor.execute("""
            UPDATE submissions 
            SET result_details = ?
            WHERE candidate_phone = '13800138003'
        """, (json.dumps(mbti_result),))
        print("✅ 王五 - MBTI数据 (ENTJ: E72/N75/T78/J80)")
        
        conn.commit()
        
        # 清空画像缓存
        cursor.execute("DELETE FROM portrait_cache WHERE candidate_id IN (3, 4, 5)")
        print("\n✅ 已清空画像缓存")
        conn.commit()
        
        print()
        print("=" * 70)
        print("✅ 数据创建完成！")
        print()
        print("📋 3个候选人 - 3种测评：")
        print("   1. 张三 - EPQ人格测评 (应显示4个圆环)")
        print("   2. 李四 - DISC性格分析 (应显示四色象限)")
        print("   3. 王五 - MBTI性格测试 (应显示4个进度条)")
        print()
        print("💡 请刷新前端页面测试：")
        print("   http://localhost:5173/")
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

