<script setup lang="ts">
import { ref } from 'vue'
import type {
  Questionnaire,
  QuestionnaireQuestionStats,
  QuestionOptionStat,
  QuestionStat,
  Submission,
} from '../../api/assessments'

type GradeDistribution = { A: number; B: number; C: number; D: number }
type TrendDay = { date: string; count: number }
type TextAnswerItem = { text: string; count: number }

defineProps<{
  questionnaire: Questionnaire | null
  questionStats: QuestionnaireQuestionStats | null
  actualSubmissionCount: number
  isScored: boolean
  completedSubmissions: Submission[]
  gradeDistribution: GradeDistribution
  highScoreRate: number
  averageScore: number
  trendRangeLabel: string
  trendSeries: TrendDay[]
  statsExportChartImages: Record<string, string>
  getExportDateText: () => string
  getGradeCount: (grade: string) => number
  getGradePercent: (grade: string) => number
  getGradePercentLabel: (grade: string) => number
  formatTrendDate: (date: string) => string
  isTextQuestion: (type: string) => boolean
  getQuestionVisualLabel: (question: QuestionStat) => string
  getQuestionExportChartKey: (question: QuestionStat) => string
  getQuestionVisualMode: (question: QuestionStat) => string
  getQuestionOptionColor: (index: number) => string
  normalizePercentage: (percentage?: number) => number
  getQuestionExportOptionWidth: (question: QuestionStat, option: QuestionOptionStat) => number
  getSortedQuestionOptions: (question: QuestionStat) => QuestionOptionStat[]
  getTextTags: (question: QuestionStat) => TextAnswerItem[]
  getTextEmptyCount: (question: QuestionStat) => number
  getTextLongAnswers: (question: QuestionStat) => TextAnswerItem[]
}>()

const reportElementRef = ref<HTMLElement | null>(null)

defineExpose({
  getElement: () => reportElementRef.value,
})
</script>

<template>
<div class="stats-export-stage" aria-hidden="true">
<article ref="reportElementRef" class="stats-export-report">
    <section class="stats-export-hero">
      <div>
        <span class="stats-export-kicker">TalentLens 问卷统计报告</span>
        <h1>{{ questionnaire?.name || questionStats?.questionnaire_name || '问卷统计' }}</h1>
        <p>导出时间：{{ getExportDateText() }} · 趋势范围：{{ trendRangeLabel }}</p>
      </div>
      <div class="stats-export-logo">
        <i class="ri-bar-chart-grouped-line"></i>
      </div>
    </section>

    <section class="stats-export-section">
      <div class="stats-export-section-title">
        <h2>核心概览</h2>
        <span>{{ actualSubmissionCount }} 份提交</span>
      </div>
      <div class="stats-export-overview">
        <div class="stats-export-metric">
          <span>参与人数</span>
          <strong>{{ actualSubmissionCount }}</strong>
        </div>
        <div class="stats-export-metric">
          <span>完成率</span>
          <strong>{{ actualSubmissionCount > 0 ? (questionStats?.completion_rate ?? 100) : 0 }}%</strong>
        </div>
        <div class="stats-export-metric">
          <span>{{ isScored ? '优良率' : '题目数' }}</span>
          <strong>{{ isScored ? `${highScoreRate}%` : (questionStats?.questions?.length || 0) }}</strong>
        </div>
        <div class="stats-export-metric">
          <span>平均用时</span>
          <strong>{{ questionStats?.average_duration_minutes ? `${questionStats.average_duration_minutes}分钟` : '-' }}</strong>
        </div>
      </div>
    </section>

    <section v-if="isScored && completedSubmissions.length > 0" class="stats-export-section">
      <div class="stats-export-section-title">
        <h2>得分分布</h2>
        <span>按等级汇总</span>
      </div>
      <div class="stats-export-grade-list">
        <div
          v-for="gradeInfo in [
            { grade: 'A', label: '优秀', color: '#10b981' },
            { grade: 'B', label: '良好', color: '#3b82f6' },
            { grade: 'C', label: '及格', color: '#f59e0b' },
            { grade: 'D', label: '待提升', color: '#ef4444' }
          ]"
          :key="`export-grade-${gradeInfo.grade}`"
          class="stats-export-grade-row"
        >
          <div class="stats-export-grade-label" :style="{ color: gradeInfo.color }">
            <strong>{{ gradeInfo.grade }}</strong>
            <span>{{ gradeInfo.label }}</span>
          </div>
          <div class="stats-export-grade-track">
            <div
              class="stats-export-grade-fill"
              :style="{
                width: completedSubmissions.length > 0
                  ? `${getGradePercent(gradeInfo.grade)}%`
                  : '0%',
                background: gradeInfo.color
              }"
            ></div>
          </div>
          <div class="stats-export-grade-count">
            {{ getGradeCount(gradeInfo.grade) }}人
          </div>
        </div>
      </div>
    </section>

    <section v-if="trendSeries.length > 0" class="stats-export-section">
      <div class="stats-export-section-title">
        <h2>提交趋势</h2>
        <span>{{ trendRangeLabel }}</span>
      </div>
      <div class="stats-export-trend">
        <div
          v-for="day in trendSeries"
          :key="`export-trend-${day.date}`"
          class="stats-export-trend-item"
        >
          <div class="stats-export-trend-bar-wrap">
            <div
              class="stats-export-trend-bar"
              :style="{ height: getTrendBarHeight(day.count) }"
            ></div>
          </div>
          <strong>{{ day.count }}</strong>
          <span>{{ formatTrendDate(day.date) }}</span>
        </div>
      </div>
    </section>

    <section v-if="questionStats?.questions && questionStats.questions.length > 0" class="stats-export-section">
      <div class="stats-export-section-title">
        <h2>题目分析</h2>
        <span>共 {{ questionStats.questions.length }} 题，已导出全部题目</span>
      </div>

      <div class="stats-export-question-list">
        <div
          v-for="q in questionStats.questions"
          :key="`export-question-${q.id}`"
          class="stats-export-question-card"
        >
          <div class="stats-export-question-head">
            <span class="question-index">Q{{ q.index }}</span>
            <div>
              <h3>{{ q.text }}</h3>
              <p>{{ getQuestionTypeLabel(q.type) }} · {{ getQuestionResponseText(q) }}</p>
            </div>
          </div>

          <div class="stats-export-question-body" :class="{ 'is-text': isTextQuestion(q.type) }">
            <template v-if="!isTextQuestion(q.type)">
              <div class="stats-export-chart-box">
                <div class="chart-mode-label">{{ getQuestionVisualLabel(q) }}</div>
                <div v-if="q.options.length > 0 && statsExportChartImages[getQuestionExportChartKey(q)]" class="stats-export-chart-image-wrap">
                  <img
                    class="stats-export-chart-image"
                    :src="statsExportChartImages[getQuestionExportChartKey(q)]"
                    :alt="`Q${q.index} ${getQuestionVisualLabel(q)}`"
                  />
                </div>
                <div v-else-if="q.options.length > 0" class="stats-export-static-chart">
                  <div
                    v-for="(opt, optIndex) in q.options"
                    :key="`export-static-${q.id}-${opt.index ?? opt.text}`"
                    class="stats-export-static-row"
                  >
                    <div class="stats-export-static-head">
                      <span class="stats-export-static-label">
                        <i :style="{ background: getQuestionOptionColor(optIndex) }"></i>
                        {{ opt.text }}
                      </span>
                      <strong>{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</strong>
                    </div>
                    <div class="stats-export-static-track">
                      <div
                        class="stats-export-static-fill"
                        :style="{
                          width: `${getQuestionExportOptionWidth(q, opt)}%`,
                          background: getQuestionOptionColor(optIndex)
                        }"
                      ></div>
                    </div>
                  </div>
                </div>
                <div v-if="q.options.length > 0 && getQuestionVisualMode(q) === 'pie'" class="stats-export-chart-legend-list">
                  <div
                    v-for="(opt, optIndex) in q.options"
                    :key="`export-legend-${q.id}-${opt.index ?? opt.text}`"
                    class="stats-export-chart-legend-item"
                  >
                    <span class="chart-legend-dot" :style="{ background: getQuestionOptionColor(optIndex) }"></span>
                    <span class="chart-legend-text">{{ opt.text }}</span>
                    <span class="chart-legend-value">{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</span>
                  </div>
                </div>
                <div v-if="q.options.length === 0" class="empty-option-chart">暂无统计数据</div>
              </div>

              <div class="stats-export-detail-box">
                <div class="detail-panel-title">
                  <span>选项明细</span>
                  <em>{{ getQuestionResponseText(q) }}</em>
                </div>
                <div class="option-detail-list">
                  <div class="option-detail-row" v-for="opt in getSortedQuestionOptions(q)" :key="`export-opt-${q.id}-${opt.index ?? opt.text}`">
                    <div class="option-detail-head">
                      <span class="option-text">{{ opt.text }}</span>
                      <span class="option-stats">{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</span>
                    </div>
                    <div class="option-track">
                      <div class="option-fill" :style="{ width: `${normalizePercentage(opt.percentage)}%` }"></div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <template v-else>
              <div class="stats-export-detail-box">
                <div class="detail-panel-title">
                  <span>关键词汇总</span>
                  <em>{{ q.total_answers }} 条回答</em>
                </div>
                <div v-if="getTextTags(q).length > 0 || getTextEmptyCount(q) > 0" class="text-answer-tags">
                  <span
                    v-for="(tag, idx) in getTextTags(q)"
                    :key="`export-tag-${q.id}-${idx}`"
                    class="text-tag"
                  >
                    {{ tag.text }} <em>×{{ tag.count }}</em>
                  </span>
                  <span v-if="getTextEmptyCount(q) > 0" class="text-tag muted">
                    无/没有意见 <em>×{{ getTextEmptyCount(q) }}</em>
                  </span>
                </div>
                <div v-else class="empty-option-chart">暂无关键词汇总</div>
              </div>

              <div class="stats-export-detail-box">
                <div class="detail-panel-title">
                  <span>代表性回答</span>
                  <em>全部聚合回答</em>
                </div>
                <div v-if="getTextLongAnswers(q).length > 0" class="stats-export-text-list">
                  <div
                    v-for="(ans, idx) in getTextLongAnswers(q)"
                    :key="`export-answer-${q.id}-${idx}`"
                    class="text-answer-item"
                  >
                    "{{ ans.text }}"
                    <span class="text-answer-count-badge">×{{ ans.count }}</span>
                  </div>
                </div>
                <div v-else class="empty-option-chart">暂无文本回答</div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>
  </article>
</div>

</template>
