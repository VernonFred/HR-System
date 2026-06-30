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
    // ⭐ V50: 追加文件而不是覆盖，支持多次选择
    const newFiles = Array.from(target.files);
    selectedResumes.value = [...selectedResumes.value, ...newFiles];
    // 重置 input 以便同一文件可以再次选择
    target.value = '';
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
  } catch (error: any) {
    console.error("AI生成失败:", error);
    // ⭐ V50: 提取友好的错误消息，避免显示代码
    const errorMsg = error?.message || error?.detail || '服务暂时不可用，请稍后重试';
    showMessage(`AI生成失败：${errorMsg}`, "error");
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
  } catch (error: any) {
    console.error("AI生成失败:", error);
    // ⭐ V50: 提取友好的错误消息，避免显示代码
    const errorMsg = error?.message || error?.detail || '服务暂时不可用，请稍后重试';
    showMessage(`AI生成失败：${errorMsg}`, "error");
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

<template src="./JobProfilesPage.template.html"></template>


<style scoped>
@import './styles/job-profiles-page.css';
</style>
