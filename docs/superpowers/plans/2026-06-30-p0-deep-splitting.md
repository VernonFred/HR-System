# P0 Deep Code Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce remaining P0 frontend files toward maintainable module sizes without changing user-visible behavior.

**Architecture:** Apply low-risk structural splits first: CSS entrypoints import focused part files, Vue templates move to external template files where supported, and shared page logic moves into local composables. Keep public component names, route names, API calls, and data contracts unchanged.

**Tech Stack:** Vue 3 SFC, Vite, TypeScript, CSS, npm build verification.

## Global Constraints

- Do not modify unrelated dirty files: `.DS_Store`, deleted zip artifacts, `frontend/src/views/SettingsPage.vue`, `人事画像系统-安装部署维护手册.md`.
- Do not change API paths, database schema, user-visible copy, routing, or exported data shape.
- Keep existing imports stable from calling components unless a local component split requires an internal import.
- Avoid TypeScript-only expressions in external `.template.html` files; move casts/helpers into `<script setup>`.
- Verification gate: run `cd frontend && npm run build`, `git diff --check`, and a maintained-code line-count scan before claiming completion.

---

### Task 1: CSS Deep Split

**Files:**
- Modify: `frontend/src/components/candidate/styles/portrait-card.css`
- Create: `frontend/src/components/candidate/styles/portrait-card.part-1.css` ... part files
- Modify: `frontend/src/views/styles/candidates-page.css`
- Create: `frontend/src/views/styles/candidates-page.part-1.css` ... part files
- Modify: `frontend/src/components/styles/submission-records-tab.css`
- Create: `frontend/src/components/styles/submission-records-tab.part-1.css` ... part files
- Modify: `frontend/src/views/styles/job-profiles-page.css`
- Create: `frontend/src/views/styles/job-profiles-page.part-1.css` ... part files
- Modify: `frontend/src/views/styles/user-management-page.css`
- Create: `frontend/src/views/styles/user-management-page.part-1.css` ... part files

**Interfaces:**
- Consumes: Existing CSS import statements in Vue files.
- Produces: Same CSS entrypoint filenames, now only containing ordered `@import` rules.

- [ ] **Step 1: Split CSS at rule boundaries**

Run a brace-depth splitter so `@media` and selector blocks are not cut in half:

```bash
python3 - <<'PY'
from pathlib import Path
# split each target at top-level CSS rule boundaries, target <= 650 lines per part
PY
```

- [ ] **Step 2: Verify CSS entrypoints remain stable**

Run:

```bash
for f in frontend/src/components/candidate/styles/portrait-card.css frontend/src/views/styles/candidates-page.css frontend/src/components/styles/submission-records-tab.css frontend/src/views/styles/job-profiles-page.css frontend/src/views/styles/user-management-page.css; do head -20 "$f"; done
```

Expected: only `@import './<name>.part-N.css';` lines in each entrypoint.

### Task 2: Low-Risk Template Extraction

**Files:**
- Modify: `frontend/src/components/SubmissionRecordsTab.vue`
- Create: `frontend/src/components/SubmissionRecordsTab.template.html`
- Modify: `frontend/src/views/JobProfilesPage.vue`
- Create: `frontend/src/views/JobProfilesPage.template.html`
- Modify: `frontend/src/views/UserManagementPage.vue`
- Create: `frontend/src/views/UserManagementPage.template.html`

**Interfaces:**
- Consumes: Existing SFC template blocks.
- Produces: Same component behavior using `<template src="..."></template>`.

- [ ] **Step 1: Move each `<template>` body unchanged**

Replace the component template with:

```vue
<template src="./ComponentName.template.html"></template>
```

Move only the inner HTML from the original `<template>` into the matching `.template.html` file.

- [ ] **Step 2: Check for external-template TypeScript casts**

Run:

```bash
rg "\sas\s|<template" frontend/src/components/SubmissionRecordsTab.template.html frontend/src/views/JobProfilesPage.template.html frontend/src/views/UserManagementPage.template.html
```

Expected: no TypeScript `as` casts inside external templates.

### Task 3: Candidate Portrait Template/Logic Split

**Files:**
- Modify: `frontend/src/components/candidate/CandidatePortraitCard.vue`
- Create: `frontend/src/components/candidate/CandidatePortraitCard.template.html`
- Create: `frontend/src/components/candidate/useCandidatePortraitExport.ts` if export logic can be moved without changing call signatures.

**Interfaces:**
- Consumes: Existing `CandidatePortraitCard.vue` props/emits and internal export handlers.
- Produces: Same component props/emits and same `exportPortraitAsImage` / `exportPortraitAsPdf` callable handlers in the template scope.

- [ ] **Step 1: Move template to external file**

Replace SFC template with:

```vue
<template src="./CandidatePortraitCard.template.html"></template>
```

- [ ] **Step 2: Extract export helpers only if the resulting component is still above target**

Keep function names exposed in script setup stable:

```ts
const { exportPortraitAsImage, exportPortraitAsPdf } = useCandidatePortraitExport({ portraitRef, props })
```

- [ ] **Step 3: Verify component line count target**

Run:

```bash
wc -l frontend/src/components/candidate/CandidatePortraitCard.vue frontend/src/components/candidate/CandidatePortraitCard.template.html
```

Expected: each file under roughly 700 lines; if not feasible without behavior changes, stop at the safe split and document remaining risk.

### Task 4: Questionnaire Detail Deep Split

**Files:**
- Modify: `frontend/src/components/QuestionnaireDetailDrawer.vue`
- Modify: `frontend/src/components/QuestionnaireDetailDrawer.template.html`
- Create: `frontend/src/components/questionnaire-detail/useQuestionnaireStatsExport.ts` if export functions can be moved cleanly.
- Create focused components only when they consume simple props and do not require broad parent state mutation.

**Interfaces:**
- Consumes: Existing statistics data, `questionStats`, `exportingStats`, `exportReportRef`, and export functions.
- Produces: Same visible statistics export controls and same PDF/PNG/Excel behavior.

- [ ] **Step 1: Identify export-only functions and template-only report blocks**

Run:

```bash
rg -n "exportStats|exportReport|statsExport|download|PDF|PNG|Excel|xlsx|jsPDF" frontend/src/components/QuestionnaireDetailDrawer.vue frontend/src/components/QuestionnaireDetailDrawer.template.html
```

- [ ] **Step 2: Move pure export helpers to a composable if dependencies are narrow**

The composable must return the same callable names used by the template. If dependencies are broad, defer the extraction and only split template blocks that are safe.

- [ ] **Step 3: Avoid forced componentization of tightly coupled template blocks**

If a block requires many parent refs and event handlers, keep it in the parent until a dedicated behavior refactor can be tested.

### Task 5: Verification

**Files:**
- No source changes unless verification reveals a compile error.

**Interfaces:**
- Produces: Build evidence and remaining line-count report.

- [ ] **Step 1: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: exit code 0.

- [ ] **Step 2: Check whitespace and patch hygiene**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 3: Re-scan maintained files**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
# print maintained source files above 700 lines and target P0 files
PY
```

Expected: P0 files are reduced materially; any remaining >700 are explicitly listed with reason.
