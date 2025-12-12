<script setup lang="ts">
import { ref } from 'vue'
import CrossValidationPanel from './CrossValidationPanel.vue'

interface ScoreBreakdown {
  assessment: number
  match: number
  completeness: number
  resume: number
}

interface TraitCheck {
  trait: string
  scores: { source: string; value: number }[]
  mean: number
  stdDev: number
  consistency: number
}

interface Contradiction {
  trait: string
  issue: string
}

interface CrossValidationData {
  consistency_score: number
  confidence_level: string
  assessment_count: number
  consistency_checks: TraitCheck[]
  contradictions: Contradiction[]
}

const props = defineProps<{
  visible: boolean
  overallScore: number
  scoreBreakdown?: ScoreBreakdown
  assessmentCount: number
  currentAssessmentType: string
  hasResume: boolean
  crossValidationData?: CrossValidationData
  assessments?: Array<{ type: string; weight: number }>
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// Tab切换状态
const activeTab = ref<'score' | 'validation'>('score')

const closeModal = () => {
  emit('update:visible', false)
  // 关闭时重置为评分构成Tab
  activeTab.value = 'score'
}

const switchTab = (tab: 'score' | 'validation') => {
  activeTab.value = tab
}

// 默认值处理
const breakdown = props.scoreBreakdown || {
  assessment: 80,
  match: 85,
  completeness: 90,
  resume: 0
}
</script>

<template>
  <Transition name="modal">
    <div 
      v-if="visible" 
      class="score-breakdown-overlay"
      @click.self="closeModal"
    >
      <div class="score-breakdown-modal">
        <!-- Header -->
        <div class="modal-header">
          <h3>
            <i class="ri-pie-chart-line"></i>
            综合评分详情
          </h3>
          <button class="close-btn" @click="closeModal">
            <i class="ri-close-line"></i>
          </button>
        </div>
        
        <!-- Tab 切换栏 -->
        <div class="modal-tabs">
          <button 
            class="tab-btn"
            :class="{ active: activeTab === 'score' }"
            @click="switchTab('score')"
          >
            <i class="ri-pie-chart-line"></i>
            评分构成
          </button>
          <button 
            class="tab-btn"
            :class="{ active: activeTab === 'validation' }"
            @click="switchTab('validation')"
          >
            <i class="ri-radar-line"></i>
            交叉验证
          </button>
        </div>
        
        <!-- Body -->
        <div class="modal-body" :class="{ 'validation-body': activeTab === 'validation' }">
          <!-- Tab 1: 评分构成 -->
          <div v-show="activeTab === 'score'" class="tab-content">
            <p class="modal-intro">
              采用AI智能加权算法，多维度精准评估候选人综合能力：
            </p>
            
            <!-- 测评分 -->
          <div class="breakdown-item">
            <div class="item-header">
              <div class="item-icon assessment-icon">
                <i class="ri-bar-chart-fill"></i>
              </div>
              <span class="item-label">测评分</span>
              <span class="item-weight">权重: 40%</span>
            </div>
            <div class="item-progress">
              <div class="progress-bar-simple" :style="{ width: '40%' }"></div>
            </div>
            <div class="item-detail">
              <span class="detail-formula">
                {{ breakdown.assessment }}分 × 0.4 = 
                <strong>{{ (breakdown.assessment * 0.4).toFixed(1) }}</strong>
              </span>
            </div>
            <div class="item-note">
              <!-- 根据实际测评情况动态显示 -->
              <span v-if="assessmentCount === 1" class="note-info">
                单项测评: {{ currentAssessmentType }}
              </span>
              <span v-else-if="assessmentCount === 2" class="note-info">
                已完成2项测评 (加权平均)
              </span>
              <span v-else-if="assessmentCount >= 3" class="note-info">
                已完成3项测评 (加权平均: MBTI 40% · DISC 30% · EPQ 30%)
              </span>
              <span v-else class="note-info">
                暂无测评数据
              </span>
            </div>
          </div>
          
          <!-- 岗位匹配 -->
          <div class="breakdown-item">
            <div class="item-header">
              <div class="item-icon match-icon">
                <i class="ri-focus-3-fill"></i>
              </div>
              <span class="item-label">岗位匹配</span>
              <span class="item-weight">权重: 30%</span>
            </div>
            <div class="item-progress">
              <div class="progress-bar-simple" :style="{ width: '30%' }"></div>
            </div>
            <div class="item-detail">
              <span class="detail-formula">
                {{ breakdown.match }}分 × 0.3 = 
                <strong>{{ (breakdown.match * 0.3).toFixed(1) }}</strong>
              </span>
            </div>
          </div>
          
          <!-- 完整度加成 -->
          <div class="breakdown-item">
            <div class="item-header">
              <div class="item-icon completeness-icon">
                <i class="ri-checkbox-circle-fill"></i>
              </div>
              <span class="item-label">完整度加成</span>
              <span class="item-weight">权重: 15%</span>
            </div>
            <div class="item-progress">
              <div class="progress-bar-simple" :style="{ width: '15%' }"></div>
            </div>
            <div class="item-detail">
              <span class="detail-formula">
                {{ breakdown.completeness }}分 × 0.15 = 
                <strong>{{ (breakdown.completeness * 0.15).toFixed(1) }}</strong>
              </span>
            </div>
            <div class="item-note">
              <span class="note-info">已完成{{ assessmentCount }}项测评</span>
            </div>
          </div>
          
          <!-- 简历质量 -->
          <div class="breakdown-item">
            <div class="item-header">
              <div class="item-icon resume-icon">
                <i class="ri-file-text-fill"></i>
              </div>
              <span class="item-label">简历质量</span>
              <span class="item-weight">权重: 15%</span>
            </div>
            <div class="item-progress">
              <div class="progress-bar-simple" :style="{ width: '15%' }"></div>
            </div>
            <div class="item-detail">
              <span class="detail-formula">
                {{ breakdown.resume }}分 × 0.15 = 
                <strong>{{ (breakdown.resume * 0.15).toFixed(1) }}</strong>
              </span>
            </div>
            <div class="item-note">
              <span class="note-info">{{ hasResume ? '✓ 简历完整' : '✗ 无简历' }}</span>
            </div>
          </div>
          
          <!-- 总分 -->
          <div class="breakdown-total">
            <span class="total-label">综合得分</span>
            <span class="total-value">{{ overallScore }}分</span>
          </div>
          
          <!-- 说明 -->
          <div class="breakdown-note">
            <div class="note-icon">
              <i class="ri-lightbulb-fill"></i>
            </div>
            <div class="note-text">
              <p><strong>AI智能评分算法</strong></p>
              <p>• 多因子加权融合，科学计算综合得分</p>
              <p>• 完成多项测评可提高准确度</p>
              <p>• 上传简历可全面提升评分</p>
            </div>
          </div>
          </div>
          
          <!-- Tab 2: 交叉验证 -->
          <div v-show="activeTab === 'validation'" class="tab-content">
            <CrossValidationPanel
              :validation-data="crossValidationData"
              :assessments="assessments || []"
            />
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped src="./styles/score-breakdown-modal.css"></style>

