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

const getEventValue = (event: Event) => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement | null;
  return target?.value || '';
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

<template src="./AssessmentFillPage.template.html"></template>

<style scoped>
@import './styles/assessment-fill-page.css';
</style>
