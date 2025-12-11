-- 数据库迁移：添加问卷分类字段 (category)
-- 执行时间：2025-12-04
-- 目的：支持导航结构重构（画像中心/问卷中心）

-- 1. 添加 category 字段到 questionnaires 表
ALTER TABLE questionnaires ADD COLUMN category VARCHAR(20) DEFAULT 'survey';

-- 2. 更新现有专业测评的 category 为 'professional'
UPDATE questionnaires SET category = 'professional' WHERE type IN ('EPQ', 'DISC', 'MBTI');

-- 3. 更新评分问卷的 category 为 'scored'
UPDATE questionnaires SET category = 'scored' WHERE custom_type = 'scored' AND type = 'custom';

-- 4. 更新调查问卷的 category 为 'survey'
UPDATE questionnaires SET category = 'survey' WHERE custom_type = 'non_scored' AND type = 'custom';

-- 验证迁移结果
SELECT id, name, type, category, custom_type FROM questionnaires;

