<script setup lang="ts">
interface Competency {
  key: string
  label: string
  score: number
}

defineProps<{
  topCompetencies: Competency[]
  bottomCompetencies: Competency[]
}>()
</script>

<template>
  <div class="competency-summary">
    <!-- 核心优势 -->
    <div v-if="topCompetencies.length > 0" class="comp-strength">
      <h4><i class="ri-trophy-line"></i> 核心优势</h4>
      <div class="comp-tags">
        <span 
          v-for="comp in topCompetencies" 
          :key="comp.key"
          class="comp-tag strength-tag"
        >
          {{ comp.label }} <strong>{{ comp.score }}</strong>
        </span>
      </div>
    </div>
    
    <!-- 提升空间 -->
    <div v-if="bottomCompetencies.length > 0" class="comp-weakness">
      <h4><i class="ri-focus-line"></i> 提升空间</h4>
      <div class="comp-tags">
        <span 
          v-for="comp in bottomCompetencies" 
          :key="comp.key"
          class="comp-tag weakness-tag"
        >
          {{ comp.label }} <strong>{{ comp.score }}</strong>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped src="./styles/competency-summary.css"></style>

