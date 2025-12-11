<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRoute } from "vue-router";
import { apiRequest } from "../api/client";

const route = useRoute();
const code = computed(() => route.params.code as string);
const submissionCode = computed(() => route.params.submissionCode as string);

// 动画状态
const showSuccess = ref(false);

// 可配置的文本（从后端获取或使用默认值）
const pageTexts = ref({
  success_title: "测评提交成功！",
  success_message: "感谢您完成本次测评，我们已收到您的答卷。",
  success_tips: "我们将在 1-3 个工作日内完成测评结果分析，届时会通过您留下的联系方式通知您，请保持电话畅通。",
});

// 加载页面配置
const loadPageTexts = async () => {
  try {
    const res = await apiRequest<{ page_texts?: typeof pageTexts.value }>({
      path: `/api/public/assessment/${code.value}`,
      fallback: {},
      auth: false,
    });
    if (res.page_texts) {
      pageTexts.value = {
        success_title: res.page_texts.success_title || pageTexts.value.success_title,
        success_message: res.page_texts.success_message || pageTexts.value.success_message,
        success_tips: res.page_texts.success_tips || pageTexts.value.success_tips,
      };
    }
  } catch (e) {
    // 使用默认值
    console.log("使用默认页面文本");
  }
};

onMounted(() => {
  loadPageTexts();
  
  // 延迟显示成功动画
  setTimeout(() => {
    showSuccess.value = true;
  }, 300);
});
</script>

<template>
  <div class="assessment-success">
    <div class="success-container">
      <!-- 成功动画 -->
      <div :class="['success-icon', { show: showSuccess }]">
        <div class="circle-bg"></div>
        <i class="ri-checkbox-circle-fill"></i>
      </div>

      <!-- 成功信息 -->
      <div class="success-content">
        <h1 class="success-title">{{ pageTexts.success_title }}</h1>
        <p class="success-desc">
          {{ pageTexts.success_message }}
        </p>

        <div class="info-box">
          <div class="info-item">
            <i class="ri-file-list-line"></i>
            <div>
              <div class="info-label">提交编号</div>
              <div class="info-value">{{ submissionCode }}</div>
            </div>
          </div>
          <div class="info-item">
            <i class="ri-time-line"></i>
            <div>
              <div class="info-label">提交时间</div>
              <div class="info-value">{{ new Date().toLocaleString() }}</div>
            </div>
          </div>
        </div>

        <div class="tips-box">
          <i class="ri-information-line"></i>
          <div>
            <p class="tips-title">接下来</p>
            <p class="tips-content">{{ pageTexts.success_tips }}</p>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.assessment-success {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  position: relative;
  overflow: hidden;
}

/* 流沙动态背景 */
.assessment-success::before {
  content: '';
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 40% 20%, rgba(255, 255, 255, 0.06) 0%, transparent 50%),
    radial-gradient(circle at 90% 30%, rgba(255, 255, 255, 0.05) 0%, transparent 50%);
  animation: flowingSand 20s ease-in-out infinite;
  opacity: 0.6;
}

@keyframes flowingSand {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(2%, -2%) scale(1.05);
  }
  50% {
    transform: translate(-2%, 2%) scale(1);
  }
  75% {
    transform: translate(2%, 1%) scale(1.02);
  }
}

.success-container {
  max-width: 600px;
  width: 100%;
  background: white;
  border-radius: 24px;
  padding: 3rem 2.5rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  position: relative;
  z-index: 1;
}

/* 成功图标 */
.success-icon {
  width: 120px;
  height: 120px;
  margin: 0 auto 2rem;
  position: relative;
  opacity: 0;
  transform: scale(0);
  transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.success-icon.show {
  opacity: 1;
  transform: scale(1);
}

.circle-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.success-icon i {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 5rem;
  color: #10b981;
}

/* 成功内容 */
.success-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 1rem;
}

.success-desc {
  font-size: 1.05rem;
  color: #6b7280;
  margin: 0 0 2rem;
  line-height: 1.6;
}

/* 信息盒子 */
.info-box {
  background: linear-gradient(135deg, #f9fafb, #f3f4f6);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  text-align: left;
}

.info-item > i {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  background: white;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: #667eea;
}

.info-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.info-value {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  font-family: monospace;
}

/* 提示盒子 */
.tips-box {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  display: flex;
  gap: 1rem;
  text-align: left;
}

.tips-box > i {
  font-size: 1.5rem;
  color: #2563eb;
  flex-shrink: 0;
  margin-top: 0.25rem;
}

.tips-title {
  font-weight: 700;
  color: #1e40af;
  margin: 0 0 0.75rem;
  font-size: 1rem;
}

.tips-list {
  margin: 0;
  padding-left: 1.25rem;
  color: #1e40af;
  font-size: 0.9rem;
  line-height: 1.8;
}

.tips-list li {
  margin-bottom: 0.5rem;
}

.tips-list li:last-child {
  margin-bottom: 0;
}

.tips-content {
  margin: 0;
  color: #1e40af;
  font-size: 0.9rem;
  line-height: 1.8;
}


/* 响应式 */
@media (max-width: 640px) {
  .success-container {
    padding: 2.5rem 1.5rem;
  }

  .success-icon {
    width: 100px;
    height: 100px;
  }

  .success-icon i {
    font-size: 4rem;
  }

  .success-title {
    font-size: 1.75rem;
  }

  .success-desc {
    font-size: 1rem;
  }

  .info-box,
  .tips-box {
    padding: 1.25rem;
  }
}
</style>

