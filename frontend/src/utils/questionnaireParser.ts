/**
 * 问卷解析工具函数
 * 用于导入问卷时解析文本格式
 */

export interface ParsedQuestion {
  id: string;
  type: string;
  text: string;
  required: boolean;
  options: { value: string; label: string }[];
}

/**
 * 解析带选项的文本格式
 * 支持多种格式：
 * 1. 标准格式：题目后跟选项
 *    1. 题目文本
 *    A. 选项1
 *    B. 选项2
 * 
 * 2. 简单格式：每行一题（自动生成选项）
 */
export const parseTextWithOptions = (text: string): ParsedQuestion[] => {
  const lines = text.split('\n').map(line => line.trim()).filter(line => line);
  const questions: ParsedQuestion[] = [];
  
  let currentQuestion: ParsedQuestion | null = null;
  let questionIndex = 0;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // 检测选项行：A. B. C. D. 或 A、B、C、D、或 A) B) C) D)
    const optionMatch = line.match(/^([A-Za-z])[.、)]\s*(.+)/);
    
    if (optionMatch) {
      // 这是一个选项
      if (currentQuestion) {
        currentQuestion.options.push({
          value: optionMatch[1].toUpperCase(),
          label: optionMatch[2].trim()
        });
      }
    } else {
      // 这是一个题目
      // 保存之前的题目
      if (currentQuestion) {
        // 如果没有选项，添加默认选项
        if (currentQuestion.options.length === 0) {
          currentQuestion.options = getDefaultOptions();
        }
        questions.push(currentQuestion);
      }
      
      // 清理题目文本：去除序号前缀
      let questionText = line
        .replace(/^\d+[.、)：:]\s*/, '')  // 去掉数字序号
        .replace(/^[（(]\d+[)）]\s*/, '') // 去掉括号序号
        .replace(/^第\d+题[.、：:]?\s*/, '') // 去掉"第N题"
        .trim();
      
      if (questionText) {
        questionIndex++;
        currentQuestion = {
          id: `import_${questionIndex}`,
          type: 'radio',
          text: questionText,
          required: true,
          options: []
        };
      }
    }
  }
  
  // 保存最后一个题目
  if (currentQuestion) {
    if (currentQuestion.options.length === 0) {
      currentQuestion.options = getDefaultOptions();
    }
    questions.push(currentQuestion);
  }
  
  return questions;
};

/**
 * 获取默认选项（用于没有显式定义选项的题目）
 */
export const getDefaultOptions = (): { value: string; label: string }[] => {
  return [
    { value: 'A', label: '非常同意' },
    { value: 'B', label: '同意' },
    { value: 'C', label: '不同意' },
    { value: 'D', label: '非常不同意' },
  ];
};

