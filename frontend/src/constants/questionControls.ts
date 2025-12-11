/**
 * 问卷控件库配置
 * 定义可用的题目类型及其属性
 */

export interface QuestionControl {
  type: string;
  label: string;
  icon: string;
}

export const questionControls: QuestionControl[] = [
  { type: 'radio', label: '单选题', icon: 'ri-radio-button-line' },
  { type: 'checkbox', label: '多选题', icon: 'ri-checkbox-line' },
  { type: 'text', label: '单行文本', icon: 'ri-input-method-line' },
  { type: 'textarea', label: '多行文本', icon: 'ri-text' },
  { type: 'scale', label: '量表题', icon: 'ri-bar-chart-horizontal-line' },
  { type: 'yesno', label: '是非题', icon: 'ri-question-answer-line' },
  { type: 'choice', label: '二选一', icon: 'ri-arrow-left-right-line' },
];

export default questionControls;

