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
  name: "问卷答题",
  questionnaire_type: "CUSTOM",
  category: "",
  custom_type: "",
  purpose: "",
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
        name: data.name || "问卷答题",
        questionnaire_type: data.type || "CUSTOM",
        category: data.category || "",
        custom_type: data.custom_type || "",
        purpose: data.purpose || "",
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
@import './styles/assessment-fill-page.css';
</style>
