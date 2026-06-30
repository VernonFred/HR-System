# P0 Code Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reduce every P0 project-maintained file below the P0 threshold of 2000 lines without changing user-visible behavior.

**Architecture:** Prefer structural extraction over behavioral rewrites. Move large inline Vue styles into adjacent CSS files, split already-large CSS bundles into imported section files, and extract only low-risk helper logic from `CandidatePortraitCard.vue` because it is the only P0 Vue file already using external CSS.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, scoped CSS imports, Vite build.

## Global Constraints

- P0 threshold is `> 2000` lines; this phase only needs to eliminate P0 files.
- Do not touch unrelated dirty files: `.DS_Store`, zip deletions, `frontend/src/views/SettingsPage.vue`, and `人事画像系统-安装部署维护手册.md`.
- Do not change route paths, API contracts, database fields, or production behavior.
- Prefer moving existing code verbatim over rewriting logic.
- Verify with line-count scan and `npm run build` before claiming completion.

---

### Task 1: Externalize large inline styles from P0 Vue files

**Files:**
- Modify: `frontend/src/views/CandidatesPage.vue`
- Create: `frontend/src/views/styles/candidates-page.css`
- Modify: `frontend/src/components/SubmissionRecordsTab.vue`
- Create: `frontend/src/components/styles/submission-records-tab.css`
- Modify: `frontend/src/views/JobProfilesPage.vue`
- Create: `frontend/src/views/styles/job-profiles-page.css`
- Modify: `frontend/src/views/UserManagementPage.vue`
- Create: `frontend/src/views/styles/user-management-page.css`

**Interfaces:**
- Consumes: existing scoped style selectors inside each Vue file.
- Produces: same selectors via `<style scoped>@import ...</style>`.

- [x] Move each full `<style scoped>` body into the matching CSS file.
- [x] Replace each style block with a single scoped `@import`.
- [x] Do not change selectors or declarations while moving.
- [x] Run a line-count scan for the four Vue files.

### Task 2: Split P0 standalone CSS bundles

**Files:**
- Modify: `frontend/src/components/styles/questionnaire-detail-drawer.css`
- Create: `frontend/src/components/styles/questionnaire-detail-drawer.base.css`
- Create: `frontend/src/components/styles/questionnaire-detail-drawer.submissions.css`
- Create: `frontend/src/components/styles/questionnaire-detail-drawer.statistics.css`
- Create: `frontend/src/components/styles/questionnaire-detail-drawer.export.css`
- Create: `frontend/src/components/styles/questionnaire-detail-drawer.responsive.css`
- Modify: `frontend/src/views/styles/professional-assessment.css`
- Create: `frontend/src/views/styles/professional-assessment.layout.css`
- Create: `frontend/src/views/styles/professional-assessment.records.css`
- Create: `frontend/src/views/styles/professional-assessment.responsive.css`
- Modify: `frontend/src/components/styles/distribute-modal.css`
- Create: `frontend/src/components/styles/distribute-modal.base.css`
- Create: `frontend/src/components/styles/distribute-modal.form.css`
- Create: `frontend/src/components/styles/distribute-modal.routing.css`
- Create: `frontend/src/components/styles/distribute-modal.success.css`
- Create: `frontend/src/components/styles/distribute-modal.responsive.css`

**Interfaces:**
- Consumes: existing class selectors and import paths.
- Produces: existing public CSS entry files that only import section files.

- [x] Split CSS by selector ranges, preserving order.
- [x] Keep original public CSS filenames as import entrypoints.
- [x] Ensure each produced file is below 2000 lines.
- [x] Run a line-count scan for the split CSS files.

### Task 3: Reduce CandidatePortraitCard.vue below P0

**Files:**
- Modify: `frontend/src/components/candidate/CandidatePortraitCard.vue`

**Interfaces:**
- Consumes: existing export, resume, and portrait-generation behavior.
- Produces: same component behavior with unused dead code removed.

- [x] Confirm whether `prepareClonedDocForExport` and `html2canvas` are actually referenced.
- [x] Remove the unused export-preparation block when no call sites exist.
- [x] Keep existing PNG/PDF/Word export handlers unchanged.
- [x] Run a line-count scan for `CandidatePortraitCard.vue`.

### Task 4: Verification

**Files:**
- Modify only if verification identifies a direct regression.

- [x] Run the P0 scan and confirm zero P0 files remain in maintained project code.
- [x] Run `cd frontend && npm run build` and require exit code 0.
- [x] Run `git status --short` and confirm unrelated dirty files remain unstaged.
