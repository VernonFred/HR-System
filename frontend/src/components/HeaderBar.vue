<script setup lang="ts">
const props = defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <header class="main-header">
    <div>
      <h1 class="page-title">{{ props.title }}</h1>
      <p v-if="props.subtitle" class="page-subtitle">{{ props.subtitle }}</p>
    </div>
  </header>
</template>

<style scoped>
.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: 700;
}

.page-subtitle {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

</style>
