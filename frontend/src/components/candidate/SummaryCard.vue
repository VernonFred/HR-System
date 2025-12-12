<script setup lang="ts">
defineProps<{
  aiAnalysisText: string | string[]
  isFallback?: boolean  // 🟢 P1-2: 是否为降级分析
  fallbackReason?: string  // 🟢 P1-2: 降级原因
}>()

defineEmits<{
  'retry-ai': []  // 🟢 P1-2: 重新生成AI分析
}>()

const getSummaryParagraphs = (text: string | string[] | undefined): string[] => {
  if (!text) return []
  if (Array.isArray(text)) return text.filter(p => p && p.trim())
  return text.split('\n\n').filter(p => p && p.trim()).map(p => p.trim())
}
</script>

<template>
  <div class="summary-card-featured">
    <div class="summary-header-fresh">
      <div class="summary-icon-fresh">
        <i class="ri-file-text-line"></i>
      </div>
      <div class="summary-title-group">
        <h3>综合评价</h3>
        <p class="summary-subtitle">AI-POWERED COMPREHENSIVE EVALUATION</p>
      </div>
      <div class="summary-actions">
        <!-- 🟢 P1-2: 根据分析方式显示不同徽章 -->
        <span v-if="!isFallback" class="ai-badge-fresh">
          <i class="ri-sparkling-2-line"></i>
          AI 分析
        </span>
        <span v-else class="fallback-badge">
          <i class="ri-tools-line"></i>
          规则分析
        </span>
      </div>
    </div>
    
    <!-- 🟢 P1-2: 降级提示横幅 -->
    <div v-if="isFallback" class="fallback-notice">
      <div class="notice-icon">
        <i class="ri-information-line"></i>
      </div>
      <div class="notice-content">
        <p class="notice-title">当前为规则分析结果</p>
        <p class="notice-desc">AI服务暂时不可用，已基于测评数据使用规则算法生成画像</p>
      </div>
      <button class="retry-btn" @click="$emit('retry-ai')">
        <i class="ri-refresh-line"></i>
        重新生成
      </button>
    </div>
    
    <div class="summary-content-sections">
      <div 
        v-for="(paragraph, idx) in getSummaryParagraphs(aiAnalysisText)" 
        :key="idx" 
        class="summary-paragraph"
      >
        <div class="paragraph-indicator">{{ idx + 1 }}</div>
        <p class="paragraph-text">{{ paragraph }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 🎨 综合评价卡片样式 */
.summary-card-featured {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  margin-bottom: 1.25rem;
}

/* 清新白色头部 */
.summary-header-fresh {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.375rem 1.75rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 2px solid #e2e8f0;
  position: relative;
}

.summary-header-fresh::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
}

.summary-icon-fresh {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
}

.summary-icon-fresh i {
  font-size: 1.5rem;
  color: white;
}

.summary-title-group {
  flex: 1;
}

.summary-title-group h3 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
  letter-spacing: -0.01em;
}

.summary-subtitle {
  font-size: 0.6875rem;
  color: #64748b;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.ai-badge-fresh {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.ai-badge-fresh i {
  font-size: 0.875rem;
  animation: sparkle 2s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

.summary-actions {
  margin-left: auto;
}

/* 🟢 P1-2: 降级徽章样式 */
.fallback-badge {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.fallback-badge i {
  font-size: 0.875rem;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 🟢 P1-2: 降级提示横幅 */
.fallback-notice {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.75rem;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-left: 4px solid #f59e0b;
}

.notice-icon {
  width: 40px;
  height: 40px;
  background: #f59e0b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notice-icon i {
  font-size: 1.25rem;
  color: white;
}

.notice-content {
  flex: 1;
}

.notice-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #92400e;
  margin: 0 0 0.25rem 0;
}

.notice-desc {
  font-size: 0.8125rem;
  color: #78350f;
  margin: 0;
  line-height: 1.5;
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  background: #f59e0b;
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.retry-btn:hover {
  background: #d97706;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.retry-btn i {
  font-size: 1rem;
}

/* 🎨 内容区域 - 恢复卡片样式 */
.summary-content-sections {
  padding: 1.5rem 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.summary-paragraph {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.25rem;
  background: #f8fafc;
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
  position: relative;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.summary-paragraph::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.summary-paragraph:hover {
  background: white;
  border-color: #c7d2fe;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
  transform: translateX(2px);
}

.summary-paragraph:hover::before {
  opacity: 1;
}

.paragraph-indicator {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25);
}

.paragraph-text {
  flex: 1;
  color: #475569;
  font-size: 0.9375rem;
  line-height: 1.7;
  margin: 0;
}
</style>

