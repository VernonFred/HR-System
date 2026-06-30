<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchPublicAssessment,
  startAssessment,
  checkCanSubmit,
  type PublicAssessmentInfo,
  type SubmissionStart,
  type SubmitCheckResult,
} from "../api/assessments";
import CustomAlert from "../components/CustomAlert.vue";
import { getAnonymousDeviceId } from "../utils/anonymousDevice";
import {
  formatQuestionnaireSystemMessage,
  getQuestionnaireCopy,
} from "../utils/questionnaireCopy";

const route = useRoute();
const router = useRouter();

const code = computed(() => route.params.code as string);
const assessment = ref<PublicAssessmentInfo | null>(null);
const loading = ref(true);
const error = ref("");

// 候选人信息表单 - 动态字段
const form = ref<Record<string, any>>({});
const formFields = ref<any[]>([]);
const copy = computed(() => getQuestionnaireCopy(assessment.value));

// ⭐ 重复提交检测
const submitCheckResult = ref<SubmitCheckResult | null>(null);
const showPreviousSubmissions = ref(false);

// ⭐ 自定义弹窗状态
const alertConfig = ref({
  show: false,
  title: '提示',
  message: '',
  type: 'warning' as 'info' | 'warning' | 'error' | 'success',
});

const showAlert = (message: string, type: 'info' | 'warning' | 'error' | 'success' = 'error', title: string = '提示') => {
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

const identityFieldNames = new Set(["name", "candidate_name", "phone", "candidate_phone"]);

const normalizeFormFields = (fields: any[], anonymousMode: boolean) => {
  return fields
    .filter(f => f.enabled !== false)
    .map(f => ({
      ...f,
      // 优先使用 name，如果没有则使用 id
      name: f.name || f.id,
    }))
    .filter(f => {
      if (!anonymousMode) return true;
      return !identityFieldNames.has(String(f.name || "").trim());
    });
};

const loadAssessment = async () => {
  try {
    loading.value = true;
    error.value = "";
    const res = await fetchPublicAssessment(code.value);
    assessment.value = res;

    // ⭐ 动态初始化表单字段
    if (res.form_fields && Array.isArray(res.form_fields)) {
      formFields.value = normalizeFormFields(res.form_fields, !!res.anonymous_mode);
      // 初始化表单值
      formFields.value.forEach(field => {
        form.value[field.name] = "";
      });
    } else {
      // 默认字段（兼容旧数据）
      formFields.value = [
        { name: "candidate_name", label: "姓名", type: "text", required: true, icon: "ri-user-line" },
        { name: "candidate_phone", label: "手机号", type: "tel", required: true, icon: "ri-phone-line" },
        { name: "candidate_email", label: "邮箱", type: "email", required: false, icon: "ri-mail-line" },
        { name: "gender", label: "性别", type: "select", required: false, icon: "ri-user-line", options: ["男", "女"] },
        { name: "target_position", label: "应聘岗位", type: "text", required: false, icon: "ri-briefcase-line" },
      ];
      formFields.value = normalizeFormFields(formFields.value, !!res.anonymous_mode);
      formFields.value.forEach(field => {
        form.value[field.name] = "";
      });
    }

    if (res.expired) {
      error.value = copy.value.expiredText;
    } else if (!res.valid) {
      error.value = copy.value.notStartedText;
    }
  } catch (err: any) {
    console.error(copy.value.loadErrorTitle, err);
    error.value = err.message || copy.value.loadErrorFallback;
  } finally {
    loading.value = false;
  }
};

// 获取字段图标
const getFieldIcon = (field: any) => {
  if (field.icon) return field.icon;
  const iconMap: Record<string, string> = {
    candidate_name: "ri-user-line",
    candidate_phone: "ri-phone-line",
    candidate_email: "ri-mail-line",
    gender: "ri-user-line",
    target_position: "ri-briefcase-line",
  };
  return iconMap[field.name] || "ri-input-cursor-move";
};

// ⭐ 获取页面文案（兼容驼峰和蛇形命名）
const getPageText = (key: string): string => {
  const pageTexts = assessment.value?.page_texts;
  if (!pageTexts) return '';
  
  // 驼峰转蛇形
  const snakeKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
  
  // 优先使用驼峰命名，兼容蛇形命名
  return pageTexts[key] || pageTexts[snakeKey] || '';
};

// ⭐ 获取页面开关（兼容驼峰和蛇形命名）
const getPageFlag = (key: string, defaultValue: boolean = true): boolean => {
  const pageTexts = assessment.value?.page_texts;
  if (!pageTexts) return defaultValue;

  const snakeKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
  const value = pageTexts[key] ?? pageTexts[snakeKey];

  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (['false', '0', 'no', '否'].includes(normalized)) return false;
    if (['true', '1', 'yes', '是'].includes(normalized)) return true;
  }

  return defaultValue;
};

const handleStart = async () => {
  // ⭐ 验证必填字段
  const missingFields = formFields.value.filter(f => f.required && !form.value[f.name]);
  if (missingFields.length > 0) {
    alert(`请填写必填项：${missingFields.map(f => f.label).join("、")}`);
    return;
  }

  const candidateName = form.value.candidate_name || form.value.name || "";
  const candidatePhone = form.value.candidate_phone || form.value.phone || "";

  // 手机号验证（如果有）
  if (candidatePhone && !/^1[3-9]\d{9}$/.test(candidatePhone)) {
    alert("请输入有效的手机号");
    return;
  }

  try {
    loading.value = true;
    const anonymousDeviceId = assessment.value?.anonymous_mode ? getAnonymousDeviceId() : undefined;
    
    // ⭐ 先检查是否可以提交
    const checkResult = await checkCanSubmit(code.value, candidatePhone, candidateName, anonymousDeviceId);
    
    submitCheckResult.value = checkResult;
    
    if (!checkResult.can_submit) {
      // 不能提交，显示原因
      if (checkResult.previous_submissions?.length > 0) {
        showPreviousSubmissions.value = true;
      }
      showAlert(
        formatQuestionnaireSystemMessage(checkResult.reason, assessment.value),
        'warning',
        '提示',
      );
      loading.value = false;
      return;
    }
    
    // ⭐ 将 form_fields 中的字段分类提取
    const customData: Record<string, any> = {};
    const builtinFields: Record<string, any> = {};
    
    // ⭐ 字段名映射：form_fields 中的 id/name 到 API 期望的字段名
    const fieldNameMapping: Record<string, string> = {
      'name': 'candidate_name',
      'phone': 'candidate_phone',
      'email': 'candidate_email',
      'candidate_name': 'candidate_name',
      'candidate_phone': 'candidate_phone',
      'candidate_email': 'candidate_email',
      'gender': 'gender',
      'target_position': 'target_position',
    };
    
    // ⭐ 定义关键字段列表（始终提取到顶层）
    const keyFields = ['name', 'phone', 'email', 'candidate_name', 'candidate_phone', 'candidate_email', 'gender', 'target_position'];
    
    formFields.value.forEach(field => {
      const value = form.value[field.name];
      
      // 关键字段始终提取到顶层，并映射字段名
      if (keyFields.includes(field.name)) {
        const apiFieldName = fieldNameMapping[field.name] || field.name;
        builtinFields[apiFieldName] = value;
      } else if (field.builtin) {
        const apiFieldName = fieldNameMapping[field.name] || field.name;
        builtinFields[apiFieldName] = value;
      } else {
        customData[field.name] = value;
      }
    });

    // 没有配置字段时仍保证必备字段存在（允许为空字符串）
    if (!("candidate_name" in builtinFields)) {
      builtinFields.candidate_name = candidateName;
    }
    if (!("candidate_phone" in builtinFields)) {
      builtinFields.candidate_phone = candidatePhone;
    }
    
    // ⭐ 传入 questionnaire 类型和题目数据，确保 fallback 时能返回正确的题目
    const res = await startAssessment(code.value, {
      ...builtinFields,
      custom_data: customData,
      anonymous_device_id: anonymousDeviceId,
    } as any, assessment.value?.type, assessment.value?.questions);

    // ⭐ 存储测评数据到 sessionStorage，供填写页面使用
    sessionStorage.setItem(`assessment_${res.submission_code}`, JSON.stringify({
      name: res.questionnaire_name || assessment.value?.name,
      type: res.questionnaire_type || assessment.value?.type,
      category: res.category ?? assessment.value?.category,
      custom_type: res.custom_type ?? assessment.value?.custom_type,
      purpose: res.purpose ?? assessment.value?.purpose,
      questions: res.questions,
      total_questions: res.questions_count || res.questions?.length || assessment.value?.questions_count || 0,
      estimated_minutes: res.estimated_minutes || assessment.value?.estimated_minutes,
    }));
    
    console.log('[AssessmentEntryPage] Saved to sessionStorage:', {
      submission_code: res.submission_code,
      questions_count: res.questions?.length || 0,
      type: assessment.value?.type
    });

    // 跳转到问卷填写页
    router.push(`/assessment/${code.value}/fill/${res.submission_code}`);
  } catch (err: any) {
    console.error(copy.value.startErrorTitle, err);
    
    // ⭐ 根据错误类型提供更友好的提示
    let errorMessage = copy.value.startErrorFallback;
    
    if (err.message) {
      errorMessage = err.message;
    } else if (err.detail) {
      errorMessage = err.detail;
    } else if (err.response?.status === 403) {
      errorMessage = err.response?.data?.detail || "该链接不允许重复提交或已达到提交次数上限";
    } else if (err.response?.status === 422) {
      errorMessage = "提交的信息格式不正确，请检查后重试";
    } else if (err.response?.status === 404) {
      errorMessage = copy.value.linkMissingText;
    }
    
    showAlert(
      formatQuestionnaireSystemMessage(errorMessage, assessment.value),
      'error',
      copy.value.startErrorTitle,
    );
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadAssessment();
});
</script>

<template src="./AssessmentEntryPage.template.html"></template>

<style scoped>
@import './styles/assessment-entry-page.css';
</style>
