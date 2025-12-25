"""候选人数据迁移脚本 - 修复 submissions 中的 candidate_id 关联.

V46: 解决人员画像和人员管理人数不统一问题
"""

from sqlmodel import Session, select
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import get_engine
from app.models import Candidate
from app.models_assessment import Submission

# 获取引擎
engine = get_engine()


def migrate_orphan_submissions():
    """为所有 candidate_id 为空的 submissions 创建/关联 candidates 记录."""
    
    with Session(engine) as session:
        # 查找所有 candidate_id 为空的已完成提交
        orphan_subs = session.exec(
            select(Submission).where(
                Submission.candidate_id == None,
                Submission.status == 'completed'
            )
        ).all()
        
        print(f"📊 发现 {len(orphan_subs)} 条孤立提交记录（candidate_id 为空）")
        
        if not orphan_subs:
            print("✅ 无需迁移，所有提交记录都已关联候选人")
            return
        
        created_count = 0
        linked_count = 0
        
        for sub in orphan_subs:
            # 查找已存在的候选人（通过 phone + name）
            existing = session.exec(
                select(Candidate).where(
                    Candidate.phone == sub.candidate_phone,
                    Candidate.name == sub.candidate_name
                )
            ).first()
            
            if existing:
                sub.candidate_id = existing.id
                linked_count += 1
                print(f"  🔗 关联: {sub.candidate_name} ({sub.candidate_phone}) -> candidate_id={existing.id}")
            else:
                # 创建新候选人
                new_candidate = Candidate(
                    name=sub.candidate_name,
                    phone=sub.candidate_phone,
                    email=sub.candidate_email,
                    position=sub.target_position,
                    status='completed',
                    created_at=sub.submitted_at or datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(new_candidate)
                session.flush()  # 获取新 ID
                sub.candidate_id = new_candidate.id
                created_count += 1
                print(f"  ✨ 创建: {sub.candidate_name} ({sub.candidate_phone}) -> candidate_id={new_candidate.id}")
        
        session.commit()
        
        print(f"\n📈 迁移完成:")
        print(f"  - 新创建候选人: {created_count}")
        print(f"  - 关联已有候选人: {linked_count}")
        print(f"  - 总处理记录: {created_count + linked_count}")


def verify_migration():
    """验证迁移结果."""
    
    with Session(engine) as session:
        # 统计候选人数量
        candidates_count = session.exec(
            select(Candidate)
        ).all()
        
        # 统计已完成提交数量
        completed_subs = session.exec(
            select(Submission).where(Submission.status == 'completed')
        ).all()
        
        # 统计孤立提交
        orphan_subs = session.exec(
            select(Submission).where(
                Submission.candidate_id == None,
                Submission.status == 'completed'
            )
        ).all()
        
        # 统计唯一候选人（按 phone+name）
        unique_candidates = set()
        for sub in completed_subs:
            unique_candidates.add((sub.candidate_phone, sub.candidate_name))
        
        print("\n📊 验证结果:")
        print(f"  - candidates 表记录数: {len(candidates_count)}")
        print(f"  - submissions 已完成记录数: {len(completed_subs)}")
        print(f"  - submissions 唯一候选人数: {len(unique_candidates)}")
        print(f"  - submissions 孤立记录数: {len(orphan_subs)}")
        
        if len(orphan_subs) == 0:
            print("\n✅ 所有数据已正确关联！")
        else:
            print(f"\n⚠️ 仍有 {len(orphan_subs)} 条记录未关联")


if __name__ == "__main__":
    print("=" * 60)
    print("HR人事系统 - 候选人数据迁移脚本")
    print("=" * 60)
    
    # 执行迁移
    migrate_orphan_submissions()
    
    # 验证结果
    verify_migration()
    
    print("\n" + "=" * 60)

