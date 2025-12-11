<script setup lang="ts">
import HeaderBar from "../components/HeaderBar.vue";
</script>

<template>
  <div class="resumes">
    <HeaderBar title="简历中心" subtitle="保持旧版体验，等待文件上传与解析 API 接入" />
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">简历库</h3>
        <button class="btn-primary ghost"><i class="ri-upload-line"></i> 上传简历</button>
      </div>
      <div class="card-body">
        <div class="empty">
          <i class="ri-file-text-line"></i>
          <h4>简历功能开发中</h4>
          <p>即将支持 PDF/图片简历上传和 AI 解析</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.resumes {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
}

.card-body {
  padding: var(--space-5);
}

.btn-primary {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  cursor: pointer;
  background: var(--gradient-primary);
  color: #fff;
  border-color: transparent;
}

.btn-primary.ghost {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-primary);
  border-color: rgba(99, 102, 241, 0.3);
}

.empty {
  display: grid;
  place-items: center;
  gap: var(--space-2);
  color: var(--text-tertiary);
  text-align: center;
}

.empty i {
  font-size: 36px;
  color: var(--text-muted);
}
</style>
