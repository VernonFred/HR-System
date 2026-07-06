import assert from 'node:assert/strict'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'

const root = process.cwd()
const outDir = mkdtempSync(join(tmpdir(), 'scoring-display-'))

try {
  const compile = spawnSync(
    join(root, 'node_modules/.bin/tsc'),
    [
      'src/utils/scoringDisplayConfig.ts',
      '--target', 'ES2020',
      '--module', 'ES2020',
      '--moduleResolution', 'Node',
      '--outDir', outDir,
      '--skipLibCheck',
      '--esModuleInterop',
    ],
    { cwd: root, encoding: 'utf8' },
  )

  if (compile.status !== 0) {
    console.error(compile.stdout)
    console.error(compile.stderr)
    process.exit(compile.status ?? 1)
  }

  const {
    buildScoringDisplayConfig,
    createDefaultDisplayConfig,
    getDistributionRows,
  } = await import(pathToFileURL(join(outDir, 'scoringDisplayConfig.js')).href)

  const survey = createDefaultDisplayConfig('survey')
  assert.equal(survey.distributionTitle, '课程评价分布')
  assert.equal(survey.rateLabel, '高认可率')
  assert.equal(survey.unitLabel, '份答卷')

  const assessment = createDefaultDisplayConfig('assessment')
  assert.equal(assessment.distributionTitle, '测评等级分布')
  assert.equal(assessment.rateLabel, '优良率')
  assert.equal(assessment.unitLabel, '人')

  const custom = buildScoringDisplayConfig({
    purpose: 'survey',
    scoringConfig: {
      displayConfig: {
        preset: 'custom',
        distributionTitle: '服务反馈分布',
        rateLabel: '满意率',
        unitLabel: '份反馈',
        averageLabel: '服务综合评分',
      },
    },
  })
  assert.equal(custom.distributionTitle, '服务反馈分布')
  assert.equal(custom.rateLabel, '满意率')
  assert.equal(custom.unitLabel, '份反馈')
  assert.equal(custom.averageLabel, '服务综合评分')

  const rows = getDistributionRows(
    {
      displayConfig: { preset: 'custom' },
      gradeConfig: [
        { grade: 'A', label: '高度认可', minScore: 90, maxScore: 100 },
        { grade: 'B', label: '整体满意', minScore: 75, maxScore: 89 },
      ],
    },
    { A: 3, B: 2, C: 0, D: 0 },
  )
  assert.deepEqual(rows.map(row => row.label), ['高度认可', '整体满意'])
  assert.deepEqual(rows.map(row => row.count), [3, 2])

  const legacySurveyRows = getDistributionRows(
    {
      gradeConfig: [
        { grade: 'A', label: '优秀', minScore: 90, maxScore: 100 },
        { grade: 'B', label: '良好', minScore: 75, maxScore: 89 },
      ],
    },
    { A: 1, B: 2 },
    'survey',
  )
  assert.deepEqual(legacySurveyRows.map(row => row.label), ['高度认可', '整体满意'])
  assert.deepEqual(legacySurveyRows.map(row => `${row.minScore}-${row.maxScore}`), ['90-100', '75-89'])

  console.log('scoring display config tests passed')
} finally {
  rmSync(outDir, { recursive: true, force: true })
}
