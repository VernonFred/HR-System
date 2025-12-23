"""
修复 EPQ 问卷的题目数量
EPQ 实际有 88 道题，但数据库中可能显示为 48 道题
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models_assessment import Questionnaire


def fix_epq_questions_count():
    """修复 EPQ 问卷的题目数量."""
    engine = get_engine()
    
    with Session(engine) as session:
        # 查找 EPQ 问卷
        statement = select(Questionnaire).where(Questionnaire.type == "EPQ")
        epq = session.exec(statement).first()
        
        if not epq:
            print("❌ 未找到 EPQ 问卷")
            return
        
        print(f"📝 当前 EPQ 问卷信息：")
        print(f"   名称: {epq.name}")
        print(f"   类型: {epq.type}")
        print(f"   题目数量: {epq.questions_count}")
        print(f"   预计时长: {epq.estimated_minutes} 分钟")
        
        # 从 questions_data 中获取实际题目数量
        actual_count = 0
        if epq.questions_data and 'questions' in epq.questions_data:
            actual_count = len(epq.questions_data['questions'])
            print(f"   实际题目数量: {actual_count}")
        
        # 如果题目数量不是 88，则更新
        if epq.questions_count != 88:
            print(f"\n🔧 修复题目数量: {epq.questions_count} → 88")
            epq.questions_count = 88
            
            # 如果预计时长是旧的 5 分钟，也更新为 15 分钟（88题更合理）
            if epq.estimated_minutes == 5:
                print(f"🔧 修复预计时长: {epq.estimated_minutes} 分钟 → 15 分钟")
                epq.estimated_minutes = 15
            
            session.add(epq)
            session.commit()
            print("✅ EPQ 问卷信息已更新")
        else:
            print("\n✅ EPQ 题目数量正确，无需修复")
        
        # 显示更新后的信息
        session.refresh(epq)
        print(f"\n📊 更新后的信息：")
        print(f"   题目数量: {epq.questions_count}")
        print(f"   预计时长: {epq.estimated_minutes} 分钟")


if __name__ == "__main__":
    print("=" * 60)
    print("修复 EPQ 问卷题目数量")
    print("=" * 60)
    fix_epq_questions_count()
    print("=" * 60)

