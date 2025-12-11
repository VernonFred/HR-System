/**
 * 自定义弹窗系统 Composable
 * 提供消息提示和确认弹窗功能
 */

import { ref } from 'vue';

/**
 * 消息类型
 */
export type MessageType = 'success' | 'error' | 'warning' | 'info';

/**
 * 消息弹窗状态
 */
export interface MessageDialogState {
  visible: boolean;
  type: MessageType;
  title: string;
  message: string;
}

/**
 * 确认弹窗状态
 */
export interface ConfirmDialogState {
  visible: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
}

/**
 * 自定义弹窗 Composable
 */
export function useCustomDialog() {
  // 消息弹窗状态
  const messageDialog = ref<MessageDialogState>({
    visible: false,
    type: 'success',
    title: '',
    message: '',
  });

  // 确认弹窗状态
  const confirmDialog = ref<ConfirmDialogState>({
    visible: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  // 消息类型对应的标题
  const typeTitles: Record<MessageType, string> = {
    success: '成功',
    error: '错误',
    warning: '警告',
    info: '提示',
  };

  /**
   * 显示消息提示
   */
  const showMessage = (message: string, type: MessageType = 'success') => {
    messageDialog.value = {
      visible: true,
      type,
      title: typeTitles[type],
      message,
    };
  };

  /**
   * 关闭消息弹窗
   */
  const closeMessageDialog = () => {
    messageDialog.value.visible = false;
  };

  /**
   * 显示确认弹窗
   * @returns Promise<boolean> - true表示确认，false表示取消
   */
  const showConfirm = (title: string, message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      confirmDialog.value = {
        visible: true,
        title,
        message,
        onConfirm: () => {
          confirmDialog.value.visible = false;
          resolve(true);
        },
      };
    });
  };

  /**
   * 关闭确认弹窗（取消操作）
   */
  const closeConfirmDialog = () => {
    confirmDialog.value.visible = false;
  };

  return {
    // 状态
    messageDialog,
    confirmDialog,
    // 方法
    showMessage,
    closeMessageDialog,
    showConfirm,
    closeConfirmDialog,
  };
}

