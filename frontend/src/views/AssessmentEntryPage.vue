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

const route = useRoute();
const router = useRouter();

const code = computed(() => route.params.code as string);
const assessment = ref<PublicAssessmentInfo | null>(null);
const loading = ref(true);
const error = ref("");

// 候选人信息表单 - 动态字段
const form = ref<Record<string, any>>({});
const formFields = ref<any[]>([]);

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

const loadAssessment = async () => {
  try {
    loading.value = true;
    error.value = "";
    const res = await fetchPublicAssessment(code.value);
    assessment.value = res;

    // ⭐ 动态初始化表单字段
    if (res.form_fields && Array.isArray(res.form_fields)) {
      // 处理字段数据，兼容 id 和 name 两种格式
      formFields.value = res.form_fields
        .filter(f => f.enabled !== false)
        .map(f => ({
          ...f,
          // 优先使用 name，如果没有则使用 id
          name: f.name || f.id,
        }));
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
      formFields.value.forEach(field => {
        form.value[field.name] = "";
      });
    }

    if (res.expired) {
      error.value = "该测评已过期";
    } else if (!res.valid) {
      error.value = "该测评暂未开始";
    }
  } catch (err: any) {
    console.error("加载测评失败:", err);
    error.value = err.message || "测评不存在或已失效";
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

const handleStart = async () => {
  // ⭐ 验证必填字段
  const missingFields = formFields.value.filter(f => f.required && !form.value[f.name]);
  if (missingFields.length > 0) {
    alert(`请填写必填项：${missingFields.map(f => f.label).join("、")}`);
    return;
  }

  // 手机号验证（如果有）
  if (form.value.candidate_phone && !/^1[3-9]\d{9}$/.test(form.value.candidate_phone)) {
    alert("请输入有效的手机号");
    return;
  }

  try {
    loading.value = true;
    
    // ⭐ 先检查是否可以提交
    const checkResult = await checkCanSubmit(
      code.value, 
      form.value.candidate_phone || "",
      form.value.candidate_name || ""
    );
    
    submitCheckResult.value = checkResult;
    
    if (!checkResult.can_submit) {
      // 不能提交，显示原因
      if (checkResult.previous_submissions?.length > 0) {
        showPreviousSubmissions.value = true;
      }
      alert(checkResult.reason);
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
    
    // ⭐ 传入 questionnaire 类型和题目数据，确保 fallback 时能返回正确的题目
    const res = await startAssessment(code.value, {
      ...builtinFields,
      custom_data: customData,
    } as any, assessment.value?.type, assessment.value?.questions);

    // ⭐ 存储测评数据到 sessionStorage，供填写页面使用
    sessionStorage.setItem(`assessment_${res.submission_code}`, JSON.stringify({
      name: assessment.value?.name,
      type: assessment.value?.type,
      questions: res.questions,
      total_questions: res.questions?.length || 0,
      estimated_minutes: assessment.value?.estimated_minutes,
    }));
    
    console.log('[AssessmentEntryPage] Saved to sessionStorage:', {
      submission_code: res.submission_code,
      questions_count: res.questions?.length || 0,
      type: assessment.value?.type
    });

    // 跳转到问卷填写页
    router.push(`/assessment/${code.value}/fill/${res.submission_code}`);
  } catch (err: any) {
    console.error("开始测评失败:", err);
    
    // ⭐ 根据错误类型提供更友好的提示
    let errorMessage = "开始测评失败，请重试";
    
    if (err.message) {
      errorMessage = err.message;
    } else if (err.detail) {
      errorMessage = err.detail;
    } else if (err.response?.status === 403) {
      errorMessage = err.response?.data?.detail || "该测评不允许重复提交或已达到提交次数上限";
    } else if (err.response?.status === 422) {
      errorMessage = "提交的信息格式不正确，请检查后重试";
    } else if (err.response?.status === 404) {
      errorMessage = "测评链接已失效或不存在";
    }
    
    showAlert(errorMessage, 'error', '开始测评失败');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadAssessment();
});
</script>

<template>
  <div class="assessment-entry">
    <div class="entry-container">
      <!-- Logo区域 -->
      <div class="logo-section">
        <div class="logo-icon">
          <i class="ri-file-list-3-fill"></i>
        </div>
        <h1 class="brand-name">TalentLens</h1>
        <p class="brand-tagline">人才初步画像智能工具</p>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-box">
        <i class="ri-loader-4-line animate-spin"></i>
        <p>加载中...</p>
      </div>

      <!-- 错误信息 -->
      <div v-else-if="error" class="error-box">
        <i class="ri-error-warning-line"></i>
        <h2>{{ error }}</h2>
        <p>请联系管理员获取有效的测评链接</p>
      </div>

      <!-- 测评信息 -->
      <div v-else class="assessment-box">
        <div class="assessment-header">
          <div class="assessment-icon">
            <i class="ri-file-text-fill"></i>
          </div>
          <h2 class="assessment-title">{{ assessment?.name }}</h2>
          <div class="assessment-meta">
            <span class="meta-item">
              <i class="ri-file-list-line"></i>
              {{ assessment?.questions_count }} 道题目
            </span>
            <span class="meta-item">
              <i class="ri-time-line"></i>
              约 {{ assessment?.estimated_minutes }} 分钟
            </span>
          </div>
          <p v-if="assessment?.description" class="assessment-desc">
            {{ assessment.description }}
          </p>
          
          <!-- 测评说明 -->
          <div v-if="assessment?.page_texts?.intro_text" class="intro-box">
            <i class="ri-file-info-line"></i>
            <p>{{ assessment.page_texts.intro_text }}</p>
          </div>
          
          <!-- 答题指导 -->
          <div v-if="assessment?.page_texts?.guide_text" class="guide-box">
            <i class="ri-compass-3-line"></i>
            <p>{{ assessment.page_texts.guide_text }}</p>
          </div>
          
          <!-- 隐私声明 -->
          <div v-if="assessment?.page_texts?.privacy_text" class="privacy-box">
            <i class="ri-shield-check-line"></i>
            <p>{{ assessment.page_texts.privacy_text }}</p>
          </div>
        </div>

        <div class="divider"></div>

        <div class="form-section">
          <h3 class="form-title">请填写您的基本信息</h3>

          <!-- ⭐ 动态表单字段 -->
          <div v-for="field in formFields" :key="field.name" class="form-group">
            <label :for="field.name" class="form-label">
              <i :class="getFieldIcon(field)"></i>
              {{ field.label }}
              <span v-if="field.required" class="required">*</span>
            </label>
            
            <!-- 文本输入 -->
            <input
              v-if="field.type === 'text' || field.type === 'tel' || field.type === 'email'"
              :id="field.name"
              :type="field.type"
              v-model="form[field.name]"
              :placeholder="`请输入${field.label}`"
              class="form-input"
              :required="field.required"
            />
            
            <!-- 下拉选择 (性别等) -->
            <select
              v-else-if="field.type === 'select'"
              :id="field.name"
              v-model="form[field.name]"
              class="form-input"
              :required="field.required"
            >
              <option value="">请选择{{ field.label }}</option>
              <!-- ⭐ V51: 兼容两种 options 格式: 字符串数组 或 {value, label} 对象数组 -->
              <option 
                v-for="(opt, idx) in (field.options || [])" 
                :key="idx" 
                :value="typeof opt === 'object' ? opt.value : opt"
              >
                {{ typeof opt === 'object' ? opt.label : opt }}
              </option>
            </select>
            
            <!-- 文本域 -->
            <textarea
              v-else-if="field.type === 'textarea'"
              :id="field.name"
              v-model="form[field.name]"
              :placeholder="`请输入${field.label}`"
              class="form-input"
              rows="3"
              :required="field.required"
            ></textarea>
          </div>

          <button
            class="btn-start"
            @click="handleStart"
            :disabled="loading"
          >
            <i v-if="loading" class="ri-loader-4-line animate-spin"></i>
            <i v-else class="ri-play-circle-fill"></i>
            {{ loading ? "正在启动..." : "开始测评" }}
          </button>

          <div class="tips">
            <i class="ri-information-line"></i>
            <span>请在安静的环境下完成测评，确保网络连接稳定</span>
          </div>
        </div>
      </div>

      <!-- 页脚 -->
      <div class="entry-footer">
        <p>© 2025 TalentLens. All rights reserved.</p>
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
  </div>
</template>

<style scoped>
.assessment-entry {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.entry-container {
  max-width: 600px;
  width: 100%;
}

/* Logo区域 */
.logo-section {
  text-align: center;
  margin-bottom: 2rem;
}

.logo-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  color: white;
  backdrop-filter: blur(10px);
}

.brand-name {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  margin: 0 0 0.5rem;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.brand-tagline {
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  font-size: 1rem;
}

/* 卡片通用样式 */
.loading-box,
.error-box,
.assessment-box {
  background: white;
  border-radius: 24px;
  padding: 2.5rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 加载状态 */
.loading-box {
  text-align: center;
  padding: 4rem 2.5rem;
}

.loading-box i {
  font-size: 3rem;
  color: #667eea;
  margin-bottom: 1rem;
  display: block;
}

.loading-box p {
  margin: 0;
  color: #6b7280;
  font-weight: 600;
}

/* 错误状态 */
.error-box {
  text-align: center;
  padding: 4rem 2.5rem;
}

.error-box i {
  font-size: 4rem;
  color: #ef4444;
  margin-bottom: 1.5rem;
  display: block;
}

.error-box h2 {
  margin: 0 0 1rem;
  color: #1f2937;
  font-size: 1.5rem;
}

.error-box p {
  margin: 0;
  color: #6b7280;
}

/* 测评卡片 */
.assessment-header {
  text-align: center;
}

.assessment-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
}

.assessment-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 1rem;
}

.assessment-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.meta-item i {
  color: #667eea;
}

.assessment-desc {
  color: #6b7280;
  margin: 0;
  line-height: 1.6;
}

/* 测评说明盒子 */
.intro-box {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #ede9fe, #ddd6fe);
  border-radius: 12px;
  text-align: left;
}

.intro-box i {
  color: #7c3aed;
  font-size: 1.25rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.intro-box p {
  margin: 0;
  color: #5b21b6;
  font-size: 0.9rem;
  line-height: 1.6;
}

/* 答题指导盒子 */
.guide-box {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  border-radius: 12px;
  text-align: left;
}

.guide-box i {
  color: #2563eb;
  font-size: 1.25rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.guide-box p {
  margin: 0;
  color: #1d4ed8;
  font-size: 0.9rem;
  line-height: 1.6;
}

/* 隐私声明盒子 */
.privacy-box {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  border-radius: 12px;
  text-align: left;
}

.privacy-box i {
  color: #059669;
  font-size: 1.25rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.privacy-box p {
  margin: 0;
  color: #047857;
  font-size: 0.9rem;
  line-height: 1.6;
}

.divider {
  height: 1px;
  background: linear-gradient(to right, transparent, #e5e7eb, transparent);
  margin: 2rem 0;
}

/* 表单区域 */
.form-section {
  margin-top: 2rem;
}

.form-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.form-label i {
  color: #667eea;
}

.required {
  color: #ef4444;
}

.form-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1.5px solid #d1d5db;
  border-radius: 12px;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.3s;
  background-color: white;
}

.form-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input::placeholder {
  color: #9ca3af;
}

/* ⭐ V51: 修复 select 下拉框样式，与 input 保持一致 */
select.form-input {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M2.5 4.5L6 8l3.5-3.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 1rem center;
  background-size: 12px;
  padding-right: 2.5rem;
  cursor: pointer;
  color: #1f2937;
}

select.form-input:invalid,
select.form-input option[value=""] {
  color: #9ca3af;
}

select.form-input option {
  color: #1f2937;
  padding: 0.5rem;
}

.btn-start {
  width: 100%;
  padding: 1rem 2rem;
  margin-top: 1rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-start:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-start:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.tips {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.tips i {
  color: #667eea;
  font-size: 1.25rem;
  flex-shrink: 0;
}

/* 页脚 */
.entry-footer {
  text-align: center;
  margin-top: 2rem;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
}

.entry-footer p {
  margin: 0;
}

/* 动画 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 响应式 */
@media (max-width: 640px) {
  .assessment-entry {
    padding: 1rem;
  }

  .loading-box,
  .error-box,
  .assessment-box {
    padding: 2rem 1.5rem;
  }

  .assessment-title {
    font-size: 1.5rem;
  }

  .assessment-meta {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>

