/**
 * 报告模板 - 测评问卷和调查问卷报告HTML生成
 */

import { getDimensionLabel, getDISCLabel } from '../utils';

/**
 * 渲染答案HTML（用于PDF导出）
 */
export const renderAnswerForPDF = (answer: any): string => {
  const answerData = answer.answer || {};
  
  switch (answer.question_type) {
    case 'single_choice':
      return `
        <div style="padding: 10px 15px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 3px solid #4facfe; border-radius: 6px;">
          <span style="color: #1e3a8a; font-weight: 500;">✓ ${answerData.label || answerData.value || '未选择'}</span>
        </div>
      `;
    
    case 'multiple_choice':
      return `
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${(answerData.values || []).map((opt: string) => `
            <div style="padding: 10px 15px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 3px solid #4facfe; border-radius: 6px;">
              <span style="color: #1e3a8a; font-weight: 500;">✓ ${opt}</span>
            </div>
          `).join('')}
        </div>
      `;
    
    case 'scale':
      const scaleValue = answerData.value || 0;
      const stars = '★'.repeat(scaleValue) + '☆'.repeat(10 - scaleValue);
      return `
        <div style="padding: 12px 16px; background: linear-gradient(135deg, #fff7ed 0%, #fed7aa 100%); border-radius: 6px;">
          <div style="display: flex; align-items: center; gap: 15px;">
            <span style="font-size: 32px; font-weight: 700; color: #ea580c;">${scaleValue}</span>
            <span style="color: #9ca3af;">/ 10</span>
            <span style="color: #f59e0b; font-size: 20px;">${stars}</span>
          </div>
        </div>
      `;
    
    case 'short_text':
    case 'long_text':
      return `
        <div style="padding: 12px 16px; background: #f9fafb; border-left: 3px solid #9ca3af; border-radius: 6px; color: #374151; line-height: 1.6; white-space: pre-wrap; word-break: break-word;">
          ${answerData.value || '未填写'}
        </div>
      `;
    
    case 'yes_no':
      const isYes = answerData.boolean;
      return `
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 20px; font-weight: 600; ${isYes ? 'background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); color: #065f46;' : 'background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); color: #991b1b;'}">
          <span style="font-size: 18px;">${isYes ? '✓' : '✗'}</span>
          <span>${isYes ? '是' : '否'}</span>
        </div>
      `;
    
    case 'date':
      return `
        <div style="padding: 10px 15px; background: #f9fafb; border-radius: 6px;">
          <span style="color: #374151; font-weight: 500;">📅 ${answerData.date ? new Date(answerData.date).toLocaleDateString('zh-CN') : '未填写'}</span>
        </div>
      `;
    
    case 'nps':
      const npsValue = answerData.value || 0;
      let npsCategory = '';
      let npsColor = '';
      if (npsValue >= 9) {
        npsCategory = '推荐者';
        npsColor = '#065f46';
      } else if (npsValue >= 7) {
        npsCategory = '中立者';
        npsColor = '#92400e';
      } else {
        npsCategory = '贬损者';
        npsColor = '#991b1b';
      }
      return `
        <div style="padding: 12px 16px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 6px;">
          <div style="display: flex; align-items: center; gap: 15px;">
            <span style="font-size: 32px; font-weight: 700; color: #d97706;">${npsValue}</span>
            <span style="color: #9ca3af;">/ 10</span>
            <span style="padding: 4px 12px; border-radius: 12px; font-size: 14px; font-weight: 600; background: rgba(255,255,255,0.5); color: ${npsColor};">${npsCategory}</span>
          </div>
        </div>
      `;
    
    default:
      return `
        <div style="padding: 10px 15px; background: #f9fafb; border-radius: 6px; color: #666;">
          ${JSON.stringify(answerData)}
        </div>
      `;
  }
};

/**
 * 生成测评问卷报告HTML（MBTI/DISC/EPQ）
 */
export const generateAssessmentReportHTML = (submission: any): string => {
  const details = submission.result_details || {};
  
  let resultSection = '';
  
  // MBTI结果
  if (details.mbti_type) {
    resultSection = `
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="font-size: 48px; font-weight: bold;">${details.mbti_type}</div>
          <div>
            <div style="font-size: 24px; font-weight: bold;">${details.mbti_description || '建筑师'}</div>
            <div style="opacity: 0.9; margin-top: 5px;">MBTI人格类型测评</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #667eea; padding-left: 12px;">维度分析</h3>
        ${Object.entries(details.mbti_dimensions || {}).map(([key, dim]: [string, any]) => {
          const dimValue = typeof dim === 'object' ? dim.value : dim;
          const dimLabel = typeof dim === 'object' ? `${dim.tendency} - ${dim.label}` : '';
          return `
          <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-weight: 500; color: #555;">${getDimensionLabel(key)}${dimLabel ? ` (${dimLabel})` : ''}</span>
              <span style="font-weight: bold; color: #667eea;">${dimValue}%</span>
            </div>
            <div style="background: #f0f0f0; height: 12px; border-radius: 6px; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #667eea, #764ba2); height: 100%; width: ${dimValue}%; transition: width 0.3s;"></div>
            </div>
          </div>
        `}).join('')}
      </div>
    `;
  }
  
  // DISC结果
  if (details.disc_type) {
    const discDesc = details.disc_description || getDISCLabel(details.disc_type?.replace('型', ''));
    resultSection = `
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="font-size: 48px; font-weight: bold;">${details.disc_type}</div>
          <div>
            <div style="font-size: 24px; font-weight: bold;">${discDesc.replace(details.disc_type, '').replace(/^[\s\-:：]+/, '') || discDesc}</div>
            <div style="opacity: 0.9; margin-top: 5px;">DISC行为风格测评</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #f5576c; padding-left: 12px;">维度分析</h3>
        ${Object.entries(details.disc_dimensions || {}).map(([key, dim]: [string, any]) => {
          const dimValue = typeof dim === 'object' ? dim.value : dim;
          const dimLabel = typeof dim === 'object' ? dim.label : getDISCLabel(key);
          return `
          <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-weight: 500; color: #555;">${key}型 - ${dimLabel}</span>
              <span style="font-weight: bold; color: #f5576c;">${dimValue}%</span>
            </div>
            <div style="background: #f0f0f0; height: 12px; border-radius: 6px; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #f093fb, #f5576c); height: 100%; width: ${dimValue}%;"></div>
            </div>
          </div>
        `}).join('')}
      </div>
    `;
  }
  
  // EPQ结果
  if (details.personality_trait) {
    resultSection = `
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div>
          <div style="font-size: 32px; font-weight: bold; margin-bottom: 10px;">${details.personality_trait}</div>
          <div style="opacity: 0.9;">EPQ人格特质测评</div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #4facfe; padding-left: 12px;">维度分析</h3>
        ${Object.entries(details.dimensions || {}).map(([key, dim]: [string, any]) => {
          const tScorePercent = Math.min(100, Math.max(0, ((dim.t_score - 20) / 60) * 100));
          return `
            <div style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 12px; border-left: 4px solid #4facfe;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 600; color: #333; font-size: 18px;">${dim.label || key}</div>
                <div style="background: ${dim.level === '高' ? '#4facfe' : dim.level === '中' ? '#ffa726' : '#e0e0e0'}; color: white; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                  ${dim.level}
                </div>
              </div>
              <div style="color: #666; font-size: 14px; margin-bottom: 10px;">
                原始分: <strong>${dim.value}</strong> | T分: <strong>${dim.t_score}</strong> | 水平: <strong>${dim.level}</strong>
              </div>
              <div style="background: #e0e0e0; height: 10px; border-radius: 5px; overflow: hidden; position: relative;">
                <div style="background: linear-gradient(90deg, #4facfe, #00f2fe); height: 100%; width: ${tScorePercent}%; transition: width 0.3s;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 11px; color: #999; margin-top: 4px;">
                <span>20 (低)</span>
                <span>50 (中)</span>
                <span>80 (高)</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }
  
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;">
      <!-- 头部 -->
      <div style="text-align: center; margin-bottom: 40px; border-bottom: 3px solid #667eea; padding-bottom: 20px;">
        <h1 style="font-size: 36px; color: #333; margin: 0 0 10px 0;">测评报告</h1>
        <p style="color: #888; margin: 0;">Assessment Report</p>
      </div>
      
      <!-- 候选人信息 -->
      <div style="background: #f8f9fa; padding: 25px; border-radius: 12px; margin-bottom: 30px;">
        <h2 style="font-size: 22px; color: #333; margin: 0 0 20px 0;">候选人信息</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
          <div><span style="color: #888;">姓名：</span><strong>${submission.candidate_name}</strong></div>
          <div><span style="color: #888;">联系方式：</span><strong>${submission.candidate_phone}</strong></div>
          <div><span style="color: #888;">测评编号：</span><strong>${submission.code}</strong></div>
          <div><span style="color: #888;">问卷类型：</span><strong>${submission.questionnaire_type}</strong></div>
        </div>
      </div>
      
      <!-- 测评信息 -->
      <div style="margin-bottom: 30px;">
        <h2 style="font-size: 22px; color: #333; margin-bottom: 15px;">测评信息</h2>
        <div style="color: #666; line-height: 1.8;">
          <div>问卷名称：<strong>${submission.questionnaire_name || 'N/A'}</strong></div>
          <div>开始时间：${new Date(submission.started_at).toLocaleString('zh-CN')}</div>
          <div>提交时间：${submission.submitted_at ? new Date(submission.submitted_at).toLocaleString('zh-CN') : 'N/A'}</div>
        </div>
      </div>
      
      <!-- 测评结果 -->
      <div>
        <h2 style="font-size: 22px; color: #333; margin-bottom: 20px;">测评结果</h2>
        ${resultSection}
        
        <!-- 总分和等级 -->
        <div style="display: flex; gap: 20px; margin-top: 30px;">
          <div style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">总分</div>
            <div style="font-size: 36px; font-weight: bold;">${submission.total_score || 'N/A'}</div>
          </div>
          <div style="flex: 1; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">等级</div>
            <div style="font-size: 36px; font-weight: bold;">${submission.grade || 'N/A'}</div>
          </div>
        </div>
      </div>
      
      <!-- 页脚 -->
      <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #999; font-size: 12px;">
        <p style="margin: 5px 0;">本报告由TalentLens系统生成</p>
        <p style="margin: 5px 0;">生成时间：${new Date().toLocaleString('zh-CN')}</p>
      </div>
    </div>
  `;
};

/**
 * 生成调查问卷报告HTML
 */
export const generateSurveyReportHTML = (submission: any): string => {
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;">
      <!-- 头部 -->
      <div style="text-align: center; margin-bottom: 40px; border-bottom: 3px solid #4facfe; padding-bottom: 20px;">
        <h1 style="font-size: 36px; color: #333; margin: 0 0 10px 0;">调查问卷报告</h1>
        <p style="color: #888; margin: 0;">Survey Report</p>
      </div>
      
      <!-- 候选人信息 -->
      <div style="background: #f8f9fa; padding: 25px; border-radius: 12px; margin-bottom: 30px;">
        <h2 style="font-size: 22px; color: #333; margin: 0 0 20px 0;">提交信息</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
          <div><span style="color: #888;">姓名：</span><strong>${submission.candidate_name}</strong></div>
          <div><span style="color: #888;">联系方式：</span><strong>${submission.candidate_phone}</strong></div>
          <div><span style="color: #888;">提交编号：</span><strong>${submission.code}</strong></div>
          <div><span style="color: #888;">问卷名称：</span><strong>${submission.questionnaire_name || 'N/A'}</strong></div>
        </div>
      </div>
      
      <!-- 提交详情 -->
      <div style="margin-bottom: 30px;">
        <h2 style="font-size: 22px; color: #333; margin-bottom: 15px;">提交详情</h2>
        <div style="color: #666; line-height: 1.8;">
          <div>开始时间：${new Date(submission.started_at).toLocaleString('zh-CN')}</div>
          <div>提交时间：${submission.submitted_at ? new Date(submission.submitted_at).toLocaleString('zh-CN') : 'N/A'}</div>
          <div>状态：<span style="color: #52c41a; font-weight: bold;">已完成</span></div>
        </div>
      </div>
      
      <!-- 答题详情 -->
      ${submission.result_details?.answers && submission.result_details.answers.length > 0 ? `
        <div style="margin-top: 30px; margin-bottom: 30px;">
          <h2 style="font-size: 22px; color: #333; margin-bottom: 20px;">答题详情 (共${submission.result_details.answers.length}题)</h2>
          ${submission.result_details.answers.map((answer: any, index: number) => `
            <div style="background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin-bottom: 15px;">
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #f3f4f6;">
                <span style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 14px;">[${index + 1}]</span>
                <strong style="font-size: 16px; color: #111827; flex: 1;">${answer.question_title}</strong>
              </div>
              <div style="margin-left: 50px;">
                ${renderAnswerForPDF(answer)}
                ${answer.scoring ? `
                  <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #f3f4f6; text-align: right;">
                    <span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-radius: 20px; color: #065f46; font-size: 14px;">
                      <strong>得分: ${answer.scoring.earned_score} / ${answer.scoring.max_score}</strong>
                      <span style="color: #10b981;">(${answer.scoring.percentage}%)</span>
                    </span>
                  </div>
                ` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}
      
      <!-- 评分信息（如果有） -->
      ${submission.total_score !== null && submission.total_score !== undefined ? `
        <div style="margin-top: 30px;">
          <h2 style="font-size: 22px; color: #333; margin-bottom: 20px;">评分结果</h2>
          <div style="display: flex; gap: 20px;">
            <div style="flex: 1; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
              <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">总分</div>
              <div style="font-size: 36px; font-weight: bold;">${submission.total_score}</div>
            </div>
            ${submission.grade ? `
              <div style="flex: 1; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">等级</div>
                <div style="font-size: 36px; font-weight: bold;">${submission.grade}</div>
              </div>
            ` : ''}
          </div>
        </div>
      ` : `
        <div style="background: #e8f4fd; padding: 25px; border-radius: 12px; border-left: 4px solid #4facfe;">
          <p style="margin: 0; color: #666;">✓ 感谢您完成本次调查问卷，您的反馈对我们非常重要！</p>
        </div>
      `}
      
      <!-- 页脚 -->
      <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #999; font-size: 12px;">
        <p style="margin: 5px 0;">本报告由TalentLens系统生成</p>
        <p style="margin: 5px 0;">生成时间：${new Date().toLocaleString('zh-CN')}</p>
      </div>
    </div>
  `;
};

