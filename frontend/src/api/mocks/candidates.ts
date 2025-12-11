import type { Candidate } from "../../types/candidate";

// ⚠️ Mock数据仅作为API失败时的fallback
// 正常情况下应该从后端API获取真实数据
export const MOCK_CANDIDATES: Candidate[] = [
  {
    id: 1,
    name: "张三",
    position: "产品经理",       // EPQ测评
    phone: "13812345678",
    score: 85,
    status: "已完成",
    grade: "A",
    level: "P6",
    tags: ["外向型", "结构化分析"],
    updated_at: "2025-12-02",
  },
  {
    id: 2,
    name: "李四",
    position: "实施工程师",     // DISC测评
    phone: "13912345678",
    score: 75,
    status: "已完成",
    grade: "B",
    level: "P5",
    tags: ["谨慎型", "注重细节"],
    updated_at: "2025-12-03",
  },
  {
    id: 3,
    name: "王五",
    position: "软件工程师",     // MBTI测评
    phone: "13712349999",
    score: 80,
    status: "已完成",
    grade: "A",
    level: "P5",
    tags: ["INTJ", "系统思维"],
    updated_at: "2025-12-04",
  },
  // ❌ 已删除赵六 - 只保留3个候选人，分别对应EPQ/DISC/MBTI
];
