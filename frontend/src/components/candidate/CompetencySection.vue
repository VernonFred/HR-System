<script setup lang="ts">
import { computed } from 'vue'
import CompetencyList from './CompetencyList.vue'
import CompetencySummary from './CompetencySummary.vue'

interface Competency {
  key: string
  label: string
  score: number
}

const props = defineProps<{
  competencies: Competency[]
}>()

// 🟢 P0优化：计算强弱项
const topCompetencies = computed(() => {
  if (!props.competencies || props.competencies.length === 0) return []
  return props.competencies
    .filter(c => c.score >= 80)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
})

const bottomCompetencies = computed(() => {
  if (!props.competencies || props.competencies.length === 0) return []
  return props.competencies
    .filter(c => c.score < 70)
    .sort((a, b) => a.score - b.score)
    .slice(0, 2)
})
</script>

<template>
  <div class="card-section competency-section">
    <div class="section-header">
      <div class="header-icon">
        <i class="ri-bar-chart-box-line"></i>
      </div>
      <div>
        <h2 class="section-title">岗位胜任力分布</h2>
        <p class="section-subtitle">JOB COMPETENCY DISTRIBUTION</p>
      </div>
    </div>

    <!-- 能力列表 -->
    <CompetencyList :competencies="competencies" />

    <!-- 🟢 P0优化：强弱项总结 -->
    <CompetencySummary 
      :top-competencies="topCompetencies"
      :bottom-competencies="bottomCompetencies"
    />
  </div>
</template>

<style scoped>
/* 🎨 岗位胜任力区域样式 */
.card-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease;
}

.card-section:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.125rem;
}

.header-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.125rem;
  flex-shrink: 0;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.section-subtitle {
  font-size: 0.6875rem;
  color: #94a3b8;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}
</style>

