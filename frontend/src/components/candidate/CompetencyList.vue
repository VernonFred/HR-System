<script setup lang="ts">
interface Competency {
  key: string
  label: string
  score: number
}

defineProps<{
  competencies: Competency[]
}>()

const getScoreColor = (score: number) => {
  if (score >= 80) return '#10b981'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

// 🟢 P0优化：等级标签
const getCompetencyLevelLabel = (score: number): string => {
  if (score >= 85) return '优秀'
  if (score >= 75) return '良好'
  if (score >= 60) return '一般'
  return '待提升'
}

const getCompetencyLevelClass = (score: number): string => {
  if (score >= 85) return 'level-excellent'
  if (score >= 75) return 'level-good'
  if (score >= 60) return 'level-fair'
  return 'level-poor'
}
</script>

<template>
  <div class="competency-list">
    <div v-for="comp in competencies" :key="comp.key" class="competency-row">
      <div class="comp-header">
        <span class="comp-label">{{ comp.label }}</span>
        <div class="comp-score-group">
          <span class="comp-score" :style="{ color: getScoreColor(comp.score) }">
            {{ comp.score }}
          </span>
          <!-- 🟢 P0优化：等级标签 -->
          <span 
            class="comp-level-tag"
            :class="getCompetencyLevelClass(comp.score)"
          >
            {{ getCompetencyLevelLabel(comp.score) }}
          </span>
        </div>
      </div>
      <div class="progress-track">
        <div
          class="progress-bar"
          :style="{
            width: comp.score + '%',
            background: `linear-gradient(90deg, ${getScoreColor(comp.score)}dd, ${getScoreColor(comp.score)})`,
          }"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped src="./styles/competency-list.css"></style>

