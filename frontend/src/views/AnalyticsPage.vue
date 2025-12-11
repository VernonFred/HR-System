<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import HeaderBar from "../components/HeaderBar.vue";
import EChartContainer from "../components/EChartContainer.vue";
import { fetchAnalyticsSummary } from "../api/analytics";
import type { AnalyticsSummary } from "../types/analytics";
import type { EChartsOption } from "echarts/core";
import { gradeFromScore } from "../types/grade";
import { getReport } from "../apis/ai";

const loading = ref(false);
const errorMsg = ref("");
const analytics = ref<AnalyticsSummary | null>(null);
const reportLoading = ref(false);
const reportMarkdown = ref("");

const loadAnalytics = async () => {
  loading.value = true;
  errorMsg.value = "";
  try {
    analytics.value = await fetchAnalyticsSummary();
  } catch (err) {
    errorMsg.value = (err as Error).message || "加载分析数据失败";
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadAnalytics();
});

const matchRadar = computed<EChartsOption>(() => {
  if (!analytics.value) return {};
  return {
    tooltip: {},
    legend: {
      data: analytics.value.radarSeries.map((s) => s.name),
      textStyle: { color: "#cbd5e1" },
    },
    radar: {
      indicator: analytics.value.radarIndicators,
      radius: 80,
    },
    series: [
      {
        type: "radar",
        data: analytics.value.radarSeries,
      },
    ],
  };
});

const personalityPie = computed<EChartsOption>(() => ({
  tooltip: { trigger: "item" },
  legend: { orient: "vertical", left: "left", textStyle: { color: "#cbd5e1" } },
  series: [
    {
      type: "pie",
      radius: "60%",
      data: analytics.value?.personalityPie || [],
    },
  ],
}));

const competitiveBar = computed<EChartsOption>(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
  xAxis: { type: "value", boundaryGap: [0, 0.01], axisLabel: { color: "#cbd5e1" } },
  yAxis: {
    type: "category",
    data: (analytics.value?.positionDistribution || []).map((i) => i.name),
    axisLabel: { color: "#cbd5e1" },
  },
  series: [
    {
      name: "匹配度",
      type: "bar",
      data: (analytics.value?.positionDistribution || []).map((i) => i.value),
      itemStyle: { color: "#6366f1" },
    },
  ],
}));

const dimensionLine = computed<EChartsOption>(() => ({
  tooltip: { trigger: "axis" },
  legend: {
    data: (analytics.value?.dimensionTrendSeries || []).map((s) => s.name),
    textStyle: { color: "#cbd5e1" },
  },
  grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
  xAxis: {
    type: "category",
    data: analytics.value?.dimensionTrendLabels || [],
    axisLabel: { color: "#cbd5e1" },
  },
  yAxis: { type: "value", axisLabel: { color: "#cbd5e1" } },
  series: (analytics.value?.dimensionTrendSeries || []).map((s) => ({
    name: s.name,
    type: "line",
    data: s.data,
  })),
}));

const generateReport = async () => {
  if (!analytics.value) return;
  reportLoading.value = true;
  reportMarkdown.value = "";
  try {
    const res = await getReport({
      submission_code: "summary",
      scores: analytics.value,
      test_type: "EPQ",
    });
    reportMarkdown.value = res.markdown || "AI 暂不可用";
  } catch (err) {
    reportMarkdown.value = "AI 暂不可用";
  } finally {
    reportLoading.value = false;
  }
};
</script>

<template>
  <div class="analytics">
    <HeaderBar title="分析中心" subtitle="支持后端/Mock 统计，等级映射随量表配置" />

    <div class="summary" v-if="analytics">
      <div class="summary-item">
        <div class="summary-label">候选人总数</div>
        <div class="summary-value">{{ analytics.totalCandidates || 0 }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">平均分</div>
        <div class="summary-value">{{ analytics.avgScore ?? "--" }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">等级阈值</div>
        <div class="summary-value">
          <span class="badge" v-for="(v, k) in analytics.gradeCutoffs" :key="k">{{ k }} ≥ {{ v }}</span>
        </div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="card">
        <div class="card-header"><h3 class="card-title">岗位匹配度</h3></div>
        <div class="card-body">
          <EChartContainer :option="matchRadar" />
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3 class="card-title">竞争力排名</h3></div>
        <div class="card-body">
          <EChartContainer :option="competitiveBar" />
        </div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="card">
        <div class="card-header"><h3 class="card-title">人格分布</h3></div>
        <div class="card-body">
          <EChartContainer :option="personalityPie" />
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3 class="card-title">维度对比</h3></div>
        <div class="card-body">
          <EChartContainer :option="dimensionLine" />
        </div>
      </div>
    </div>

    <div class="card" v-if="analytics">
      <div class="card-header"><h3 class="card-title">评分等级</h3></div>
      <div class="card-body grades">
        <div v-for="s in analytics.radarSeries" :key="s.name" class="grade-row">
          <div class="grade-name">{{ s.name }}</div>
          <div class="grade-badges">
            <span
              class="badge"
              v-for="(val, idx) in s.value"
              :key="idx"
            >
              {{ analytics.radarIndicators[idx]?.name }}:
              {{ gradeFromScore(val, analytics.gradeCutoffs || { A: 85, B: 70, C: 55 }) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header flex">
        <h3 class="card-title">AI 综合报告</h3>
        <button class="btn-primary ghost" :disabled="reportLoading" @click="generateReport">
          {{ reportLoading ? "生成中..." : "生成报告" }}
        </button>
      </div>
      <div class="card-body">
        <pre v-if="reportMarkdown" class="markdown">{{ reportMarkdown }}</pre>
        <div v-else class="note">点击生成后显示报告（失败时显示占位）。</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analytics {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-3);
}

.card {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
}

.card-body {
  padding: var(--space-4);
}
.flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.markdown {
  white-space: pre-wrap;
  background: var(--bg-subtle);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}
.summary-item {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
}
.summary-label {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
.summary-value {
  font-weight: 700;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.badge {
  padding: 4px 8px;
  border-radius: var(--radius-full);
  background: rgba(99, 102, 241, 0.12);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.grades {
  display: grid;
  gap: var(--space-3);
}

.grade-row {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  align-items: center;
}

.grade-name {
  font-weight: 700;
}

.grade-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 8px;
  border-radius: var(--radius-full);
  background: rgba(99, 102, 241, 0.12);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
</style>
