<script setup lang="ts">
/**
 * 人员管理页面
 *
 * 功能：
 * 1. 统一展示所有人员（候选人+答题人）
 * 2. 支持搜索、筛选、列表/分组视图切换
 * 3. 分组视图下支持展开查看每个人的所有提交记录
 * 4. V44: 支持单个删除和批量删除人员
 */
import { ref, computed, onMounted, defineAsyncComponent, watch } from "vue";
import { apiRequest, apiRequestWithBody } from "../api/client";

// 异步加载提交详情弹窗
const SubmissionDetailModal = defineAsyncComponent(() => import('../components/SubmissionDetailModal.vue'))

// 异步加载自定义确认弹窗
const CustomAlert = defineAsyncComponent(() => import('../components/CustomAlert.vue'))

// 提交记录接口
interface SubmissionRecord {
  id: number;
  code: string;
  questionnaire_name: string;
  questionnaire_type: string;
  submitted_at: string;
  started_at: string;
  status: string;
  total_score?: number;
  grade?: string;
}

// 人员记录接口
interface PersonRecord {
  id: number;
  name: string;
  phone: string;
  email?: string;
  gender?: string;
  position?: string;
  department?: string;
  totalSubmissions: number;
  completedSubmissions: number;
  submissions: SubmissionRecord[];
  firstActivity: string;
  lastActivity: string;
}

// 状态
const loading = ref(false);
const persons = ref<PersonRecord[]>([]);
const searchQuery = ref("");
const filterStatus = ref<"all" | "active" | "completed">("all");
const viewMode = ref<"list" | "group">("list");
const expandedPersons = ref<Set<string>>(new Set());

// 分页状态
const currentPage = ref(1);
const pageSize = 10;

// V45: 年份/月份筛选
const filterYear = ref<number | null>(null);
const filterMonth = ref<number | null>(null);

// 生成年份选项（从2024年到当前年份）
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear();
  const years: number[] = [];
  for (let y = currentYear; y >= 2024; y--) {
    years.push(y);
  }
  return years;
});

// 月份选项
const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// 详情弹窗
const showSubmissionDetailModal = ref(false);
const selectedSubmission = ref<any>(null);

// V44: 删除功能状态
const selectedPersons = ref<Set<string>>(new Set());  // 选中的人员（用 phone || name 作为 key）
const isSelectMode = ref(false);  // 是否处于选择模式
const showDeleteConfirmModal = ref(false);  // 删除确认弹窗
const deleteTargetPerson = ref<PersonRecord | null>(null);  // 单个删除目标
const isBatchDelete = ref(false);  // 是否批量删除

// V44: 切换选择模式
const toggleSelectMode = () => {
  isSelectMode.value = !isSelectMode.value;
  if (!isSelectMode.value) {
    selectedPersons.value.clear();
  }
};

// V44: 切换单个人员选择
const togglePersonSelect = (person: PersonRecord) => {
  const key = person.phone || person.name;
  if (selectedPersons.value.has(key)) {
    selectedPersons.value.delete(key);
  } else {
    selectedPersons.value.add(key);
  }
};

// V44: 全选/取消全选
const toggleSelectAll = () => {
  if (selectedPersons.value.size === filteredPersons.value.length) {
    selectedPersons.value.clear();
  } else {
    selectedPersons.value = new Set(filteredPersons.value.map(p => p.phone || p.name));
  }
};

// V44: 打开单个删除确认弹窗
const openDeleteConfirmModal = (person: PersonRecord) => {
  deleteTargetPerson.value = person;
  isBatchDelete.value = false;
  showDeleteConfirmModal.value = true;
};

// V44: 打开批量删除确认弹窗
const openBatchDeleteModal = () => {
  if (selectedPersons.value.size === 0) return;
  isBatchDelete.value = true;
  showDeleteConfirmModal.value = true;
};

// V44: 关闭删除确认弹窗
const closeDeleteConfirmModal = () => {
  showDeleteConfirmModal.value = false;
  deleteTargetPerson.value = null;
  isBatchDelete.value = false;
};

// V44: 执行删除
const executeDelete = async () => {
  try {
    if (isBatchDelete.value) {
      // 批量删除
      const toDeleteKeys = Array.from(selectedPersons.value);
      const toDeletePersons = filteredPersons.value.filter(p => toDeleteKeys.includes(p.phone || p.name));

      // 删除所有相关人员
      for (const person of toDeletePersons) {
        await deletePersonData(person);
      }

      selectedPersons.value.clear();
      isSelectMode.value = false;
    } else if (deleteTargetPerson.value) {
      // 单个删除
      await deletePersonData(deleteTargetPerson.value);
    }

    closeDeleteConfirmModal();

    // V45: 删除成功后自动刷新列表
    await loadPersons();
  } catch (error) {
    console.error('删除失败:', error);
    alert('删除失败，请重试');
  }
};

// V45: 删除人员数据（支持通过候选人ID或手机号删除）
const deletePersonData = async (person: PersonRecord) => {
  // 如果有候选人ID，通过ID删除
  if (person.id && person.id > 0) {
    await apiRequestWithBody({
      path: `/api/candidates/${person.id}`,
      method: 'DELETE',
      auth: true
    });
  } else if (person.phone) {
    // 没有候选人ID，通过手机号删除提交记录
    await apiRequestWithBody({
      path: `/api/persons/by-phone/${encodeURIComponent(person.phone)}`,
      method: 'DELETE',
      auth: true
    });
  } else if (person.name) {
    // 通过姓名删除
    await apiRequestWithBody({
      path: `/api/persons/by-name/${encodeURIComponent(person.name)}`,
      method: 'DELETE',
      auth: true
    });
  }
};

// 过滤后的人员列表
const filteredPersons = computed(() => {
  let result = [...persons.value];

  // V45: 年份筛选（基于最后活动时间）
  if (filterYear.value) {
    result = result.filter(p => {
      const dateStr = p.lastActivity;
      if (!dateStr) return false;
      const date = new Date(dateStr);
      return date.getFullYear() === filterYear.value;
    });
  }

  // V45: 月份筛选
  if (filterMonth.value) {
    result = result.filter(p => {
      const dateStr = p.lastActivity;
      if (!dateStr) return false;
      const date = new Date(dateStr);
      return (date.getMonth() + 1) === filterMonth.value;
    });
  }

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.phone.includes(query) ||
      (p.email?.toLowerCase().includes(query)) ||
      (p.position?.toLowerCase().includes(query))
    );
  }

  // 状态过滤
  if (filterStatus.value === "active") {
    result = result.filter(p => p.completedSubmissions < p.totalSubmissions || p.totalSubmissions === 0);
  } else if (filterStatus.value === "completed") {
    result = result.filter(p => p.completedSubmissions > 0 && p.completedSubmissions === p.totalSubmissions);
  }

  return result;
});

// 过滤后总数
const totalFilteredCount = computed(() => filteredPersons.value.length);

// 总页数
const totalPages = computed(() => Math.ceil(totalFilteredCount.value / pageSize));

// 分页后的人员列表（用于显示）
const paginatedPersons = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  const end = start + pageSize;
  return filteredPersons.value.slice(start, end);
});

// 切换页码
const changePage = (newPage: number) => {
  if (newPage < 1 || newPage > totalPages.value) return;
  currentPage.value = newPage;
};

// 搜索/筛选变化时重置页码
watch([searchQuery, filterYear, filterMonth, filterStatus], () => {
  currentPage.value = 1;
});

// 统计数据
const stats = computed(() => ({
  total: persons.value.length,
  active: persons.value.filter(p => p.totalSubmissions === 0 || p.completedSubmissions < p.totalSubmissions).length,
  completed: persons.value.filter(p => p.completedSubmissions > 0 && p.completedSubmissions === p.totalSubmissions).length,
  totalSubmissions: persons.value.reduce((sum, p) => sum + p.totalSubmissions, 0),
}));

// 加载人员数据
const loadPersons = async () => {
  loading.value = true;
  try {
    // 从候选人和提交记录中聚合人员数据
    const [candidatesRes, submissionsRes] = await Promise.all([
      apiRequest<any>({ path: "/api/candidates?page=1&page_size=1000", fallback: { items: [] }, auth: true }),
      apiRequest<any>({ path: "/api/assessments/submissions?page=1&page_size=1000", fallback: [], auth: true }),
    ]);

    const personMap = new Map<string, PersonRecord>();

    const isAnonymous = (name?: string, phone?: string) => {
      const trimmedName = (name || "").trim();
      const trimmedPhone = (phone || "").trim();
      if (trimmedPhone) return false;
      if (!trimmedName) return true;
      return ["匿名", "未知", "unknown"].includes(trimmedName.toLowerCase());
    };

    // 处理候选人数据
    const candidates = candidatesRes?.items || candidatesRes || [];
    candidates.forEach((c: any) => {
      if (isAnonymous(c.name, c.phone)) return;
      const key = c.phone || c.name;
      if (!personMap.has(key)) {
        personMap.set(key, {
          id: c.id,
          name: c.name,
          phone: c.phone || "",
          email: c.email,
          gender: c.gender,
          position: c.target_position || c.position,
          department: c.department,
          totalSubmissions: 0,
          completedSubmissions: 0,
          submissions: [],
          firstActivity: c.created_at || new Date().toISOString(),
          lastActivity: c.updated_at || c.created_at || new Date().toISOString(),
        });
      }
    });

    // 处理提交记录
    const submissions = submissionsRes?.items || submissionsRes || [];
    submissions.forEach((s: any) => {
      if (isAnonymous(s.candidate_name, s.candidate_phone)) return;
      const key = s.candidate_phone || s.candidate_name;

      const submissionRecord: SubmissionRecord = {
        id: s.id,
        code: s.code,
        questionnaire_name: s.questionnaire_name,
        questionnaire_type: s.questionnaire_type,
        submitted_at: s.submitted_at,
        started_at: s.started_at,
        status: s.status,
        total_score: s.total_score,
        grade: s.grade,
      };

      if (personMap.has(key)) {
        const person = personMap.get(key)!;
        person.totalSubmissions++;
        if (s.status === "completed") {
          person.completedSubmissions++;
        }
        person.submissions.push(submissionRecord);
        // 更新活动时间
        if (s.submitted_at && new Date(s.submitted_at) > new Date(person.lastActivity)) {
          person.lastActivity = s.submitted_at;
        }
        if (s.started_at && new Date(s.started_at) < new Date(person.firstActivity)) {
          person.firstActivity = s.started_at;
        }
        // V45: 更新性别和岗位（取第一个有效的值）
        if (!person.gender && s.gender) {
          person.gender = s.gender;
        }
        if (!person.position && s.target_position) {
          person.position = s.target_position;
        }
      } else {
        // 新建人员记录 - 注意：这里没有候选人记录，id 设为 0 表示需要通过其他方式删除
        personMap.set(key, {
          id: 0,  // 没有候选人记录时设为 0
          name: s.candidate_name || "未知",
          phone: s.candidate_phone || "",
          email: s.candidate_email,
          gender: s.gender,  // V45: 从提交记录获取性别
          position: s.target_position,  // V45: 从提交记录获取岗位
          totalSubmissions: 1,
          completedSubmissions: s.status === "completed" ? 1 : 0,
          submissions: [submissionRecord],
          firstActivity: s.started_at || s.submitted_at || new Date().toISOString(),
          lastActivity: s.submitted_at || s.started_at || new Date().toISOString(),
        });
      }
    });

    // 按最后活动时间排序，并对每个人的提交记录按时间倒序排序
    persons.value = Array.from(personMap.values())
      .map(p => ({
        ...p,
        submissions: p.submissions.sort((a, b) =>
          new Date(b.submitted_at || b.started_at).getTime() - new Date(a.submitted_at || a.started_at).getTime()
        )
      }))
      .sort((a, b) => new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime());
  } catch (error) {
    console.error("加载人员数据失败:", error);
  } finally {
    loading.value = false;
  }
};

// 格式化日期
const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return "--";
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "--";
  }
};

// 格式化简短日期
const formatShortDate = (dateStr: string | undefined) => {
  if (!dateStr) return "--";
  try {
    return new Date(dateStr).toLocaleDateString("zh-CN");
  } catch {
    return "--";
  }
};

// 切换人员展开状态
const togglePersonExpand = (key: string) => {
  if (expandedPersons.value.has(key)) {
    expandedPersons.value.delete(key);
  } else {
    expandedPersons.value.add(key);
  }
};

// 全部展开/收起
const toggleAllPersons = () => {
  if (expandedPersons.value.size === filteredPersons.value.length) {
    expandedPersons.value.clear();
  } else {
    expandedPersons.value = new Set(
      filteredPersons.value.map(p => p.phone || p.name)
    );
  }
};

// 查看提交详情
const openSubmissionDetail = (submission: SubmissionRecord, person: PersonRecord) => {
  selectedSubmission.value = {
    ...submission,
    candidate_name: person.name,
    candidate_phone: person.phone,
  };
  showSubmissionDetailModal.value = true;
};

// 导出数据
const exportData = () => {
  const headers = ["姓名", "联系方式", "邮箱", "岗位", "测评次数", "完成次数", "最近活动"];
  const rows = filteredPersons.value.map(p => [
    p.name,
    p.phone,
    p.email || "",
    p.position || "",
    p.totalSubmissions,
    p.completedSubmissions,
    formatDate(p.lastActivity),
  ]);

  const csvContent = [
    headers.join(","),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
  ].join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `人员管理_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
};

onMounted(() => {
  loadPersons();
});
</script>

<template src="./UserManagementPage.template.html"></template>


<style scoped>
@import './styles/user-management-page.css';
</style>
