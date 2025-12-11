<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import * as jobProfilesAPI from "@/api/jobProfiles";
import { analyzeResumeForProfile, analyzeMultipleResumesForProfile, analyzeJDForProfile, aiConfigureDimensions } from "@/api/jobProfiles";

interface JobProfile {
  id: number;
  name: string;
  department?: string;
  tags?: string[];
  dimensionCount?: number;
  updatedAt: string;
}

interface Dimension {
  name: string;
  weight: number;
  description: string;
}

interface JobProfileForm {
  name: string;
  department: string;
  tags: string[];
  description: string;
  dimensions: Dimension[];
}

// 状态
const loading = ref(false);
const searchQuery = ref("");
const profiles = ref<JobProfile[]>([]);
const showImportResumeDialog = ref(false);
const showImportJDDialog = ref(false);
const showEditorDialog = ref(false);
const selectedResumes = ref<File[]>([]);
const selectedJD = ref<File | null>(null);
const aiGenerating = ref(false);
const aiConfiguring = ref(false);
const resumeInput = ref<HTMLInputElement | null>(null);
const jdInput = ref<HTMLInputElement | null>(null);
const newTag = ref("");
const isAIGenerated = ref(false);
const isNew = ref(true);
const editingProfileId = ref<number | null>(null);

// 上传进度状态
const uploadProgress = ref(0);
const isUploading = ref(false);

// 确认/提示模态框
const showConfirmDialog = ref(false);
const confirmDialogData = ref({
  title: "",
  message: "",
  type: "info" as "info" | "warning" | "success" | "error",
  onConfirm: () => {},
});

const formData = ref<JobProfileForm>({
  name: "",
  department: "",
  tags: [],
  description: "",
  dimensions: [],
});

// 计算属性
const filteredProfiles = computed(() => {
  if (!searchQuery.value) return profiles.value;
  const query = searchQuery.value.toLowerCase();
  return profiles.value.filter(
    (p) =>
      p.name.toLowerCase().includes(query) ||
      p.department?.toLowerCase().includes(query)
  );
});

const totalWeight = computed(() => {
  return formData.value.dimensions.reduce((sum, dim) => sum + (dim.weight || 0), 0);
});

const isWeightValid = computed(() => {
  return totalWeight.value === 100;
});

const canSave = computed(() => {
  return (
    formData.value.name.trim() !== "" &&
    formData.value.dimensions.length > 0 &&
    isWeightValid.value
  );
});

// 显示提示对话框
const showMessage = (message: string, type: "info" | "warning" | "success" | "error" = "info") => {
  confirmDialogData.value = {
    title: type === "success" ? "成功" : type === "error" ? "错误" : type === "warning" ? "警告" : "提示",
    message,
    type,
    onConfirm: () => {
      showConfirmDialog.value = false;
    },
  };
  showConfirmDialog.value = true;
};

// 显示确认对话框
const showConfirm = (
  message: string,
  onConfirm: () => void,
  title = "确认"
) => {
  confirmDialogData.value = {
    title,
    message,
    type: "warning",
    onConfirm: () => {
      showConfirmDialog.value = false;
      onConfirm();
    },
  };
  showConfirmDialog.value = true;
};

// 方法
const loadProfiles = async () => {
  loading.value = true;
  try {
    // ✅ 调用真实API
    const response = await jobProfilesAPI.getJobProfiles({
      skip: 0,
      limit: 100,
      status: 'active'
    });
    
    // 转换为前端需要的格式
    profiles.value = response.items.map(item => ({
      id: item.id,
      name: item.name,
      department: item.department,
      tags: item.tags,
      dimensionCount: item.dimensions.length,
      updatedAt: new Date(item.updated_at).toLocaleDateString('zh-CN'),
    }));
    
    console.log('✅ 已加载岗位画像:', profiles.value.length, '个');
  } catch (error) {
    console.error("加载岗位画像失败:", error);
    showMessage("加载岗位画像失败，请重试", "error");
    
    // 降级：使用Mock数据
    profiles.value = [
      {
        id: 1,
        name: "产品经理",
        department: "产品部",
        tags: ["ToB", "产品", "中高级"],
        dimensionCount: 8,
        updatedAt: "2025-11-30",
      },
      {
        id: 2,
        name: "软件工程师",
        department: "研发部",
        tags: ["技术", "后端"],
        dimensionCount: 6,
        updatedAt: "2025-11-29",
      },
      {
        id: 3,
        name: "实施工程师",
        department: "交付部",
        tags: ["技术", "客户服务"],
        dimensionCount: 7,
        updatedAt: "2025-11-28",
      },
    ];
  } finally {
    loading.value = false;
  }
};

const createNewProfile = () => {
  isNew.value = true;
  editingProfileId.value = null;
  isAIGenerated.value = false;
  formData.value = {
    name: "",
    department: "",
    tags: [],
    description: "",
    dimensions: [],
  };
  showEditorDialog.value = true;
};

const editProfile = async (profile: JobProfile) => {
  isNew.value = false;
  editingProfileId.value = profile.id;
  isAIGenerated.value = false;

  // ✅ 从API加载完整数据
  try {
    const fullProfile = await jobProfilesAPI.getJobProfile(profile.id);
    formData.value = {
      name: fullProfile.name,
      department: fullProfile.department || "",
      tags: fullProfile.tags || [],
      description: fullProfile.description || "",
      dimensions: fullProfile.dimensions || [],
    };
    showEditorDialog.value = true;
  } catch (error) {
    console.error("加载岗位画像详情失败:", error);
    showMessage("加载岗位画像详情失败", "error");
    
    // 降级：使用列表中的数据
  formData.value = {
    name: profile.name,
    department: profile.department || "",
    tags: profile.tags || [],
    description: "负责产品规划、需求分析、用户研究等工作",
    dimensions: [
      { name: "产品规划能力", weight: 30, description: "负责产品中长期规划" },
      { name: "用户洞察能力", weight: 25, description: "深入理解用户需求" },
      { name: "跨部门沟通能力", weight: 15, description: "协调研发、运营等团队" },
      { name: "数据分析能力", weight: 15, description: "基于数据做决策" },
      { name: "项目管理能力", weight: 15, description: "推动项目按时交付" },
    ],
  };
  showEditorDialog.value = true;
  }
};

const closeEditor = () => {
  showEditorDialog.value = false;
};

const deleteProfile = async (profile: JobProfile) => {
  showConfirm(`确定要删除岗位画像"${profile.name}"吗？`, async () => {
    try {
      // ✅ 调用删除API
      await jobProfilesAPI.deleteJobProfile(profile.id);
      profiles.value = profiles.value.filter((p) => p.id !== profile.id);
      showMessage("删除成功", "success");
    } catch (error) {
      console.error("删除失败:", error);
      showMessage("删除失败，请重试", "error");
    }
  });
};

const deleteCurrentProfile = async () => {
  if (!editingProfileId.value) return;
  const profile = profiles.value.find((p) => p.id === editingProfileId.value);
  if (profile) {
    await deleteProfile(profile);
    closeEditor();
  }
};

const triggerResumeInput = () => {
  resumeInput.value?.click();
};

const handleResumeSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    selectedResumes.value = Array.from(target.files);
  }
};

const removeResume = (idx: number) => {
  selectedResumes.value.splice(idx, 1);
};

const generateFromResumes = async () => {
  if (selectedResumes.value.length === 0 || aiGenerating.value) return;

  aiGenerating.value = true;
  isUploading.value = true;
  uploadProgress.value = 0;
  
  try {
    const files = selectedResumes.value;
    const fileCount = files.length;
    
    // 从第一个文件名提取岗位信息
    const fileName = files[0].name.replace(/\.(pdf|docx?|txt)$/i, '');
    const jobTitle = fileName.split(/[_\-]/)[0] || "未命名岗位";

    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 30) {
        uploadProgress.value += 10;
      }
    }, 200);
    
    uploadProgress.value = 40;
    clearInterval(progressInterval);
    
    // AI分析进度模拟
    const analysisInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 5;
      }
    }, 500);
    
    // 根据简历数量选择API
    let result;
    if (fileCount === 1) {
      // 单份简历使用原有API
      result = await analyzeResumeForProfile(files[0], jobTitle);
    } else {
      // 多份简历使用新API（提取共性特征）
      result = await analyzeMultipleResumesForProfile(files, jobTitle);
    }
    
    clearInterval(analysisInterval);
    uploadProgress.value = 100;
    
    // 使用AI返回的建议
    formData.value = {
      name: result.name,
      department: result.department || "未知部门",
      tags: result.tags || [],
      description: result.description || "",
      dimensions: result.dimensions.map(d => ({
        name: d.name,
        weight: d.weight,
        description: d.description || ""
      }))
    };

    isNew.value = true;
    isAIGenerated.value = true;
    showImportResumeDialog.value = false;
    showEditorDialog.value = true;
    selectedResumes.value = [];
    
    const msg = fileCount > 1 
      ? `AI分析完成，已从${fileCount}份简历中提取共性特征` 
      : "AI分析完成，已生成岗位画像建议";
    showMessage(msg, "success");
  } catch (error) {
    console.error("AI生成失败:", error);
    showMessage(`AI生成失败：${error}`, "error");
  } finally {
    aiGenerating.value = false;
    isUploading.value = false;
    uploadProgress.value = 0;
  }
};

const triggerJDInput = () => {
  jdInput.value?.click();
};

const handleJDSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    selectedJD.value = target.files[0];
  }
};

const generateFromJD = async () => {
  if (!selectedJD.value || aiGenerating.value) return;

  aiGenerating.value = true;
  isUploading.value = true;
  uploadProgress.value = 0;
  
  try {
    // ⭐ Phase 5: 调用真实AI分析API
    const file = selectedJD.value;
    
    // 提取文件名作为岗位名称（去掉扩展名）
    const fileName = file.name.replace(/\.(pdf|docx?|txt)$/i, '');
    const jobTitle = fileName.split(/[_\-]/)[0] || "未命名岗位";
    
    // 模拟上传进度
    uploadProgress.value = 20;
    
    // 读取文件内容
    const jdText = await readFileAsText(file);
    uploadProgress.value = 40;
    
    // AI分析进度模拟
    const analysisInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 5;
      }
    }, 500);
    
    // 调用AI分析API
    const result = await analyzeJDForProfile(jdText, jobTitle);
    
    clearInterval(analysisInterval);
    uploadProgress.value = 100;
    
    // 使用AI返回的建议
    formData.value = {
      name: result.name,
      department: result.department || "未知部门",
      tags: result.tags || [],
      description: result.description || "",
      dimensions: result.dimensions.map(d => ({
        name: d.name,
        weight: d.weight,
        description: d.description || ""
      }))
    };

    isNew.value = true;
    isAIGenerated.value = true;
    showImportJDDialog.value = false;
    showEditorDialog.value = true;
    selectedJD.value = null;
    
    showMessage("AI分析完成，已生成岗位画像建议", "success");
  } catch (error) {
    console.error("AI生成失败:", error);
    showMessage(`AI生成失败：${error}`, "error");
  } finally {
    aiGenerating.value = false;
    isUploading.value = false;
    uploadProgress.value = 0;
  }
};

// 读取文件内容为文本
const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      resolve(text || '');
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsText(file);
  });
};

const addTag = () => {
  if (newTag.value.trim() && !formData.value.tags.includes(newTag.value.trim())) {
    formData.value.tags.push(newTag.value.trim());
    newTag.value = "";
  }
};

const removeTag = (idx: number) => {
  formData.value.tags.splice(idx, 1);
};

const addDimension = () => {
  formData.value.dimensions.push({
    name: "",
    weight: 0,
    description: "",
  });
};

const removeDimension = (idx: number) => {
  formData.value.dimensions.splice(idx, 1);
  validateWeights();
};

const validateWeights = () => {
  // 实时验证权重
};

const aiAutoConfig = async () => {
  if (!formData.value.name || aiConfiguring.value) return;

  aiConfiguring.value = true;
  try {
    // 检查是否已有维度填写
    const hasExistingDimensions = formData.value.dimensions.length > 0 && 
      formData.value.dimensions.some(d => d.name.trim() !== '');
    
    // 调用AI智能配置API
    const result = await aiConfigureDimensions(
      formData.value.name,
      formData.value.description,
      hasExistingDimensions ? formData.value.dimensions : undefined
    );
    
    // 更新维度配置
    formData.value.dimensions = result.dimensions.map(d => ({
      name: d.name,
      weight: d.weight,
      description: d.description || ''
    }));
    
    if (hasExistingDimensions) {
      showMessage(
        `AI已根据岗位特点智能优化了${result.dimensions.length}个能力维度的权重！`,
        "success"
      );
    } else {
      showMessage(
        `AI已为"${formData.value.name}"生成${result.dimensions.length}个能力维度！`,
        "success"
      );
    }
  } catch (error) {
    console.error("AI配置失败:", error);
    showMessage(`AI配置失败：${error}`, "error");
  } finally {
    aiConfiguring.value = false;
  }
};

const saveProfile = async () => {
  if (!canSave.value) return;

  try {
    console.log("保存岗位画像:", formData.value);

    // ✅ 调用保存API
    if (isNew.value) {
      // 创建新画像
      const created = await jobProfilesAPI.createJobProfile({
        name: formData.value.name,
        department: formData.value.department || undefined,
        description: formData.value.description || undefined,
        tags: formData.value.tags,
        dimensions: formData.value.dimensions,
      });
      
      // 添加到列表
      profiles.value.unshift({
        id: created.id,
        name: created.name,
        department: created.department,
        tags: created.tags,
        dimensionCount: created.dimensions.length,
        updatedAt: new Date(created.updated_at).toLocaleDateString('zh-CN'),
      });
      
      showMessage("创建成功！", "success");
    } else {
      // 更新现有画像
      if (!editingProfileId.value) {
        throw new Error('未指定要编辑的画像ID');
      }
      
      const updated = await jobProfilesAPI.updateJobProfile(editingProfileId.value, {
        name: formData.value.name,
        department: formData.value.department || undefined,
        description: formData.value.description || undefined,
        tags: formData.value.tags,
        dimensions: formData.value.dimensions,
      });
      
      // 更新列表中的数据
      const profile = profiles.value.find((p) => p.id === editingProfileId.value);
      if (profile) {
        profile.name = updated.name;
        profile.department = updated.department;
        profile.tags = updated.tags;
        profile.dimensionCount = updated.dimensions.length;
        profile.updatedAt = new Date(updated.updated_at).toLocaleDateString('zh-CN');
    }

      showMessage("更新成功！", "success");
    }

    closeEditor();
  } catch (error) {
    console.error("保存失败:", error);
    showMessage("保存失败，请重试", "error");
  }
};

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString("zh-CN");
};

onMounted(() => {
  loadProfiles();
});
</script>

<template>
  <div class="job-profiles-page">
    <!-- 渐变头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="icon-wrapper">
            <i class="ri-briefcase-line"></i>
          </div>
          <div>
            <h1 class="page-title">岗位能力画像配置</h1>
            <p class="page-subtitle">配置岗位能力维度与权重，用于人员匹配分析</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn-import" @click="showImportResumeDialog = true">
            <i class="ri-file-user-line"></i>
            导入简历
          </button>
          <button class="btn-import" @click="showImportJDDialog = true">
            <i class="ri-file-text-line"></i>
            导入JD
          </button>
          <button class="btn-primary" @click="createNewProfile">
            <i class="ri-add-line"></i>
            创建岗位画像
          </button>
        </div>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-section">
      <div class="search-bar">
        <i class="ri-search-line"></i>
        <input
          v-model="searchQuery"
          type="search"
          placeholder="搜索岗位名称或部门..."
          class="search-input"
        />
      </div>
    </div>

    <!-- 岗位卡片网格 -->
    <div v-if="loading" class="loading-state">
      <i class="ri-loader-4-line animate-spin"></i>
      <p>加载中...</p>
    </div>

    <div v-else-if="filteredProfiles.length === 0" class="empty-state">
      <i class="ri-inbox-line"></i>
      <p>暂无岗位画像</p>
      <button class="btn-primary" @click="createNewProfile">
        <i class="ri-add-line"></i>
        创建岗位画像
      </button>
    </div>

    <div v-else class="profiles-grid">
      <div
        v-for="profile in filteredProfiles"
        :key="profile.id"
        class="profile-card"
        @click="editProfile(profile)"
      >
        <div class="card-header">
          <div class="job-icon">
            <i class="ri-briefcase-line"></i>
          </div>
          <div class="card-actions" @click.stop>
            <button class="action-btn" @click="editProfile(profile)" title="编辑">
              <i class="ri-edit-line"></i>
            </button>
            <button
              class="action-btn delete"
              @click="deleteProfile(profile)"
              title="删除"
            >
              <i class="ri-delete-bin-line"></i>
            </button>
          </div>
        </div>

        <h3 class="job-name">{{ profile.name }}</h3>

        <div class="job-info">
          <div class="info-item">
            <i class="ri-building-line"></i>
            <span>{{ profile.department || "未分配部门" }}</span>
          </div>
          <div class="info-item">
            <i class="ri-stack-line"></i>
            <span>{{ profile.dimensionCount || 0 }} 个能力维度</span>
          </div>
        </div>

        <div class="job-tags" v-if="profile.tags && profile.tags.length > 0">
          <span v-for="tag in profile.tags.slice(0, 3)" :key="tag" class="tag">
            {{ tag }}
          </span>
        </div>

        <div class="card-footer">
          <span class="update-time">
            <i class="ri-time-line"></i>
            {{ formatDate(profile.updatedAt) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 导入简历对话框 -->
    <Transition name="modal">
      <div
        v-if="showImportResumeDialog"
        class="modal-overlay"
        @click.self="showImportResumeDialog = false"
      >
        <div class="modal-dialog import-modal">
          <div class="modal-header">
            <div class="modal-title-wrapper">
              <i class="ri-file-user-line"></i>
              <h2>导入简历生成岗位画像</h2>
            </div>
            <button class="btn-close" @click="showImportResumeDialog = false">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body">
            <div class="import-hint">
              <i class="ri-information-line"></i>
              <p>
                上传1-N份优秀候选人的简历，AI将分析共性特征，自动生成岗位能力画像草稿
              </p>
            </div>
            <div class="upload-area" @click="triggerResumeInput">
              <i class="ri-upload-cloud-line"></i>
              <p>点击上传简历文件</p>
              <span class="upload-hint-text">支持 PDF、Word 格式，可多选</span>
              <input
                ref="resumeInput"
                type="file"
                multiple
                accept=".pdf,.doc,.docx"
                @change="handleResumeSelect"
                style="display: none"
              />
            </div>
            <div v-if="selectedResumes.length > 0" class="file-list">
              <div v-for="(file, idx) in selectedResumes" :key="idx" class="file-item">
                <i class="ri-file-line"></i>
                <span>{{ file.name }}</span>
                <button class="btn-remove" @click="removeResume(idx)" :disabled="aiGenerating">
                  <i class="ri-close-line"></i>
                </button>
              </div>
            </div>
            <!-- 上传/分析进度条 -->
            <div v-if="isUploading" class="upload-progress">
              <div class="progress-info">
                <span class="progress-label">{{ uploadProgress < 40 ? '上传中...' : 'AI分析中...' }}</span>
                <span class="progress-value">{{ uploadProgress }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showImportResumeDialog = false" :disabled="aiGenerating">
              取消
            </button>
            <button
              class="btn-primary"
              @click="generateFromResumes"
              :disabled="selectedResumes.length === 0 || aiGenerating"
            >
              <i v-if="aiGenerating" class="ri-loader-4-line animate-spin"></i>
              <i v-else class="ri-sparkle-line"></i>
              {{ aiGenerating ? "AI分析中..." : "AI生成岗位画像" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 导入JD对话框 -->
    <Transition name="modal">
      <div
        v-if="showImportJDDialog"
        class="modal-overlay"
        @click.self="showImportJDDialog = false"
      >
        <div class="modal-dialog import-modal">
          <div class="modal-header">
            <div class="modal-title-wrapper">
              <i class="ri-file-text-line"></i>
              <h2>导入JD生成岗位画像</h2>
            </div>
            <button class="btn-close" @click="showImportJDDialog = false">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body">
            <div class="import-hint">
              <i class="ri-information-line"></i>
              <p>上传岗位JD文档，AI将自动分析岗位要求，生成岗位能力画像草稿</p>
            </div>
            <div class="upload-area" @click="triggerJDInput">
              <i class="ri-upload-cloud-line"></i>
              <p>点击上传JD文件</p>
              <span class="upload-hint-text">支持 PDF、Word、TXT 格式</span>
              <input
                ref="jdInput"
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                @change="handleJDSelect"
                style="display: none"
              />
            </div>
            <div v-if="selectedJD" class="file-list">
              <div class="file-item">
                <i class="ri-file-text-line"></i>
                <span>{{ selectedJD.name }}</span>
                <button class="btn-remove" @click="selectedJD = null" :disabled="aiGenerating">
                  <i class="ri-close-line"></i>
                </button>
              </div>
            </div>
            <!-- 上传/分析进度条 -->
            <div v-if="isUploading" class="upload-progress">
              <div class="progress-info">
                <span class="progress-label">{{ uploadProgress < 40 ? '读取文件...' : 'AI分析中...' }}</span>
                <span class="progress-value">{{ uploadProgress }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showImportJDDialog = false" :disabled="aiGenerating">
              取消
            </button>
            <button
              class="btn-primary"
              @click="generateFromJD"
              :disabled="!selectedJD || aiGenerating"
            >
              <i v-if="aiGenerating" class="ri-loader-4-line animate-spin"></i>
              <i v-else class="ri-sparkle-line"></i>
              {{ aiGenerating ? "AI分析中..." : "AI生成岗位画像" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 编辑/创建岗位画像弹窗 -->
    <Transition name="modal">
      <div
        v-if="showEditorDialog"
        class="modal-overlay"
        @click.self="closeEditor"
      >
        <div class="modal-dialog editor-modal">
          <div class="modal-header">
            <div class="modal-title-wrapper">
              <i class="ri-edit-line"></i>
              <h2>{{ isNew ? "创建岗位画像" : "编辑岗位画像" }}</h2>
            </div>
            <button class="btn-close" @click="closeEditor">
              <i class="ri-close-line"></i>
            </button>
          </div>

          <!-- AI提示 -->
          <div v-if="isAIGenerated" class="ai-hint-banner">
            <i class="ri-sparkle-line"></i>
            <p>
              以下为 AI
              根据导入的简历/JD
              自动生成的岗位能力模型，请根据实际情况调整后保存
            </p>
          </div>

          <div class="modal-body editor-body">
            <!-- 基本信息 -->
            <div class="editor-section">
              <h3 class="section-title">
                <i class="ri-information-line"></i>
                基本信息
              </h3>
              <div class="form-grid">
                <div class="form-group required">
                  <label>岗位名称</label>
                  <input
                    v-model="formData.name"
                    type="text"
                    placeholder="例如：产品经理"
                    class="form-input"
                  />
                </div>
                <div class="form-group">
                  <label>所属部门</label>
                  <input
                    v-model="formData.department"
                    type="text"
                    placeholder="例如：产品部"
                    class="form-input"
                  />
                </div>
              </div>
              <div class="form-group">
                <label>岗位标签</label>
                <div class="tags-input">
                  <span
                    v-for="(tag, idx) in formData.tags"
                    :key="idx"
                    class="tag-item"
                  >
                    {{ tag }}
                    <button class="tag-remove" @click="removeTag(idx)">
                      <i class="ri-close-line"></i>
                    </button>
                  </span>
                  <input
                    v-model="newTag"
                    type="text"
                    placeholder="输入标签后按回车"
                    class="tag-input"
                    @keydown.enter.prevent="addTag"
                  />
                </div>
              </div>
              <div class="form-group">
                <label>岗位说明</label>
                <textarea
                  v-model="formData.description"
                  placeholder="简要说明岗位职责和要求"
                  class="form-textarea"
                  rows="2"
                ></textarea>
              </div>
            </div>

            <!-- AI一键配置按钮 -->
            <div class="ai-config-section">
              <button
                class="btn-ai-config"
                @click="aiAutoConfig"
                :disabled="!formData.name || aiConfiguring"
              >
                <i v-if="aiConfiguring" class="ri-loader-4-line animate-spin"></i>
                <i v-else class="ri-magic-line"></i>
                {{ aiConfiguring ? "AI配置中..." : "AI一键配置能力维度" }}
              </button>
              <p class="ai-config-hint">
                根据岗位基本信息智能生成能力维度和权重，或根据已填写的描述自动分配权重
              </p>
            </div>

            <!-- 能力维度配置 -->
            <div class="editor-section">
              <div class="section-header">
                <h3 class="section-title">
                  <i class="ri-stack-line"></i>
                  能力维度配置
                </h3>
                <button class="btn-add-small" @click="addDimension">
                  <i class="ri-add-line"></i>
                  添加维度
                </button>
              </div>

              <div class="dimensions-list">
                <div
                  v-for="(dim, idx) in formData.dimensions"
                  :key="idx"
                  class="dimension-item"
                >
                  <div class="dimension-header">
                    <span class="dimension-index">{{ idx + 1 }}</span>
                    <input
                      v-model="dim.name"
                      type="text"
                      placeholder="例如：产品规划能力"
                      class="dimension-name-input"
                    />
                    <button
                      class="btn-icon-small delete"
                      @click="removeDimension(idx)"
                    >
                      <i class="ri-delete-bin-line"></i>
                    </button>
                  </div>
                  <div class="dimension-body">
                    <div class="weight-control">
                      <label>权重</label>
                      <div class="weight-input-group">
                        <input
                          v-model.number="dim.weight"
                          type="range"
                          min="0"
                          max="100"
                          class="weight-slider"
                          @input="validateWeights"
                        />
                        <input
                          v-model.number="dim.weight"
                          type="number"
                          min="0"
                          max="100"
                          class="weight-number-input"
                          @input="validateWeights"
                        />
                        <span class="weight-unit">%</span>
                      </div>
                    </div>
                  </div>
                  <div class="dimension-description">
                    <label>描述</label>
                    <textarea
                      v-model="dim.description"
                      placeholder="说明该维度的具体要求"
                      class="description-textarea"
                      rows="2"
                    ></textarea>
                  </div>
                </div>
              </div>

              <!-- 权重验证 -->
              <div
                class="weight-validation"
                :class="{
                  error: !isWeightValid,
                  success: isWeightValid && formData.dimensions.length > 0,
                }"
              >
                <div class="validation-content">
                  <div class="weight-sum">
                    <span class="label">权重总和：</span>
                    <span class="value">{{ totalWeight }}%</span>
                  </div>
                  <div
                    v-if="!isWeightValid && formData.dimensions.length > 0"
                    class="validation-message error"
                  >
                    <i class="ri-error-warning-line"></i>
                    权重总和必须等于 100%
                  </div>
                  <div
                    v-else-if="isWeightValid && formData.dimensions.length > 0"
                    class="validation-message success"
                  >
                    <i class="ri-checkbox-circle-line"></i>
                    权重配置正确
                  </div>
                </div>
              </div>
            </div>

            <!-- 模型预览 -->
            <div class="editor-section preview-section">
              <h3 class="section-title">
                <i class="ri-eye-line"></i>
                模型预览
              </h3>
              <div class="preview-card">
                <div class="preview-header">
                  <h4>{{ formData.name || "岗位名称" }}</h4>
                  <span v-if="formData.department" class="preview-department">
                    {{ formData.department }}
                  </span>
                </div>
                <div class="preview-dimensions">
                  <div
                    v-for="(dim, idx) in formData.dimensions"
                    :key="idx"
                    class="preview-dimension"
                  >
                    <div class="dimension-info">
                      <span class="dimension-name">{{
                        dim.name || `维度${idx + 1}`
                      }}</span>
                      <span class="dimension-weight">{{ dim.weight }}%</span>
                    </div>
                    <div class="dimension-bar">
                      <div
                        class="bar-fill"
                        :style="{ width: dim.weight + '%' }"
                      ></div>
                    </div>
                  </div>
                </div>
                <div v-if="formData.dimensions.length === 0" class="preview-empty">
                  <i class="ri-information-line"></i>
                  请添加能力维度
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button
              v-if="!isNew"
              class="btn-delete"
              @click="deleteCurrentProfile"
            >
              <i class="ri-delete-bin-line"></i>
              删除画像
            </button>
            <div class="footer-actions">
              <button class="btn-secondary" @click="closeEditor">取消</button>
              <button
                class="btn-primary"
                @click="saveProfile"
                :disabled="!canSave"
              >
                <i class="ri-save-line"></i>
                保存画像
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 确认/提示对话框 -->
    <Transition name="modal">
      <div
        v-if="showConfirmDialog"
        class="modal-overlay"
        @click.self="showConfirmDialog = false"
      >
        <div class="modal-dialog confirm-modal">
          <div class="modal-header" :class="`type-${confirmDialogData.type}`">
            <div class="modal-title-wrapper">
              <i
                :class="{
                  'ri-information-line': confirmDialogData.type === 'info',
                  'ri-error-warning-line': confirmDialogData.type === 'warning',
                  'ri-checkbox-circle-line': confirmDialogData.type === 'success',
                  'ri-close-circle-line': confirmDialogData.type === 'error',
                }"
              ></i>
              <h2>{{ confirmDialogData.title }}</h2>
            </div>
          </div>
          <div class="modal-body">
            <p class="confirm-message">{{ confirmDialogData.message }}</p>
          </div>
          <div class="modal-footer">
            <button
              v-if="confirmDialogData.type === 'warning'"
              class="btn-secondary"
              @click="showConfirmDialog = false"
            >
              取消
            </button>
            <button class="btn-primary" @click="confirmDialogData.onConfirm()">
              {{ confirmDialogData.type === 'warning' ? '确定' : '知道了' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.job-profiles-page {
  padding: 2rem;
  min-height: 100vh;
  /* V41: 移除背景渐变，与专业测评页面保持一致 */
  background: transparent;
}

/* 渐变头部 - 与专业测评页面形状一致 */
.page-header {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #b45309 100%);
  border-radius: 20px;
  padding: 2.5rem;
  margin-bottom: 2rem;
  /* V41: 减小阴影范围，避免橙色延伸到内容区域 */
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.icon-wrapper {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
}

.page-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: white;
  margin: 0 0 0.375rem 0;
}

.page-subtitle {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-primary,
.btn-import {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: white;
  color: #d97706;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-import {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.btn-import:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
}

/* 统计卡片 */
.stats-grid {
  max-width: 1400px;
  margin: 0 auto 2rem;
  padding: 0 2rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.25rem;
}

.stat-card {
  background: linear-gradient(135deg, var(--gradient-from), var(--gradient-to));
  border-radius: 16px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.9375rem;
  color: rgba(255, 255, 255, 0.9);
}

/* 搜索栏 */
.search-section {
  max-width: 1400px;
  margin: 0 auto 2rem;
  padding: 0 2rem;
}

.search-bar {
  position: relative;
  max-width: 500px;
}

.search-bar i {
  position: absolute;
  left: 1.125rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.25rem;
  color: #94a3b8;
}

.search-input {
  width: 100%;
  padding: 0.875rem 1.125rem 0.875rem 3rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  font-size: 0.9375rem;
  background: white;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.search-input:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

/* 加载和空状态 */
.loading-state,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #94a3b8;
}

.loading-state i,
.empty-state i {
  font-size: 3rem;
  color: #cbd5e1;
  margin-bottom: 1rem;
}

.loading-state p,
.empty-state p {
  font-size: 1rem;
  margin-bottom: 1.5rem;
}

/* 岗位卡片网格 */
.profiles-grid {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem 2rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.profile-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  cursor: pointer;
  border: 2px solid transparent;
}

.profile-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.2);
  border-color: #f59e0b;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.job-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: white;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1.5px solid #e2e8f0;
  background: white;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #f59e0b;
  color: #d97706;
  background: #fef3c7;
}

.action-btn.delete:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

.job-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 1rem 0;
}

.job-info {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

.info-item i {
  font-size: 1rem;
  color: #94a3b8;
}

.job-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.tag {
  padding: 0.25rem 0.75rem;
  background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
  border-radius: 6px;
  font-size: 0.8125rem;
  color: #475569;
  font-weight: 500;
}

.card-footer {
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.update-time {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: #94a3b8;
}

.update-time i {
  font-size: 0.875rem;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-dialog {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.import-modal {
  max-width: 600px;
}

.editor-modal {
  max-width: 900px;
}

.confirm-modal {
  max-width: 450px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1.5px solid #f1f5f9;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 16px 16px 0 0;
}

.modal-header.type-success {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.modal-header.type-error {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
}

.modal-header.type-warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
}

.modal-title-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.modal-title-wrapper i {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: white;
}

.modal-header.type-success .modal-title-wrapper i {
  background: linear-gradient(135deg, #10b981, #059669);
}

.modal-header.type-error .modal-title-wrapper i {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.modal-header.type-warning .modal-title-wrapper i {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.modal-title-wrapper h2 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.btn-close {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #e2e8f0;
  color: #475569;
}

.modal-body {
  padding: 2rem;
}

.editor-body {
  max-height: calc(90vh - 200px);
  overflow-y: auto;
}

.confirm-message {
  font-size: 1rem;
  color: #475569;
  line-height: 1.6;
  margin: 0;
  text-align: center;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 2rem;
  border-top: 1.5px solid #f1f5f9;
  background: #f8fafc;
  border-radius: 0 0 16px 16px;
}

.confirm-modal .modal-footer {
  justify-content: center;
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
  margin-left: auto;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: white;
  color: #475569;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.btn-delete {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: white;
  color: #ef4444;
  border: 1.5px solid #fecaca;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.import-hint {
  display: flex;
  gap: 0.875rem;
  padding: 1.125rem;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f4ff 100%);
  border-radius: 10px;
  border: 1.5px solid #dbeafe;
  margin-bottom: 1.5rem;
}

.import-hint i {
  font-size: 1.375rem;
  color: #d97706;
  flex-shrink: 0;
}

.import-hint p {
  font-size: 0.9375rem;
  color: #475569;
  line-height: 1.6;
  margin: 0;
}

.upload-area {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 2.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #f8fafc;
}

.upload-area:hover {
  border-color: #f59e0b;
  background: linear-gradient(135deg, #fef3c7 0%, #fef7ed 100%);
}

.upload-area i {
  font-size: 3rem;
  color: #d97706;
  margin-bottom: 1rem;
}

.upload-area p {
  font-size: 1.0625rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.375rem 0;
}

.upload-hint-text {
  font-size: 0.875rem;
  color: #94a3b8;
}

.file-list {
  margin-top: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1.125rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
}

.file-item i {
  font-size: 1.375rem;
  color: #d97706;
}

.file-item span {
  flex: 1;
  font-size: 0.9375rem;
  color: #475569;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-remove {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: #fee2e2;
  color: #dc2626;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s;
}

/* 上传进度条样式 */
.upload-progress {
  margin-top: 1.25rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #fef3c7 0%, #fef7ed 100%);
  border-radius: 10px;
  border: 1.5px solid #c7d2fe;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.625rem;
}

.progress-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #4f46e5;
}

.progress-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #d97706;
}

.progress-bar {
  height: 8px;
  background: #e0e7ff;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-remove:hover {
  background: #fecaca;
}

/* AI提示横幅 */
.ai-hint-banner {
  display: flex;
  gap: 0.875rem;
  padding: 1.125rem 2rem;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f4ff 100%);
  border-bottom: 1.5px solid #dbeafe;
}

.ai-hint-banner i {
  font-size: 1.375rem;
  color: #d97706;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.ai-hint-banner p {
  font-size: 0.9375rem;
  color: #475569;
  line-height: 1.6;
  margin: 0;
}

/* 编辑器区块 */
.editor-section {
  margin-bottom: 2rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 1.25rem 0;
}

.section-title i {
  font-size: 1.25rem;
  color: #d97706;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.btn-add-small {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

.btn-add-small:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

/* 表单 */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group.required label::after {
  content: " *";
  color: #ef4444;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.625rem;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 0.875rem 1.125rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9375rem;
  transition: all 0.2s;
  background: white;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
}

/* 标签输入 */
.tags-input {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.625rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  min-height: 48px;
  background: white;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
  border-radius: 6px;
  font-size: 0.875rem;
  color: #475569;
  font-weight: 500;
}

.tag-remove {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: rgba(100, 116, 139, 0.2);
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  transition: all 0.2s;
}

.tag-remove:hover {
  background: rgba(100, 116, 139, 0.3);
}

.tag-input {
  flex: 1;
  min-width: 120px;
  border: none;
  outline: none;
  font-size: 0.9375rem;
  padding: 0.25rem;
}

/* AI配置区域 */
.ai-config-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-radius: 12px;
  border: 1.5px solid #e9d5ff;
  text-align: center;
}

.ai-config-content {
  flex: 1;
  text-align: center;
}

.btn-ai-config {
  display: inline-flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #a855f7, #9333ea);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 12px rgba(168, 85, 247, 0.3);
  margin-bottom: 0.75rem;
}

.btn-ai-config:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4);
}

.btn-ai-config:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-ai-config i {
  font-size: 1.25rem;
}

.ai-config-hint {
  font-size: 0.875rem;
  color: #7c3aed;
  margin: 0;
}

/* 维度列表 */
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.dimension-item {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  transition: all 0.2s;
}

.dimension-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.dimension-header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  margin-bottom: 1rem;
}

.dimension-index {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9375rem;
  font-weight: 700;
  flex-shrink: 0;
}

.dimension-name-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  background: white;
  transition: all 0.2s;
}

.dimension-name-input:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

.btn-icon-small {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1.5px solid #e2e8f0;
  background: white;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-icon-small:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.btn-icon-small.delete:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

.dimension-body {
  display: flex;
  align-items: flex-end;
  gap: 0;
  margin-bottom: 1rem;
}

.dimension-description {
  margin-top: 0;
}

.weight-control label,
.dimension-description label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.weight-input-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.weight-slider {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  -webkit-appearance: none;
}

.weight-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
}

.weight-number-input {
  width: 60px;
  padding: 0.5rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9375rem;
  font-weight: 600;
  text-align: center;
  background: white;
}

.weight-number-input:focus {
  outline: none;
  border-color: #f59e0b;
}

.weight-unit {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 600;
}

.description-textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.875rem;
  background: white;
  transition: all 0.2s;
  resize: vertical;
  font-family: inherit;
  line-height: 1.5;
}

.description-textarea:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

/* 权重验证 */
.weight-validation {
  padding: 1.25rem;
  background: #f8fafc;
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
}

.weight-validation.error {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-color: #fecaca;
}

.weight-validation.success {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: #bbf7d0;
}

.validation-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weight-sum {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.weight-sum .label {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #64748b;
}

.weight-sum .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ef4444;
}

.weight-validation.success .weight-sum .value {
  color: #10b981;
}

.validation-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.validation-message.error {
  color: #ef4444;
}

.validation-message.success {
  color: #10b981;
}

.validation-message i {
  font-size: 1.125rem;
}

/* 预览 */
.preview-section {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1.5px solid #e9d5ff;
  border-radius: 12px;
  padding: 1.5rem;
}

.preview-card {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1.5px solid #f1f5f9;
}

.preview-header h4 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  flex: 1;
}

.preview-department {
  padding: 0.375rem 0.875rem;
  background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
  border-radius: 6px;
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.preview-dimensions {
  display: flex;
  flex-direction: column;
  gap: 1.125rem;
}

.preview-dimension {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dimension-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dimension-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #475569;
}

.dimension-weight {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #d97706;
}

.dimension-bar {
  height: 10px;
  background: #f1f5f9;
  border-radius: 5px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b, #d97706);
  border-radius: 5px;
  transition: width 0.3s ease;
}

.preview-empty {
  text-align: center;
  padding: 2.5rem;
  color: #94a3b8;
}

.preview-empty i {
  font-size: 2.5rem;
  color: #cbd5e1;
  margin-bottom: 0.75rem;
}

/* 动画 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-dialog,
.modal-leave-to .modal-dialog {
  transform: scale(0.95) translateY(20px);
}
</style>
