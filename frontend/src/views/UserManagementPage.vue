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
    
    // 处理候选人数据
    const candidates = candidatesRes?.items || candidatesRes || [];
    candidates.forEach((c: any) => {
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

<template>
  <div class="person-management">
        <!-- 页面头部 -->
    <header class="page-header">
      <div class="header-icon">
        <i class="ri-group-2-line"></i>
      </div>
      <div class="header-content">
              <h1>人员管理</h1>
            </div>
    </header>
        
    <!-- V45: 现代化工具栏 - 飞书/Notion风格 -->
    <div class="toolbar">
      <!-- 搜索框 -->
      <div class="toolbar-search">
            <i class="ri-search-line"></i>
            <input 
              type="text" 
            v-model="searchQuery"
            placeholder="搜索姓名、电话或岗位..."
            />
        </div>
      
      <!-- 筛选器组 -->
      <div class="toolbar-filters">
        <div class="filter-chip" :class="{ active: filterYear !== null }">
          <i class="ri-calendar-line"></i>
          <select v-model="filterYear">
            <option :value="null">全部年份</option>
            <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}年</option>
          </select>
        </div>
        <div class="filter-chip" :class="{ active: filterMonth !== null }">
          <i class="ri-calendar-event-line"></i>
          <select v-model="filterMonth">
            <option :value="null">全部月份</option>
            <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}月</option>
          </select>
        </div>
        <div class="filter-chip" :class="{ active: filterStatus !== 'all' }">
          <i class="ri-checkbox-circle-line"></i>
          <select v-model="filterStatus">
            <option value="all">全部状态</option>
            <option value="active">待测评</option>
            <option value="completed">已完成</option>
          </select>
        </div>
      </div>
      
        <!-- 视图切换 -->
      <div class="toolbar-view">
          <button 
          :class="['view-btn', { active: viewMode === 'list' }]" 
            @click="viewMode = 'list'"
            title="列表视图"
          >
            <i class="ri-list-unordered"></i>
          </button>
          <button 
          :class="['view-btn', { active: viewMode === 'group' }]" 
            @click="viewMode = 'group'"
            title="分组视图"
          >
          <i class="ri-layout-grid-line"></i>
            </button>
          </div>
      
      <!-- 操作按钮 -->
      <div class="toolbar-actions">
        <button class="action-btn primary" @click="exportData">
          <i class="ri-download-line"></i>
          导出
        </button>
        <button 
          v-if="viewMode === 'list'"
          :class="['action-btn', { danger: isSelectMode }]" 
          @click="toggleSelectMode"
        >
            <i :class="isSelectMode ? 'ri-close-line' : 'ri-checkbox-multiple-line'"></i>
            {{ isSelectMode ? '取消' : '批量删除' }}
          </button>
        <button class="action-btn icon-only" @click="loadPersons" :disabled="loading" title="刷新">
          <i class="ri-refresh-line" :class="{ spin: loading }"></i>
        </button>
          </div>
        </div>

    <!-- V44: 批量操作栏 - 仅列表模式显示 -->
    <div v-if="isSelectMode && viewMode === 'list'" class="batch-bar">
      <label class="select-all">
        <input type="checkbox" :checked="selectedPersons.size === filteredPersons.length && filteredPersons.length > 0" @change="toggleSelectAll" />
        <span>全选</span>
      </label>
      <span class="selected-count">已选 {{ selectedPersons.size }} 人</span>
      <button class="btn-delete-batch" :disabled="selectedPersons.size === 0" @click="openBatchDeleteModal">
        <i class="ri-delete-bin-line"></i>
        删除选中
      </button>
        </div>
        
    <!-- 统计信息 -->
    <div class="stats-summary">
      <div class="summary-item">
        <span class="summary-value">{{ stats.total }}</span>
        <span class="summary-label">人员总数</span>
      </div>
      <div class="summary-item active">
        <i class="ri-time-fill"></i>
        <span class="summary-value">{{ stats.active }}</span>
        <span class="summary-label">待测评</span>
      </div>
      <div class="summary-item completed">
        <i class="ri-checkbox-circle-fill"></i>
        <span class="summary-value">{{ stats.completed }}</span>
        <span class="summary-label">已完成</span>
      </div>
      <div class="summary-item total">
        <i class="ri-file-list-3-line"></i>
        <span class="summary-value">{{ stats.totalSubmissions }}</span>
        <span class="summary-label">测评记录</span>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-card">
          <div v-if="loading" class="loading-state">
        <i class="ri-loader-4-line spin"></i>
            <span>加载中...</span>
          </div>
          
      <div v-else-if="paginatedPersons.length === 0" class="empty-state">
            <i class="ri-user-unfollow-line"></i>
            <p>暂无人员数据</p>
          </div>
          
      <!-- 列表视图 -->
      <div v-else-if="viewMode === 'list'" class="table-wrapper">
        <table class="persons-table">
            <thead>
              <tr>
                <th v-if="isSelectMode" class="cell-checkbox"><input type="checkbox" :checked="selectedPersons.size === filteredPersons.length" @change="toggleSelectAll" /></th>
                <th>姓名</th>
                <th>性别</th>
                <th>联系方式</th>
              <th>岗位</th>
              <th>测评次数</th>
              <th>完成率</th>
              <th>最近测评</th>
                <th>最近活动</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
            <tr v-for="person in paginatedPersons" :key="person.phone || person.name" class="person-row" :class="{ selected: selectedPersons.has(person.phone || person.name) }">
                <td v-if="isSelectMode" class="cell-checkbox"><input type="checkbox" :checked="selectedPersons.has(person.phone || person.name)" @change="togglePersonSelect(person)" /></td>
                <td class="cell-name">
                <div class="person-info">
                  <span class="person-avatar">{{ person.name.charAt(0).toUpperCase() }}</span>
                  <div class="person-detail">
                    <span class="name">{{ person.name }}</span>
                    <span v-if="person.email" class="email">{{ person.email }}</span>
                  </div>
                </div>
                </td>
                <td class="cell-gender">
                  <span v-if="person.gender" class="gender-tag" :class="person.gender === '男' ? 'male' : 'female'">
                    <i :class="person.gender === '男' ? 'ri-men-line' : 'ri-women-line'"></i>
                    {{ person.gender }}
                  </span>
                  <span v-else class="no-data">--</span>
                </td>
              <td class="cell-phone">{{ person.phone || "--" }}</td>
              <td class="cell-position">{{ person.position || "--" }}</td>
              <td class="cell-count">
                <span class="count-badge">{{ person.totalSubmissions }} 次</span>
                </td>
              <td class="cell-rate">
                <div class="progress-bar">
                  <div 
                    class="progress-fill" 
                    :style="{ width: person.totalSubmissions > 0 ? `${(person.completedSubmissions / person.totalSubmissions) * 100}%` : '0%' }"
                  ></div>
                </div>
                <span class="rate-text">{{ person.completedSubmissions }}/{{ person.totalSubmissions }}</span>
              </td>
              <td class="cell-latest">
                <div v-if="person.submissions.length > 0" class="latest-info">
                  <span class="questionnaire-name">{{ person.submissions[0].questionnaire_name }}</span>
                </div>
                <span v-else class="no-data">--</span>
                </td>
              <td class="cell-time">{{ formatDate(person.lastActivity) }}</td>
              <td class="cell-actions">
                <button class="btn-action-delete" @click="openDeleteConfirmModal(person)" title="删除">
                  <i class="ri-delete-bin-line"></i>
                </button>
              </td>
              </tr>
            </tbody>
          </table>
          
          <!-- 分页控件 -->
          <div v-if="totalFilteredCount > pageSize" class="pagination-bar">
            <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)" title="上一页">
              <i class="ri-arrow-left-s-line"></i>
            </button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }} (共 {{ totalFilteredCount }} 人)</span>
            <button class="page-btn" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)" title="下一页">
              <i class="ri-arrow-right-s-line"></i>
            </button>
          </div>
        </div>

      <!-- 分组视图 -->
      <div v-else class="grouped-view">
        <!-- V45: 分组模式控制栏 - 类似专业测评 -->
        <div class="grouped-controls">
          <button class="btn-toggle-all" @click="toggleAllPersons">
            <i :class="expandedPersons.size === filteredPersons.length ? 'ri-contract-up-down-line' : 'ri-expand-up-down-line'"></i>
            {{ expandedPersons.size === filteredPersons.length ? '全部收起' : '全部展开' }}
          </button>
          <button 
            :class="['btn-batch-select', { active: isSelectMode }]" 
            @click="toggleSelectMode"
          >
            <i :class="isSelectMode ? 'ri-close-line' : 'ri-checkbox-multiple-line'"></i>
            {{ isSelectMode ? '取消选择' : '批量删除' }}
          </button>
        </div>
        
        <!-- V45: 批量操作栏 -->
        <div v-if="isSelectMode" class="batch-action-bar">
          <div class="batch-left">
            <label class="select-all-checkbox">
              <input 
                type="checkbox" 
                :checked="selectedPersons.size === filteredPersons.length && filteredPersons.length > 0"
                @change="toggleSelectAll"
              />
              <span>全选</span>
            </label>
            <span class="selected-count">已选择 {{ selectedPersons.size }} 人</span>
          </div>
          <div class="batch-right">
            <button 
              class="btn-batch-delete" 
              :disabled="selectedPersons.size === 0"
              @click="openBatchDeleteConfirmModal"
            >
              <i class="ri-delete-bin-line"></i>
              删除选中 ({{ selectedPersons.size }})
            </button>
          </div>
        </div>
        
        <!-- 人员分组卡片 -->
        <div class="person-groups">
          <div 
            v-for="person in paginatedPersons" 
            :key="person.phone || person.name"
            class="person-group-card"
            :class="{ expanded: expandedPersons.has(person.phone || person.name) }"
          >
            <!-- 分组头部 - V45: 标签放在名字旁边，类似专业测评分组样式 -->
            <div 
              class="group-header"
              @click="togglePersonExpand(person.phone || person.name)"
            >
              <!-- V45: 选择模式下显示复选框 -->
              <input 
                v-if="isSelectMode"
                type="checkbox" 
                class="group-checkbox"
                :checked="selectedPersons.has(person.phone || person.name)"
                @click.stop
                @change="togglePersonSelect(person)"
              />
              <div class="group-main">
                <span class="group-avatar">{{ person.name.charAt(0).toUpperCase() }}</span>
                <div class="group-info">
                  <div class="group-name-row">
                  <span class="group-name">{{ person.name }}</span>
                  <span class="group-phone">{{ person.phone || '--' }}</span>
                    <!-- V45: 标签放在名字旁边 -->
                <span class="stat-badge total">
                  <i class="ri-file-list-3-line"></i>
                  {{ person.totalSubmissions }}次测评
                </span>
                <span class="stat-badge completed" v-if="person.completedSubmissions > 0">
                  <i class="ri-checkbox-circle-fill"></i>
                  {{ person.completedSubmissions }}已完成
                </span>
                <span class="stat-badge latest" v-if="person.submissions.length > 0">
                  <i class="ri-time-line"></i>
                  {{ formatShortDate(person.lastActivity) }}
                </span>
              </div>
                </div>
              </div>
              <button class="btn-delete-group" @click.stop="openDeleteConfirmModal(person)" title="删除">
                <i class="ri-delete-bin-line"></i>
              </button>
              <i :class="['expand-icon', expandedPersons.has(person.phone || person.name) ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line']"></i>
            </div>
            
            <!-- 展开的测评列表 -->
            <div v-if="expandedPersons.has(person.phone || person.name)" class="group-submissions">
              <div v-if="person.submissions.length === 0" class="no-submissions">
                <i class="ri-inbox-line"></i>
                <span>暂无测评记录</span>
              </div>
              <div 
                v-else
                v-for="(sub, idx) in person.submissions" 
                :key="sub.id"
                class="submission-item"
              >
                <div class="submission-order">#{{ idx + 1 }}</div>
                <div class="submission-info">
                  <span class="submission-questionnaire">{{ sub.questionnaire_name || 'N/A' }}</span>
                  <span class="submission-time">
                    {{ sub.submitted_at ? formatDate(sub.submitted_at) : '进行中' }}
                  </span>
                </div>
                <div class="submission-result">
                  <span v-if="sub.total_score !== null && sub.total_score !== undefined" class="score">{{ sub.total_score }}分</span>
                  <span v-if="sub.grade" class="grade" :class="`grade-${sub.grade.toLowerCase()}`">{{ sub.grade }}</span>
                  <span :class="['status-mini', sub.status === 'completed' ? 'completed' : 'progress']">
                    {{ sub.status === 'completed' ? '已完成' : '进行中' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 分页控件 -->
        <div v-if="totalFilteredCount > pageSize" class="pagination-bar">
          <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)" title="上一页">
            <i class="ri-arrow-left-s-line"></i>
          </button>
          <span class="page-info">{{ currentPage }} / {{ totalPages }} (共 {{ totalFilteredCount }} 人)</span>
          <button class="page-btn" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)" title="下一页">
            <i class="ri-arrow-right-s-line"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- 提交详情弹窗 -->
    <SubmissionDetailModal
      v-if="showSubmissionDetailModal"
      :submission="selectedSubmission"
      @close="showSubmissionDetailModal = false"
    />

    <!-- V44: 删除确认弹窗 -->
    <CustomAlert
      :show="showDeleteConfirmModal"
      :title="isBatchDelete ? '批量删除确认' : '删除确认'"
      :message="isBatchDelete ? `确定要删除选中的 ${selectedPersons.size} 位人员吗？此操作不可恢复。` : `确定要删除「${deleteTargetPerson?.name}」吗？此操作不可恢复。`"
      type="error"
      confirm-text="确认删除"
      cancel-text="取消"
      :show-cancel="true"
      @confirm="executeDelete"
      @close="closeDeleteConfirmModal"
    />
      </div>
</template>

<style scoped>
.person-management {
  padding: 24px;
  min-height: 100vh;
  background: transparent;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #1d4ed8 100%);
  border-radius: 20px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.header-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: white;
}

.header-content h1 {
  font-size: 28px;
  font-weight: 700;
  color: white;
  margin: 0;
}

/* ===== V45: 现代化工具栏 - 飞书/Notion风格 ===== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  background: white;
  border-radius: 12px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  flex-wrap: wrap;
}

/* 搜索框 */
.toolbar-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  min-width: 220px;
  transition: all 0.2s;
}

.toolbar-search:focus-within {
  background: white;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.toolbar-search i {
  color: #9ca3af;
  font-size: 1rem;
}

.toolbar-search input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: #1f2937;
  outline: none;
}

.toolbar-search input::placeholder {
  color: #9ca3af;
}

/* 筛选器组 */
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* 筛选芯片 - 现代化设计 */
.filter-chip {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.8125rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-chip:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.filter-chip.active {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4f46e5;
}

.filter-chip.active i {
  color: #6366f1;
}

.filter-chip i {
  font-size: 0.875rem;
  color: #9ca3af;
}

.filter-chip select {
  border: none;
  background: transparent;
  font-size: 0.8125rem;
  color: inherit;
  cursor: pointer;
  outline: none;
  padding-right: 0.25rem;
  appearance: none;
  -webkit-appearance: none;
}

/* 视图切换 */
.toolbar-view {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: #f3f4f6;
  border-radius: 8px;
  margin-left: auto;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.view-btn:hover {
  color: #374151;
}

.view-btn.active {
  background: white;
  color: #6366f1;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.view-btn i {
  font-size: 1rem;
}

/* 操作按钮 */
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.action-btn.primary {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
}

.action-btn.primary:hover {
  background: #4f46e5;
  border-color: #4f46e5;
}

.action-btn.danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.action-btn.danger:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.action-btn.icon-only {
  padding: 0.5rem;
}

.action-btn.icon-only i {
  font-size: 1rem;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn i {
  font-size: 0.9375rem;
}

/* 保留旧样式兼容 */
.filter-select:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.08);
}

/* 按钮样式 - 简约风格 */
.btn-export {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 0.875rem;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-export:hover {
  background: #4f46e5;
}

.btn-export i {
  font-size: 0.9375rem;
}

.btn-refresh {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.4rem;
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-refresh:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
  color: #374151;
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-refresh i {
  font-size: 1rem;
}

/* 批量删除按钮 */
.btn-batch {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 0.875rem;
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-batch:hover {
  background: #f9fafb;
  border-color: #d1d5db;
  color: #374151;
}

.btn-batch i {
  font-size: 0.9375rem;
}

.btn-batch.active {
  background: #ef4444;
  color: white;
  border-color: #ef4444;
}

.btn-batch.active:hover {
  background: #dc2626;
  border-color: #dc2626;
}

/* V44: 批量操作栏 */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fecaca;
  border-radius: 10px;
  margin-bottom: 16px;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #64748b;
}

.select-all input {
  accent-color: #ef4444;
}

.selected-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: #ef4444;
}

.btn-delete-batch {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete-batch:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-delete-batch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 统计摘要 */
.stats-summary {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 2.5rem;
  padding: 1.25rem 1.5rem;
  background: white;
  border-radius: 16px;
  margin-bottom: 16px;
  flex-wrap: nowrap;
}

.summary-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  flex-direction: row;
  white-space: nowrap;
}

.summary-item i {
  font-size: 1.125rem;
  flex-shrink: 0;
}

.summary-item .summary-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  line-height: 1;
}

.summary-item .summary-label {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1;
}

.summary-item.active i {
  color: #f59e0b;
}

.summary-item.completed i {
  color: #10b981;
}

.summary-item.total i {
  color: #6366f1;
}

/* 内容卡片 */
.content-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* 表格 - 列表视图 */
.table-wrapper {
  overflow-x: auto;
}

.persons-table {
  width: 100%;
  border-collapse: collapse;
}

.persons-table thead {
  background: #f9fafb;
}

.persons-table th {
  padding: 0.875rem 1rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e5e7eb;
}

.persons-table td {
  padding: 1rem;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.875rem;
  color: #374151;
}

.person-row:hover {
  background: #faf5ff;
}

.person-row.selected {
  background: rgba(124, 58, 237, 0.05);
}

/* 分页控件样式 */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
  margin-top: 16px;
  background: rgba(124, 58, 237, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(124, 58, 237, 0.1);
}

.page-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: 8px;
  background: white;
  color: #7c3aed;
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled) {
  background: #7c3aed;
  color: white;
  border-color: #7c3aed;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  min-width: 120px;
  text-align: center;
}

/* V44: 复选框列 */
.cell-checkbox {
  width: 40px;
  text-align: center;
}

.cell-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #7c3aed;
}

/* V44: 操作列 */
.cell-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-action-delete {
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action-delete:hover {
  background: #ef4444;
  color: white;
}

/* 单元格样式 */
.cell-name {
  min-width: 180px;
}

.person-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.person-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
}

.person-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.person-detail .name {
  font-weight: 500;
  color: #1f2937;
}

.person-detail .email {
  font-size: 0.75rem;
  color: #9ca3af;
}

.cell-phone {
  color: #6b7280;
}

.cell-gender {
  text-align: center;
}

.gender-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.gender-tag.male {
  background: #eff6ff;
  color: #3b82f6;
}

.gender-tag.female {
  background: #fdf2f8;
  color: #ec4899;
}

.gender-tag i {
  font-size: 0.875rem;
}

.cell-position {
  color: #6b7280;
}

.no-data {
  color: #d1d5db;
}

.count-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #4b5563;
}

.cell-rate {
  min-width: 100px;
}

.progress-bar {
  width: 60px;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
  display: inline-block;
  vertical-align: middle;
  margin-right: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.rate-text {
  font-size: 0.75rem;
  color: #6b7280;
}

.cell-latest {
  min-width: 150px;
}

.latest-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.questionnaire-name {
  font-size: 0.8125rem;
  color: #374151;
}

.grade-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 600;
}

.grade-badge.grade-a {
  background: #d1fae5;
  color: #065f46;
}

.grade-badge.grade-b {
  background: #dbeafe;
  color: #1e40af;
}

.grade-badge.grade-c {
  background: #fef3c7;
  color: #92400e;
}

.grade-badge.grade-d {
  background: #fee2e2;
  color: #991b1b;
}

.no-data {
  color: #d1d5db;
}

.cell-time {
  color: #6b7280;
  font-size: 0.8125rem;
}

/* 分组视图 */
.grouped-view {
  padding: 1rem;
}

/* V45: 分组控制栏 - 类似专业测评 */
.grouped-controls {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.btn-toggle-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #4b5563;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-toggle-all:hover {
  background: #e5e7eb;
}

/* V45: 批量删除按钮 */
.btn-batch-select {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-batch-select:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-batch-select.active {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border-color: transparent;
}

/* V45: 批量操作栏 */
.batch-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #e9d5ff;
  border-radius: 10px;
  margin-bottom: 1rem;
}

.batch-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.select-all-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #6b7280;
}

.select-all-checkbox input {
  width: 16px;
  height: 16px;
  accent-color: #7c3aed;
  cursor: pointer;
}

.selected-count {
  font-size: 0.875rem;
  color: #7c3aed;
  font-weight: 600;
}

.batch-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-batch-delete {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-batch-delete:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-batch-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* V45: 分组卡片复选框 */
.group-checkbox {
  width: 18px;
  height: 18px;
  accent-color: #7c3aed;
  cursor: pointer;
  flex-shrink: 0;
  margin-right: 0.5rem;
}

.person-groups {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.person-group-card {
  background: #f9fafb;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.person-group-card.expanded {
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: background 0.2s;
}

.group-header:hover {
  background: rgba(124, 58, 237, 0.05);
}

.group-left {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.group-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  font-weight: 600;
}

.group-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.group-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.9375rem;
}

/* V45: 新的分组布局 */
.group-main {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  flex: 1;
}

.group-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.group-phone {
  font-size: 0.8125rem;
  color: #6b7280;
}

.group-stats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
}

.stat-badge.total {
  background: #ede9fe;
  color: #6d28d9;
}

.stat-badge.completed {
  background: #d1fae5;
  color: #059669;
}

.stat-badge.latest {
  background: #e0e7ff;
  color: #4338ca;
}

/* V44: 分组视图删除按钮 */
.btn-delete-group {
  padding: 0.375rem;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 0.5rem;
}

.btn-delete-group:hover {
  background: #fee2e2;
  color: #ef4444;
}

.expand-icon {
  font-size: 1.25rem;
  color: #9ca3af;
  transition: transform 0.2s;
}

.person-group-card.expanded .expand-icon {
  color: #7c3aed;
}

/* 展开的提交列表 */
.group-submissions {
  border-top: 1px solid #e5e7eb;
  padding: 0.5rem;
  background: white;
}

.no-submissions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: #9ca3af;
  font-size: 0.875rem;
}

.submission-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  transition: background 0.2s;
}

.submission-item:hover {
  background: #f9fafb;
}

.submission-order {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f3f4f6;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.submission-info {
  flex: 1;
  margin-left: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.submission-questionnaire {
  font-weight: 500;
  color: #374151;
  font-size: 0.875rem;
}

.submission-time {
  font-size: 0.75rem;
  color: #9ca3af;
}

.submission-result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 1rem;
}

.submission-result .score {
  font-weight: 600;
  color: #7c3aed;
  font-size: 0.875rem;
}

.submission-result .grade {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 600;
}

.submission-result .grade.grade-a {
  background: #d1fae5;
  color: #065f46;
}

.submission-result .grade.grade-b {
  background: #dbeafe;
  color: #1e40af;
}

.submission-result .grade.grade-c {
  background: #fef3c7;
  color: #92400e;
}

.submission-result .grade.grade-d {
  background: #fee2e2;
  color: #991b1b;
}

.status-mini {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 500;
}

.status-mini.completed {
  background: #d1fae5;
  color: #059669;
}

.status-mini.progress {
  background: #fef3c7;
  color: #d97706;
}

.submission-actions {
  display: flex;
  gap: 0.375rem;
}

.btn-mini {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-mini:hover {
  background: #7c3aed;
  color: white;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: #6b7280;
  gap: 1rem;
}

.loading-state i {
  font-size: 2rem;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: #9ca3af;
  gap: 1rem;
}

.empty-state i {
  font-size: 3rem;
}

/* 动画 */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spin {
  animation: spin 1s linear infinite;
}

/* 响应式 */
@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-left, .filter-right {
    flex-wrap: wrap;
  }
  
  .search-box input {
    min-width: 150px;
  }
  
  .stats-summary {
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .group-stats {
    display: none;
  }
}
</style>
