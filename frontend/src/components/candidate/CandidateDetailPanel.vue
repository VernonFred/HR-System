<script setup lang="ts">
import type { CandidateProfile } from "../../types/candidate";
import PersonalityRadarChart from "./PersonalityRadarChart.vue";

const props = defineProps<{ profile: CandidateProfile | null }>();

const ringTone = (score: number) => {
  if (score >= 80) return "tone-excellent";
  if (score >= 60) return "tone-medium";
  return "tone-danger";
};
</script>

<template>
  <div class="detail-root">
    <div v-if="!profile" class="empty">
      <i class="ri-user-search-line"></i>
      <h3>请选择候选人查看画像</h3>
      <p>包含人格分布、岗位胜任力、画像总结、亮点/风险与简历摘要</p>
    </div>
    <div v-else class="page">
      <!-- 顶部区域 -->
      <div class="top-grid">
        <!-- 左：人格/岗位条形图 -->
        <section class="card dim-card">
          <div class="dim-block">
            <div class="card-title">人格特征分布</div>
            <div class="bar-list">
              <div v-for="d in profile.personalityDimensions" :key="d.key" class="bar-row">
                <div class="bar-label">
                  <span class="edge">低</span>
                  <span class="name">{{ d.label }}</span>
                  <span class="edge">高</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: d.score + '%' }"></div>
                  <div class="bar-thumb" :style="{ left: d.score + '%' }"></div>
                </div>
                <div class="bar-meta">{{ d.score }}%</div>
              </div>
            </div>
          </div>
          <div class="dim-block">
            <div class="card-title">岗位胜任力分布</div>
            <div class="bar-list">
              <div v-for="c in profile.competencies" :key="c.key" class="bar-row">
                <div class="bar-label">
                  <span class="edge">低</span>
                  <span class="name">{{ c.label }}</span>
                  <span class="edge">高</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: c.score + '%' }"></div>
                  <div class="bar-thumb" :style="{ left: c.score + '%' }"></div>
                </div>
                <div class="bar-meta">{{ c.score }}%</div>
              </div>
            </div>
          </div>
        </section>

        <!-- 右：候选人概要 -->
        <section class="card summary-card" :style="{ '--score': profile.overallMatchScore + '%' }">
          <div class="summary-header">
            <div class="avatar">{{ profile.name.charAt(0) }}</div>
            <div class="info">
              <div class="name">{{ profile.name }}</div>
              <div class="role">{{ profile.appliedPosition }}</div>
              <div class="meta">更新于 {{ profile.updatedAt }}</div>
            </div>
          </div>
          <div class="summary-body">
            <div class="ring" :class="ringTone(profile.overallMatchScore)">
              <div class="ring-inner">
                <div class="ring-value">{{ profile.overallMatchScore }}</div>
                <div class="ring-label">综合匹配度</div>
              </div>
            </div>
            <div class="tags">
              <span v-for="tag in profile.tags" :key="tag" class="pill tag">{{ tag }}</span>
            </div>
          </div>
        </section>
      </div>

      <!-- 中部区域 -->
      <div class="middle-grid">
        <section class="card text-card">
          <div class="card-title">画像总结（人格 & 职业倾向）</div>
          <p class="summary-text">{{ profile.aiAnalysisText }}</p>
        </section>
        <section class="card radar-card">
          <div class="card-title">人格维度雷达图</div>
          <PersonalityRadarChart :dimensions="profile.personalityDimensions" />
        </section>
      </div>

      <!-- 底部区域 -->
      <div class="bottom-grid">
        <section class="card list-card">
          <div class="card-title">优势亮点</div>
          <ul class="list">
            <li v-for="(item, idx) in profile.highlights" :key="idx">🟢 {{ item }}</li>
          </ul>
        </section>
        <section class="card list-card">
          <div class="card-title">潜在风险</div>
          <ul class="list">
            <li v-for="(item, idx) in profile.risks" :key="idx">🟠 {{ item }}</li>
          </ul>
        </section>
        <section class="card resume-card">
          <div class="card-title">简历摘要</div>
          <div v-if="profile.hasResume" class="resume-content">
            <div class="resume-block">
              <div class="label">教育</div>
              <div class="text">{{ profile.resumeEducation }}</div>
            </div>
            <div class="resume-block">
              <div class="label">经历</div>
              <div class="text">{{ profile.resumeExperiences }}</div>
            </div>
            <div class="resume-block" v-if="profile.resumeSkills?.length">
              <div class="label">技能</div>
              <div class="pill-list">
                <span v-for="s in profile.resumeSkills" :key="s" class="pill skill">{{ s }}</span>
              </div>
            </div>
          </div>
          <div v-else class="resume-content empty-resume">
            简历未上传，本画像基于测评数据生成。
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-root {
  width: 100%;
  min-height: 100%;
  background: #f7f8fa;
  padding: 16px;
  border-radius: 12px;
}
.empty {
  border: 1px dashed rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  color: #6d6f76;
  display: grid;
  gap: 8px;
  place-items: center;
  background: #f1f3f5;
}
.empty i {
  font-size: 28px;
}
.page {
  display: grid;
  gap: 24px;
}
.top-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}
.card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  padding: 20px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1b1c1f;
  margin-bottom: 12px;
}

.dim-card {
  display: grid;
  gap: 16px;
}
.dim-block {
  display: grid;
  gap: 12px;
}
.bar-list {
  display: grid;
  gap: 12px;
}
.bar-row {
  display: grid;
  gap: 6px;
}
.bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #6d6f76;
  font-size: 13px;
}
.bar-label .name {
  font-size: 14px;
  font-weight: 600;
  color: #1b1c1f;
}
.bar-track {
  position: relative;
  width: 100%;
  height: 12px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.05);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6a5aec, #a798ff);
}
.bar-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #6a5aec;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.bar-meta {
  color: #1b1c1f;
  font-weight: 600;
  font-size: 13px;
}
.edge {
  font-size: 12px;
}

.summary-card {
  display: grid;
  gap: 12px;
}
.summary-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6a5aec, #7a6cff);
  display: grid;
  place-items: center;
  font-weight: 700;
  color: #fff;
  font-size: 20px;
}
.info {
  display: grid;
  gap: 4px;
}
.name {
  font-size: 20px;
  font-weight: 700;
  color: #1b1c1f;
}
.role {
  color: #4a4e55;
  font-size: 14px;
}
.meta {
  color: #6d6f76;
  font-size: 13px;
}
.summary-body {
  display: grid;
  gap: 8px;
  align-items: center;
}
.ring {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(#6a5aec var(--score), rgba(0, 0, 0, 0.06) 0);
  margin: 0 auto;
}
.ring.tone-excellent {
  background: conic-gradient(#34c759 var(--score), rgba(0, 0, 0, 0.06) 0);
}
.ring.tone-medium {
  background: conic-gradient(#ffa654 var(--score), rgba(0, 0, 0, 0.06) 0);
}
.ring-inner {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.ring-value {
  font-size: 24px;
  font-weight: 700;
  color: #5c4fe7;
  line-height: 1;
}
.ring-label {
  color: #6d6f76;
  font-size: 12px;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.pill {
  padding: 6px 12px;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 13px;
  height: 32px;
  display: inline-flex;
  align-items: center;
}
.tag {
  background: #f1f0ff;
  color: #6a5aec;
}

.middle-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 16px;
}
.text-card .summary-text {
  color: #4a4e55;
  line-height: 1.7;
}
.radar-card {
  padding: 16px 16px 24px 16px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.list-card .list {
  display: grid;
  gap: 8px;
  color: #4a4e55;
  padding-left: 0;
  list-style: none;
}
.resume-card .resume-content {
  display: grid;
  gap: 10px;
}
.resume-card .label {
  color: #6d6f76;
  font-weight: 600;
  font-size: 13px;
}
.resume-card .text {
  color: #4a4e55;
  font-size: 14px;
}
.resume-card .pill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.resume-card .pill.skill {
  background: #eaf1ff;
  color: #2a3a7b;
}
.empty-resume {
  color: #6d6f76;
  font-size: 14px;
}

@media (max-width: 1280px) {
  .top-grid {
    grid-template-columns: 1fr;
  }
  .middle-grid {
    grid-template-columns: 1fr;
  }
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}
</style>
