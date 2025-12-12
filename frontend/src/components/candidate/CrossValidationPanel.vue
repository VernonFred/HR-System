<script setup lang="ts">
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
  confidence_level: string // "高" | "中" | "低"
  assessment_count: number
  consistency_checks: TraitCheck[]
  contradictions: Contradiction[]
}

const props = defineProps<{
  validationData?: CrossValidationData
  assessments: Array<{ type: string; weight: number }>
}>()

const getStatusClass = (consistency: number) => {
  if (consistency >= 80) return 'status-high'
  if (consistency >= 60) return 'status-medium'
  return 'status-low'
}

const getStatusText = (consistency: number) => {
  if (consistency >= 80) return '✓ 高度一致'
  if (consistency >= 60) return '~ 有差异'
  return '! 需关注'
}

const getScoreClass = (level: string) => {
  if (level === '高') return 'score-high'
  if (level === '中') return 'score-medium'
  return 'score-low'
}

const getScoreIcon = (level: string) => {
  if (level === '高') return 'ri-check-double-line'
  if (level === '中') return 'ri-error-warning-line'
  return 'ri-alert-line'
}

const getRecommendation = () => {
  if (!props.validationData) return ''
  
  const { confidence_level, assessment_count, contradictions } = props.validationData
  const contradictionCount = contradictions.length
  
  if (confidence_level === '高') {
    return `已完成${assessment_count}项测评，结果整体一致性良好，画像可信度高。${contradictionCount === 0 ? '无明显矛盾点。' : `建议关注${contradictionCount}处差异点的实际表现。`}`
  } else if (confidence_level === '中') {
    return `已完成${assessment_count}项测评，存在部分差异。建议结合实际工作表现综合判断，或补充更多测评以提升准确性。`
  } else {
    return `测评结果存在明显矛盾（${contradictionCount}处），建议人工深度面试核实，或重新进行测评以确保准确性。`
  }
}
</script>

<template>
  <div class="cross-validation-panel">
    <div v-if="!validationData || !validationData.assessment_count || validationData.assessment_count < 2" class="empty-state">
      <div class="empty-icon">
        <i class="ri-file-list-3-line"></i>
      </div>
      <p class="empty-title">暂无交叉验证数据</p>
      <p class="empty-desc">候选人需完成至少2项测评才能进行交叉验证分析</p>
    </div>
    
    <template v-else>
      <!-- 一致性得分卡片 -->
      <div class="consistency-score-card" :class="getScoreClass(validationData.confidence_level)">
        <div class="score-icon-wrapper">
          <i :class="getScoreIcon(validationData.confidence_level)"></i>
        </div>
        <div class="score-content">
          <div class="score-value">{{ validationData.consistency_score }}分</div>
          <div class="score-label">一致性得分 ({{ validationData.confidence_level }}置信度)</div>
        </div>
      </div>

      <!-- 已完成测评 -->
      <div class="section">
        <h4 class="section-title">
          <i class="ri-file-list-line"></i>
          已完成测评
        </h4>
        <div class="assessment-badges">
          <span 
            v-for="assessment in assessments" 
            :key="assessment.type" 
            class="assessment-badge"
          >
            <span class="badge-type">{{ assessment.type.toUpperCase() }}</span>
            <span class="badge-weight">权重 {{ assessment.weight }}%</span>
          </span>
        </div>
      </div>

      <!-- 特质一致性检查 -->
      <div v-if="validationData.consistency_checks && validationData.consistency_checks.length > 0" class="section">
        <h4 class="section-title">
          <i class="ri-check-double-line"></i>
          特质一致性检查
        </h4>
        <div class="trait-checks">
          <div 
            v-for="trait in validationData.consistency_checks" 
            :key="trait.trait" 
            class="trait-item"
          >
            <div class="trait-header">
              <span class="trait-name">{{ trait.trait }}</span>
              <span class="trait-status" :class="getStatusClass(trait.consistency)">
                {{ getStatusText(trait.consistency) }}
              </span>
            </div>
            <div class="trait-scores">
              <span 
                v-for="score in trait.scores" 
                :key="score.source" 
                class="score-chip"
              >
                {{ score.source }} {{ score.value }}
              </span>
            </div>
            <div class="trait-stats">
              <span class="stat-item">
                <i class="ri-bar-chart-line"></i>
                平均 {{ trait.mean.toFixed(1) }}
              </span>
              <span class="stat-item">
                <i class="ri-line-chart-line"></i>
                标准差 {{ trait.stdDev.toFixed(1) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 矛盾点提示 -->
      <div v-if="validationData.contradictions && validationData.contradictions.length > 0" class="section contradictions-section">
        <h4 class="section-title">
          <i class="ri-alert-line"></i>
          需关注的差异
        </h4>
        <div class="contradiction-list">
          <div 
            v-for="(contradiction, index) in validationData.contradictions" 
            :key="index" 
            class="contradiction-item"
          >
            <div class="contradiction-trait">{{ contradiction.trait }}</div>
            <div class="contradiction-issue">{{ contradiction.issue }}</div>
          </div>
        </div>
      </div>

      <!-- 综合建议 -->
      <div class="section recommendation-section">
        <h4 class="section-title">
          <i class="ri-lightbulb-line"></i>
          综合建议
        </h4>
        <p class="recommendation-text">{{ getRecommendation() }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.cross-validation-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 0;
}

// 空状态
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  
  .empty-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    
    i {
      font-size: 32px;
      color: #3b82f6;
    }
  }
  
  .empty-title {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 8px 0;
  }
  
  .empty-desc {
    font-size: 13px;
    color: #64748b;
    margin: 0;
    line-height: 1.6;
  }
}

// 一致性得分卡片
.consistency-score-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  border: 2px solid;
  transition: all 0.3s ease;
  
  &.score-high {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.1) 100%);
    border-color: rgba(16, 185, 129, 0.3);
    
    .score-icon-wrapper {
      background: #10b981;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
  }
  
  &.score-medium {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(245, 158, 11, 0.1) 100%);
    border-color: rgba(245, 158, 11, 0.3);
    
    .score-icon-wrapper {
      background: #f59e0b;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }
  }
  
  &.score-low {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(239, 68, 68, 0.1) 100%);
    border-color: rgba(239, 68, 68, 0.3);
    
    .score-icon-wrapper {
      background: #ef4444;
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
    }
  }
  
  .score-icon-wrapper {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    
    i {
      font-size: 28px;
      color: white;
    }
  }
  
  .score-content {
    flex: 1;
    
    .score-value {
      font-size: 32px;
      font-weight: 700;
      color: #0f172a;
      line-height: 1;
      margin-bottom: 6px;
    }
    
    .score-label {
      font-size: 13px;
      color: #64748b;
      font-weight: 500;
    }
  }
}

// 区块样式
.section {
  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 12px 0;
    
    i {
      font-size: 18px;
      color: #3b82f6;
    }
  }
}

// 测评徽章
.assessment-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assessment-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: white;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.05);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
  }
  
  .badge-type {
    font-size: 14px;
    font-weight: 700;
    color: #3b82f6;
    letter-spacing: 0.5px;
  }
  
  .badge-weight {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
  }
}

// 特质检查列表
.trait-checks {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trait-item {
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  transition: all 0.2s ease;
  
  &:hover {
    background: white;
    border-color: #cbd5e1;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  
  .trait-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    
    .trait-name {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
    }
    
    .trait-status {
      font-size: 12px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 6px;
      
      &.status-high {
        color: #10b981;
        background: rgba(16, 185, 129, 0.12);
      }
      
      &.status-medium {
        color: #f59e0b;
        background: rgba(245, 158, 11, 0.12);
      }
      
      &.status-low {
        color: #ef4444;
        background: rgba(239, 68, 68, 0.12);
      }
    }
  }
  
  .trait-scores {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
    
    .score-chip {
      font-size: 12px;
      font-weight: 600;
      color: #3b82f6;
      padding: 5px 10px;
      background: white;
      border: 1px solid #e0f2fe;
      border-radius: 6px;
    }
  }
  
  .trait-stats {
    display: flex;
    gap: 16px;
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      color: #64748b;
      font-weight: 500;
      
      i {
        font-size: 14px;
        color: #94a3b8;
      }
    }
  }
}

// 矛盾点区块
.contradictions-section {
  .section-title i {
    color: #ef4444;
  }
}

.contradiction-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.contradiction-item {
  padding: 12px 14px;
  background: rgba(239, 68, 68, 0.04);
  border-left: 3px solid #ef4444;
  border-radius: 6px;
  
  .contradiction-trait {
    font-size: 13px;
    font-weight: 600;
    color: #ef4444;
    margin-bottom: 6px;
  }
  
  .contradiction-issue {
    font-size: 12px;
    color: #64748b;
    line-height: 1.5;
  }
}

// 综合建议区块
.recommendation-section {
  .section-title i {
    color: #f59e0b;
  }
  
  .recommendation-text {
    font-size: 13px;
    line-height: 1.7;
    color: #475569;
    margin: 0;
    padding: 14px;
    background: rgba(245, 158, 11, 0.05);
    border-left: 3px solid #f59e0b;
    border-radius: 6px;
  }
}
</style>

