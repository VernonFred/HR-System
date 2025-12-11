/**
 * 画像导出 Composable
 * 提供导出状态管理和基础工具函数
 * 
 * 注意：完整的导出逻辑（包括 prepareClonedDocForExport）
 * 目前保留在 CandidatePortraitCard.vue 组件内部，
 * 因为它依赖于组件内的特定样式和状态
 */
import { ref } from 'vue';

/**
 * 导出 Composable
 * 管理导出状态
 */
export function usePortraitExport() {
  const isExporting = ref(false);
  const showExportMenu = ref(false);

  /**
   * 开始导出
   */
  const startExport = () => {
    isExporting.value = true;
    showExportMenu.value = false;
  };

  /**
   * 结束导出
   */
  const endExport = () => {
    isExporting.value = false;
  };

  /**
   * 切换导出菜单
   */
  const toggleExportMenu = () => {
    showExportMenu.value = !showExportMenu.value;
  };

  /**
   * 关闭导出菜单
   */
  const closeExportMenu = () => {
    showExportMenu.value = false;
  };

  return {
    isExporting,
    showExportMenu,
    startExport,
    endExport,
    toggleExportMenu,
    closeExportMenu,
  };
}

export default usePortraitExport;
