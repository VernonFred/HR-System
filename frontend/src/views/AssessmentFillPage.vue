<script setup lang="ts">
import { onMounted, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { submitAnswers } from "../api/assessments";
import CustomAlert from "../components/CustomAlert.vue";

const route = useRoute();
const router = useRouter();

const code = computed(() => route.params.code as string);
const submissionCode = computed(() => route.params.submissionCode as string);

// 测评信息
const assessmentInfo = ref({
  name: "产品经理能力测评",
  questionnaire_type: "CUSTOM",
  total_questions: 0,
  estimated_minutes: 15,
});

// 题目数据
const questions = ref<any[]>([]);
const answers = ref<Record<string, any>>({});
const currentIndex = ref(0);
const loading = ref(false);
const showAnswerCard = ref(false);
const transitioning = ref(false);
const transitionDirection = ref<'next' | 'prev'>('next');

// ⭐ 自定义弹窗状态
const alertConfig = ref({
  show: false,
  title: '提示',
  message: '',
  type: 'warning' as 'info' | 'warning' | 'error' | 'success',
});

const showAlert = (message: string, type: 'info' | 'warning' | 'error' | 'success' = 'warning', title: string = '提示') => {
  alertConfig.value = {
    show: true,
    title,
    message,
    type,
  };
};

const closeAlert = () => {
  alertConfig.value.show = false;
};

// ⭐ 自定义确认弹窗
const confirmConfig = ref({
  show: false,
  title: '确认',
  message: '',
  onConfirm: () => {},
});

const showConfirm = (message: string, title: string = '确认'): Promise<boolean> => {
  return new Promise((resolve) => {
    confirmConfig.value = {
      show: true,
      title,
      message,
      onConfirm: () => {
        confirmConfig.value.show = false;
        resolve(true);
      },
    };
    // 当点击取消或关闭时
    const watchStop = watch(() => confirmConfig.value.show, (newVal) => {
      if (!newVal) {
        watchStop();
        resolve(false);
      }
    });
  });
};

const closeConfirm = () => {
  confirmConfig.value.show = false;
};

const handleConfirmAction = () => {
  confirmConfig.value.onConfirm?.();
};

const currentQuestion = computed(() => questions.value[currentIndex.value]);
const progress = computed(() => {
  if (questions.value.length === 0) return 0;
  const answered = Object.keys(answers.value).length;
  return Math.round((answered / questions.value.length) * 100);
});
const answeredCount = computed(() => Object.keys(answers.value).length);
const isLastQuestion = computed(() => currentIndex.value === questions.value.length - 1);
const canGoNext = computed(() => {
  if (!currentQuestion.value) return false;
  return !!answers.value[currentQuestion.value.id];
});

// ⭐ 从 sessionStorage 加载真实题目数据
const loadQuestions = async () => {
  const storageKey = `assessment_${submissionCode.value}`;
  const storedData = sessionStorage.getItem(storageKey);
  
  if (storedData) {
    try {
      const data = JSON.parse(storedData);
      
      // 更新测评信息
      assessmentInfo.value = {
        name: data.name || "测评",
        questionnaire_type: data.type || "CUSTOM",
        total_questions: data.total_questions || data.questions?.length || 0,
        estimated_minutes: data.estimated_minutes || 15,
      };
      
      // ⭐ 转换后端题目格式为前端格式
      if (data.questions && Array.isArray(data.questions)) {
        questions.value = data.questions.map((q: any, index: number) => {
          // 后端格式: { id, text, options: [{label, text, score}], dimension }
          // 前端格式: { id, type, text, required, options: [{value, label}] }
          
          // 判断题目类型
          let type = "radio"; // 默认单选
          if (q.type) {
            type = q.type;
          } else if (q.options?.length === 2) {
            // 如果只有2个选项，可能是二选一题
            const labels = q.options.map((o: any) => o.label?.toUpperCase());
            if (labels.includes("A") && labels.includes("B")) {
              type = "choice"; // MBTI 二选一
            }
          }
          
          // 转换选项格式
          const options = q.options?.map((opt: any) => {
            // 🔍 处理蛇形命名（allow_custom）和驼峰命名（allowCustom）
            const allowCustomValue = opt.allow_custom ?? opt.allowCustom ?? false;
            
            const option = {
              value: opt.label || opt.value,
              label: opt.text || opt.label,
              score: opt.score,
              allowCustom: allowCustomValue,  // 🟢 保留自定义输入标记
              placeholder: opt.placeholder,  // 🟢 保留占位符
            };
            
            // 🔍 调试：打印"其他"选项
            if (option.label?.includes('其他')) {
              console.log('🔍 转换"其他"选项:', {
                原始: opt,
                转换后: option
              });
            }
            
            return option;
          });
          
          // 🔍 调试：打印选项数据
          if (options && options.some(opt => opt.label?.includes('其他'))) {
            console.log('🔍 发现"其他"选项:', options);
          }
          
          return {
            id: String(q.id),
            type: type,
            text: q.text,
            required: true,
            dimension: q.dimension,
            options: options,
            // MBTI 二选一题的特殊字段
            optionA: q.options?.[0]?.text,
            optionB: q.options?.[1]?.text,
            // 量表题的特殊字段
            scale: q.scale,
            // 文本题的特殊字段
            placeholder: q.placeholder,
            maxLength: q.maxLength,
          };
        });
      }
      
      console.log(`✅ 已加载 ${questions.value.length} 道题目`);
    } catch (e) {
      console.error("解析题目数据失败:", e);
      loadFallbackQuestions();
    }
  } else {
    console.warn("⚠️ 未找到测评数据，使用fallback数据");
    loadFallbackQuestions();
  }
};

// ⭐ Fallback 模拟数据（仅在无真实数据时使用）
const loadFallbackQuestions = () => {
  questions.value = [
    {
      id: "1",
      type: "radio",
      text: "在团队协作中，你更倾向于哪种角色？",
      required: true,
      options: [
        { value: "A", label: "领导者 - 喜欢主导方向和决策" },
        { value: "B", label: "协调者 - 善于沟通和调解" },
        { value: "C", label: "执行者 - 专注于完成任务" },
        { value: "D", label: "创新者 - 喜欢提出新想法" },
      ],
    },
    {
      id: "2",
      type: "yesno",
      text: "你是否喜欢周围热闹？",
      required: true,
      dimension: "E",
    },
    {
      id: "3",
      type: "choice",
      text: "在聚会上，你通常：",
      required: true,
      dimension: "EI",
      optionA: "与很多人交流，享受社交",
      optionB: "只与少数熟人交流",
    },
  ];
  assessmentInfo.value.total_questions = questions.value.length;
};

// 选择选项（单选）
const selectOption = (questionId: string, value: string) => {
  answers.value[questionId] = value;
  // 自动跳转下一题
  if (!isLastQuestion.value) {
    setTimeout(() => nextQuestion(), 300);
  }
};

// 切换多选选项
const toggleCheckbox = (questionId: string, value: string) => {
  if (!answers.value[questionId]) {
    answers.value[questionId] = [];
  }
  const arr = answers.value[questionId] as string[];
  const idx = arr.indexOf(value);
  if (idx > -1) {
    arr.splice(idx, 1);
  } else {
    arr.push(value);
  }
};

// 选择量表
const selectScale = (questionId: string, value: number) => {
  answers.value[questionId] = value;
  // 自动跳转下一题（与单选题保持一致）
  if (!isLastQuestion.value) {
    setTimeout(() => nextQuestion(), 300);
  }
};

// 更新文本
const updateText = (questionId: string, value: string) => {
  answers.value[questionId] = value;
};

// 下一题
const nextQuestion = () => {
  // ⭐ 检查当前题是否为必答且未完成
  if (currentQuestion.value?.required && !answers.value[currentQuestion.value.id]) {
    showAlert('请先完成当前必答题再继续', 'warning', '必答题提醒');
    return;
  }
  
  if (currentIndex.value < questions.value.length - 1) {
    transitionDirection.value = 'next';
    transitioning.value = true;
    setTimeout(() => {
    currentIndex.value++;
      transitioning.value = false;
    }, 150);
  }
};

// 上一题
const prevQuestion = () => {
  if (currentIndex.value > 0) {
    transitionDirection.value = 'prev';
    transitioning.value = true;
    setTimeout(() => {
    currentIndex.value--;
      transitioning.value = false;
    }, 150);
  }
};

// 跳转到指定题目
const goToQuestion = (index: number) => {
  if (index !== currentIndex.value) {
    // ⭐ 检查当前题是否为必答且未完成
    if (currentQuestion.value?.required && !answers.value[currentQuestion.value.id]) {
      showAlert('请先完成当前必答题再跳转', 'warning', '必答题提醒');
      return;
    }
    
    transitionDirection.value = index > currentIndex.value ? 'next' : 'prev';
    transitioning.value = true;
    setTimeout(() => {
  currentIndex.value = index;
      transitioning.value = false;
      showAnswerCard.value = false;
    }, 150);
  }
};

// 提交
const handleSubmit = async () => {
  const unanswered = questions.value.filter(q => q.required && !answers.value[q.id]);
  if (unanswered.length > 0) {
    // ⭐ 必答题必须完成，不允许跳过
    showAlert(`请先完成所有必答题（还有 ${unanswered.length} 道未完成）`, 'warning', '无法提交');
      return;
  }

  try {
    loading.value = true;
    await submitAnswers(submissionCode.value, answers.value);
    router.push(`/assessment/${code.value}/success/${submissionCode.value}`);
  } catch (error: any) {
    console.error("提交失败:", error);
    // ⭐ 使用自定义提示弹窗替代原生alert
    showAlert(error.message || "提交失败，请重试", 'error', '提交失败');
  } finally {
    loading.value = false;
  }
};

// 检查题目是否已回答
const isAnswered = (questionId: string) => {
  const answer = answers.value[questionId];
  if (Array.isArray(answer)) return answer.length > 0;
  return !!answer;
};

onMounted(() => {
  loadQuestions();
});
</script>

<template>
  <div class="assessment-fill">
    <!-- 顶部导航栏 -->
    <header class="fill-header">
      <div class="header-content">
        <div class="header-left">
          <div class="logo">
            <i class="ri-file-list-3-line"></i>
          </div>
          <div class="assessment-title">
            <h1>{{ assessmentInfo.name }}</h1>
            <span class="assessment-meta">
              共 {{ assessmentInfo.total_questions }} 题 · 预计 {{ assessmentInfo.estimated_minutes }} 分钟
            </span>
          </div>
        </div>
        <button class="btn-answer-card" @click="showAnswerCard = !showAnswerCard">
          <i class="ri-layout-grid-line"></i>
          <span class="answer-card-badge" v-if="answeredCount > 0">{{ answeredCount }}</span>
        </button>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-wrapper">
      <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }">
            <div class="progress-glow"></div>
      </div>
    </div>
        <div class="progress-info">
          <span class="progress-current">{{ currentIndex + 1 }}/{{ questions.length }}</span>
          <span class="progress-percent">{{ progress }}%</span>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="fill-main">
      <div class="question-container">
        <!-- 题目卡片 -->
        <div 
          class="question-card"
          :class="{ 
            'slide-out-left': transitioning && transitionDirection === 'next',
            'slide-out-right': transitioning && transitionDirection === 'prev',
          }"
        >
          <template v-if="currentQuestion">
            <!-- 题目头部 -->
            <div class="question-header">
              <div class="question-number-badge">
                <span class="q-num">{{ currentIndex + 1 }}</span>
                <span class="q-total">/ {{ questions.length }}</span>
              </div>
              <div class="question-tags">
                <span v-if="currentQuestion.required" class="tag tag-required">必答</span>
                <span class="tag tag-type" :class="{ 'tag-personality': currentQuestion.type === 'yesno' || currentQuestion.type === 'choice' }">
                  {{ currentQuestion.type === 'radio' ? '单选' : 
                     currentQuestion.type === 'checkbox' ? '多选' : 
                     currentQuestion.type === 'scale' ? '量表' : 
                     currentQuestion.type === 'text' ? '文本' :
                     currentQuestion.type === 'yesno' ? '是非题' : 
                     currentQuestion.type === 'choice' ? '二选一' : '题目' }}
                </span>
              </div>
            </div>

            <!-- 题目内容 -->
            <div class="question-body">
              <h2 class="question-text">{{ currentQuestion.text }}</h2>

              <!-- 单选题 -->
              <div v-if="currentQuestion.type === 'radio'" class="options-grid">
                <div 
                  v-for="(option, idx) in currentQuestion.options"
                  :key="option.value"
                  class="option-wrapper"
                >
                  <button
                    class="option-card"
                    :class="{ selected: answers[currentQuestion.id] === option.value }"
                    @click="selectOption(currentQuestion.id, option.value)"
                  >
                    <span class="option-indicator">
                      <span class="indicator-inner"></span>
                    </span>
                    <span class="option-content">
                      <span class="option-label">{{ option.label }}</span>
                    </span>
                    <i v-if="answers[currentQuestion.id] === option.value" class="ri-check-line option-check"></i>
                  </button>
                  <!-- 🟢 自定义输入框（当选项允许自定义且被选中时显示） -->
                  <!-- 🔍 调试信息 -->
                  <!-- allowCustom: {{ option.allowCustom }}, selected: {{ answers[currentQuestion.id] === option.value }} -->
                  <input 
                    v-if="option.allowCustom === true && answers[currentQuestion.id] === option.value"
                    type="text"
                    class="custom-input-field"
                    :placeholder="option.placeholder || '请填写具体内容...'"
                    :value="answers[`${currentQuestion.id}_custom`] || ''"
                    @input="updateText(`${currentQuestion.id}_custom`, ($event.target as HTMLInputElement).value)"
                    @click.stop
                  />
                </div>
              </div>

              <!-- 多选题 -->
              <div v-else-if="currentQuestion.type === 'checkbox'" class="options-grid checkbox-grid">
                <div
                  v-for="option in currentQuestion.options"
                  :key="option.value"
                  class="option-wrapper"
                >
                  <button
                    class="option-card checkbox-card"
                    :class="{ selected: (answers[currentQuestion.id] || []).includes(option.value) }"
                    @click="toggleCheckbox(currentQuestion.id, option.value)"
                  >
                    <span class="checkbox-indicator">
                      <i class="ri-check-line"></i>
                    </span>
                    <span class="option-content">
                      <span class="option-label">{{ option.label }}</span>
                    </span>
                  </button>
                  <!-- 🟢 自定义输入框（当选项允许自定义且被选中时显示） -->
                  <input 
                    v-if="option.allowCustom === true && (answers[currentQuestion.id] || []).includes(option.value)"
                    type="text"
                    class="custom-input-field"
                    :placeholder="option.placeholder || '请填写具体内容...'"
                    :value="answers[`${currentQuestion.id}_custom_${option.value}`] || ''"
                    @input="updateText(`${currentQuestion.id}_custom_${option.value}`, ($event.target as HTMLInputElement).value)"
                    @click.stop
                  />
                </div>
              </div>

              <!-- 量表题 -->
              <div v-else-if="currentQuestion.type === 'scale'" class="scale-container">
                <div class="scale-labels">
                  <span class="scale-label-min">{{ currentQuestion.scale?.minLabel || '最低' }}</span>
                  <span class="scale-label-max">{{ currentQuestion.scale?.maxLabel || '最高' }}</span>
          </div>
                <div class="scale-buttons">
                  <button
                    v-for="n in (currentQuestion.scale?.max || 5)"
                    :key="n"
                    class="scale-btn"
                    :class="{ 
                      selected: answers[currentQuestion.id] === n,
                      'before-selected': answers[currentQuestion.id] && n < answers[currentQuestion.id]
                    }"
                    @click="selectScale(currentQuestion.id, n)"
                  >
                    {{ n }}
                  </button>
                </div>
                <div class="scale-value" v-if="answers[currentQuestion.id]">
                  当前选择：<strong>{{ answers[currentQuestion.id] }}</strong> 分
        </div>
      </div>

              <!-- 单行文本题 -->
              <div v-else-if="currentQuestion.type === 'text'" class="text-container">
                <input
                  type="text"
                  class="text-input single-line"
                  :placeholder="currentQuestion.placeholder || '请输入你的回答...'"
                  :maxlength="currentQuestion.maxLength || 200"
                  :value="answers[currentQuestion.id] || ''"
                  @input="updateText(currentQuestion.id, ($event.target as HTMLInputElement).value)"
                />
                <div class="text-counter">
                  {{ (answers[currentQuestion.id] || '').length }} / {{ currentQuestion.maxLength || 200 }}
                </div>
              </div>

              <!-- 多行文本题 -->
              <div v-else-if="currentQuestion.type === 'textarea'" class="text-container">
                <textarea
                  class="text-input multi-line"
                  :placeholder="currentQuestion.placeholder || '请输入你的详细回答...'"
                  :maxlength="currentQuestion.maxLength || 500"
                  :value="answers[currentQuestion.id] || ''"
                  @input="updateText(currentQuestion.id, ($event.target as HTMLTextAreaElement).value)"
                  rows="5"
                ></textarea>
                <div class="text-counter">
                  {{ (answers[currentQuestion.id] || '').length }} / {{ currentQuestion.maxLength || 500 }}
                </div>
        </div>

              <!-- 是/否题 (EPQ/DISC人格测试) -->
              <div v-else-if="currentQuestion.type === 'yesno'" class="yesno-container">
                <div class="yesno-buttons">
                  <button
                    class="yesno-btn yes-btn"
                    :class="{ selected: answers[currentQuestion.id] === 'yes' }"
                    @click="selectOption(currentQuestion.id, 'yes')"
                  >
                    <i class="ri-check-line"></i>
                    <span>是</span>
                  </button>
                  <button
                    class="yesno-btn no-btn"
                    :class="{ selected: answers[currentQuestion.id] === 'no' }"
                    @click="selectOption(currentQuestion.id, 'no')"
                  >
                    <i class="ri-close-line"></i>
                    <span>否</span>
                  </button>
                </div>
              </div>

              <!-- 二选一题 (MBTI人格测试) -->
              <div v-else-if="currentQuestion.type === 'choice'" class="choice-container">
                <div class="choice-options">
            <button
                    class="choice-card choice-a"
                    :class="{ selected: answers[currentQuestion.id] === 'A' }"
                    @click="selectOption(currentQuestion.id, 'A')"
            >
                    <span class="choice-letter">A</span>
                    <span class="choice-text">{{ currentQuestion.optionA }}</span>
                    <i v-if="answers[currentQuestion.id] === 'A'" class="ri-check-double-line choice-check"></i>
            </button>
                  <div class="choice-divider">
                    <span class="or-text">或</span>
          </div>
                  <button
                    class="choice-card choice-b"
                    :class="{ selected: answers[currentQuestion.id] === 'B' }"
                    @click="selectOption(currentQuestion.id, 'B')"
                  >
                    <span class="choice-letter">B</span>
                    <span class="choice-text">{{ currentQuestion.optionB }}</span>
                    <i v-if="answers[currentQuestion.id] === 'B'" class="ri-check-double-line choice-check"></i>
                  </button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 底部导航 -->
        <div class="question-nav">
          <button
            class="nav-btn btn-prev"
            @click="prevQuestion"
            :disabled="currentIndex === 0"
          >
            <i class="ri-arrow-left-line"></i>
            <span>上一题</span>
          </button>

          <div class="nav-dots">
            <span 
              v-for="(q, idx) in questions.slice(
                Math.max(0, currentIndex - 2), 
                Math.min(questions.length, currentIndex + 3)
              )" 
              :key="q.id"
              class="nav-dot"
              :class="{ 
                active: questions.indexOf(q) === currentIndex,
                answered: isAnswered(q.id)
              }"
              @click="goToQuestion(questions.indexOf(q))"
            ></span>
          </div>

          <button
            v-if="!isLastQuestion"
            class="nav-btn btn-next"
            @click="nextQuestion"
            :disabled="!canGoNext"
          >
            <span>下一题</span>
            <i class="ri-arrow-right-line"></i>
          </button>

          <button
            v-else
            class="nav-btn btn-submit"
            @click="handleSubmit"
            :disabled="loading"
          >
            <i v-if="loading" class="ri-loader-4-line animate-spin"></i>
            <i v-else class="ri-send-plane-fill"></i>
            <span>{{ loading ? '提交中...' : '提交答卷' }}</span>
          </button>
        </div>
      </div>
    </main>

    <!-- 答题卡侧边栏 -->
    <div class="answer-card-overlay" :class="{ show: showAnswerCard }" @click="showAnswerCard = false">
      <div class="answer-card-panel" @click.stop>
        <div class="panel-header">
          <h3><i class="ri-layout-grid-line"></i> 答题卡</h3>
          <button class="btn-close-panel" @click="showAnswerCard = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="panel-body">
          <div class="answer-grid">
            <button
              v-for="(q, index) in questions"
              :key="q.id"
              class="answer-num"
              :class="{ 
                answered: isAnswered(q.id),
                current: index === currentIndex,
                required: q.required && !isAnswered(q.id)
              }"
              @click="goToQuestion(index)"
            >
              {{ index + 1 }}
            </button>
          </div>
          <div class="answer-legend">
            <div class="legend-item">
              <span class="legend-dot answered"></span>
              <span>已答 ({{ answeredCount }})</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot required"></span>
              <span>必答未完成</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot"></span>
              <span>未答</span>
            </div>
          </div>
        </div>
        <div class="panel-footer">
          <button class="btn-submit-panel" @click="handleSubmit" :disabled="loading">
            <i class="ri-send-plane-fill"></i>
            提交答卷
          </button>
        </div>
      </div>
    </div>

    <!-- ⭐ 自定义弹窗 -->
    <CustomAlert
      :show="alertConfig.show"
      :title="alertConfig.title"
      :message="alertConfig.message"
      :type="alertConfig.type"
      @close="closeAlert"
    />
    
    <!-- ⭐ 自定义确认弹窗 -->
    <Teleport to="body">
      <Transition name="confirm-fade">
        <div v-if="confirmConfig.show" class="confirm-overlay" @click="closeConfirm">
          <div class="confirm-box" @click.stop>
            <div class="confirm-icon">
              <i class="ri-question-line"></i>
            </div>
            <h3 class="confirm-title">{{ confirmConfig.title }}</h3>
            <p class="confirm-message">{{ confirmConfig.message }}</p>
            <div class="confirm-actions">
              <button class="btn-cancel" @click="closeConfirm">取消</button>
              <button class="btn-ok" @click="handleConfirmAction">确定</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* 基础样式 */
.assessment-fill {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea08 0%, #764ba210 50%, #f093fb08 100%);
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.fill-header {
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
}

.assessment-title h1 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.assessment-meta {
  font-size: 0.8125rem;
  color: #6b7280;
}

.btn-answer-card {
  position: relative;
  width: 44px;
  height: 44px;
  background: #f3f4f6;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: #6b7280;
  transition: all 0.2s;
}

.btn-answer-card:hover {
  background: #e5e7eb;
  color: #7c3aed;
}

.answer-card-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: white;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

/* 进度条 */
.progress-wrapper {
  padding: 0 2rem 1rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c3aed, #a855f7, #ec4899);
  border-radius: 3px;
  transition: width 0.4s ease;
  position: relative;
}

.progress-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.4) 50%,
    transparent 100%
  );
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.progress-current {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  min-width: 60px;
  text-align: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.progress-percent {
  font-size: 0.875rem;
  font-weight: 600;
  color: #7c3aed;
}

/* 主内容 */
.fill-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.question-container {
  width: 100%;
  max-width: 720px;
}

/* 题目卡片 */
.question-card {
  background: white;
  border-radius: 24px;
  padding: 2.5rem;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  transition: all 0.15s ease;
}

.question-card.slide-out-left {
  opacity: 0;
  transform: translateX(-20px);
}

.question-card.slide-out-right {
  opacity: 0;
  transform: translateX(20px);
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.question-number-badge {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.q-num {
  font-size: 2rem;
  font-weight: 700;
  color: #7c3aed;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  letter-spacing: -0.02em;
}

.q-total {
  font-size: 1rem;
  color: #9ca3af;
  font-weight: 500;
}

.question-tags {
  display: flex;
  gap: 0.5rem;
}

.tag {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
}

.tag-required {
  background: #fee2e2;
  color: #dc2626;
}

.tag-type {
  background: #f3f4f6;
  color: #6b7280;
}

.question-body {
  min-height: 300px;
}

.question-text {
  font-size: 1.375rem;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.6;
  margin: 0 0 2rem;
}

/* 单选题选项 */
.options-grid {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.125rem 1.25rem;
  background: #fafafa;
  border: 2px solid transparent;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  position: relative;
}

.option-card:hover {
  background: #f5f3ff;
  border-color: #e9d5ff;
  transform: translateY(-1px);
}

.option-card.selected {
  background: linear-gradient(135deg, #f5f3ff 0%, #fdf4ff 100%);
  border-color: #7c3aed;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
}

.option-indicator {
  width: 22px;
  height: 22px;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.option-card.selected .option-indicator {
  border-color: #7c3aed;
  background: #7c3aed;
}

.indicator-inner {
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  opacity: 0;
  transform: scale(0);
  transition: all 0.2s;
}

.option-card.selected .indicator-inner {
  opacity: 1;
  transform: scale(1);
}

.option-content {
  flex: 1;
}

.option-label {
  font-size: 1rem;
  color: #374151;
  font-weight: 500;
}

.option-card.selected .option-label {
  color: #7c3aed;
}

.option-check {
  font-size: 1.25rem;
  color: #7c3aed;
  animation: checkIn 0.3s ease;
}

@keyframes checkIn {
  0% { opacity: 0; transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

/* 🟢 选项包装器 */
.option-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* 🟢 自定义输入框样式 */
.custom-input-field {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid #e9d5ff;
  border-radius: 10px;
  font-size: 0.9375rem;
  color: #374151;
  background: #fefbff;
  transition: all 0.2s ease;
  animation: slideDown 0.3s ease;
}

.custom-input-field:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.1);
  background: white;
}

.custom-input-field::placeholder {
  color: #9ca3af;
  font-style: italic;
}

@keyframes slideDown {
  0% {
    opacity: 0;
    transform: translateY(-8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 多选题 */
.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.875rem;
}

.checkbox-card {
  padding: 1rem;
}

.checkbox-indicator {
  width: 22px;
  height: 22px;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: transparent;
}

.checkbox-card.selected .checkbox-indicator {
  border-color: #7c3aed;
  background: #7c3aed;
  color: white;
}

/* 量表题 */
.scale-container {
  padding: 1rem 0;
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.scale-label-min,
.scale-label-max {
  font-size: 0.875rem;
  color: #6b7280;
}

.scale-buttons {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.scale-btn {
  width: 56px;
  height: 56px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 14px;
  font-size: 1.25rem;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.scale-btn:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
}

.scale-btn.selected {
  border-color: #7c3aed;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: white;
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
}

.scale-btn.before-selected {
  border-color: #c4b5fd;
  background: #f5f3ff;
  color: #7c3aed;
}

.scale-value {
  text-align: center;
  margin-top: 1.5rem;
  font-size: 0.9375rem;
  color: #6b7280;
}

.scale-value strong {
  color: #7c3aed;
  font-size: 1.125rem;
}

/* 文本题 */
.text-container {
  position: relative;
}

.text-input {
  width: 100%;
  padding: 1.25rem;
  border: 2px solid #e5e7eb;
  border-radius: 14px;
  font-size: 1rem;
  line-height: 1.6;
  transition: all 0.2s;
  font-family: inherit;
  background: white;
}

/* 单行文本 */
.text-input.single-line {
  min-height: auto;
  height: 56px;
  resize: none;
}

/* 多行文本 */
.text-input.multi-line {
  min-height: 180px;
  resize: vertical;
}

.text-input:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.1);
}

.text-input::placeholder {
  color: #9ca3af;
}

.text-counter {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

/* 人格测试标签 */
.tag-personality {
  background: linear-gradient(135deg, #8b5cf6, #d946ef);
  color: white;
}

/* 是/否题 (EPQ/DISC) */
.yesno-container {
  padding: 2rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
}

.yesno-buttons {
  display: flex;
  gap: 2rem;
}

.yesno-btn {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  border: 3px solid #e5e7eb;
  background: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.yesno-btn i {
  font-size: 2.5rem;
  color: #9ca3af;
  transition: all 0.3s;
}

.yesno-btn span {
  font-size: 1.25rem;
  font-weight: 600;
  color: #6b7280;
  transition: all 0.3s;
}

.yesno-btn:hover {
  transform: scale(1.05);
  border-color: #c4b5fd;
}

.yes-btn.selected {
  border-color: #10b981;
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25);
}

.yes-btn.selected i {
  color: #059669;
}

.yes-btn.selected span {
  color: #047857;
}

.no-btn.selected {
  border-color: #f87171;
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  box-shadow: 0 8px 24px rgba(248, 113, 113, 0.25);
}

.no-btn.selected i {
  color: #dc2626;
}

.no-btn.selected span {
  color: #b91c1c;
}

/* 二选一题 (MBTI) */
.choice-container {
  padding: 1rem 0;
}

.choice-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
}

.choice-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  background: #fafafa;
  border: 2px solid transparent;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
  position: relative;
}

.choice-card:hover {
  background: #f5f3ff;
  border-color: #e9d5ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1);
}

.choice-card.selected {
  background: linear-gradient(135deg, #f5f3ff 0%, #fdf4ff 100%);
  border-color: #8b5cf6;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.2);
}

.choice-letter {
  width: 44px;
  height: 44px;
  background: #e5e7eb;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.25rem;
  color: #6b7280;
  flex-shrink: 0;
  transition: all 0.3s;
}

.choice-card.selected .choice-letter {
  background: linear-gradient(135deg, #8b5cf6, #d946ef);
  color: white;
}

.choice-text {
  flex: 1;
  font-size: 1.0625rem;
  color: #374151;
  font-weight: 500;
  line-height: 1.5;
}

.choice-card.selected .choice-text {
  color: #7c3aed;
}

.choice-check {
  font-size: 1.5rem;
  color: #8b5cf6;
  animation: checkIn 0.3s ease;
}

.choice-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0.5rem 0;
}

.or-text {
  position: relative;
  padding: 0.5rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #9ca3af;
  background: linear-gradient(135deg, #f3e8ff, #fce7f3);
  border-radius: 999px;
}

/* 维度提示 */
.dimension-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: linear-gradient(135deg, #f5f3ff, #fdf4ff);
  border-radius: 12px;
  margin-top: 1rem;
}

.hint-label {
  font-size: 0.8125rem;
  color: #6b7280;
}

.hint-value {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #7c3aed;
  padding: 0.25rem 0.75rem;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 底部导航 */
.question-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2rem;
  padding-top: 1.5rem;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border: none;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-prev {
  background: #f3f4f6;
  color: #374151;
}

.btn-prev:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-next {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: white;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
}

.btn-next:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.35);
}

.btn-submit {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35);
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.nav-dots {
  display: flex;
  gap: 0.5rem;
}

.nav-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-dot:hover {
  background: #c4b5fd;
}

.nav-dot.active {
  width: 28px;
  border-radius: 5px;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
}

.nav-dot.answered {
  background: #7c3aed;
}

/* 答题卡侧边栏 */
.answer-card-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 200;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s;
}

.answer-card-overlay.show {
  opacity: 1;
  visibility: visible;
}

.answer-card-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 320px;
  background: white;
  transform: translateX(100%);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
}

.answer-card-overlay.show .answer-card-panel {
  transform: translateX(0);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.panel-header h3 i {
  color: #7c3aed;
}

.btn-close-panel {
  width: 32px;
  height: 32px;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: all 0.2s;
}

.btn-close-panel:hover {
  background: #e5e7eb;
  color: #1f2937;
}

.panel-body {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.answer-num {
  aspect-ratio: 1;
  min-height: 48px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 10px;
  font-weight: 700;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.answer-num:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
  transform: scale(1.05);
}

.answer-num.answered {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: white;
  border-color: #7c3aed;
}

.answer-num.current {
  border-color: #7c3aed;
  border-width: 3px;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.answer-num.required {
  border-color: #fca5a5;
  background: #fef2f2;
  color: #dc2626;
  font-weight: 700;
}

.answer-legend {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}

.legend-dot {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 2px solid #e5e7eb;
  background: white;
}

.legend-dot.answered {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  border-color: #7c3aed;
}

.legend-dot.required {
  background: #fef2f2;
  border-color: #fecaca;
}

.panel-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.btn-submit-panel {
  width: 100%;
  padding: 0.875rem;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn-submit-panel:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.btn-submit-panel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 动画 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    padding: 0.875rem 1rem;
  }

  .logo {
    width: 36px;
    height: 36px;
    font-size: 1.25rem;
  }

  .assessment-title h1 {
    font-size: 1rem;
  }
  
  .progress-wrapper {
    padding: 0 1rem 0.875rem;
  }

  .fill-main {
    padding: 1rem;
    align-items: flex-start;
  }

  .question-card {
    padding: 1.5rem;
    border-radius: 20px;
  }

  .question-text {
    font-size: 1.125rem;
  }

  .checkbox-grid {
    grid-template-columns: 1fr;
  }
  
  .scale-buttons {
    gap: 0.5rem;
  }
  
  .scale-btn {
    width: 48px;
    height: 48px;
    font-size: 1.125rem;
  }

  /* 人格测试移动端适配 */
  .yesno-buttons {
    gap: 1.5rem;
  }
  
  .yesno-btn {
    width: 110px;
    height: 110px;
  }
  
  .yesno-btn i {
    font-size: 2rem;
  }
  
  .yesno-btn span {
    font-size: 1rem;
  }
  
  .choice-card {
    padding: 1.25rem;
  }
  
  .choice-letter {
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }
  
  .choice-text {
    font-size: 0.9375rem;
  }

  .question-nav {
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .nav-dots {
    order: 3;
    width: 100%;
    justify-content: center;
  }
  
  .btn-prev,
  .btn-next,
  .btn-submit {
    flex: 1;
    justify-content: center;
  }
  
  .answer-card-panel {
    width: 100%;
  }
}

/* ⭐ 确认弹窗样式 */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.confirm-box {
  background: white;
  border-radius: 16px;
  padding: 32px 28px;
  max-width: 400px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.confirm-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 32px;
}

.confirm-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px;
}

.confirm-message {
  font-size: 15px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 24px;
}

.confirm-actions {
  display: flex;
  gap: 12px;
}

.btn-cancel {
  flex: 1;
  padding: 12px 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #6b7280;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f3f4f6;
}

.btn-ok {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: white;
  background: #3b82f6;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ok:hover {
  background: #2563eb;
}

/* 确认弹窗动画 */
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.3s;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}
</style>
