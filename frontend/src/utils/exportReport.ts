/**
 * 导出报告工具函数
 * 支持PDF和图片格式导出
 */
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import type { Submission } from '../api/assessments'

// MBTI 维度标签
const getDimensionLabel = (key: string): string => {
  const labels: Record<string, string> = {
    'E-I': '外向-内向',
    'S-N': '感觉-直觉',
    'T-F': '思考-情感',
    'J-P': '判断-知觉'
  }
  return labels[key] || key
}

// DISC 类型标签
const getDISCLabel = (key: string): string => {
  const labels: Record<string, string> = {
    'D': '支配型',
    'I': '影响型',
    'S': '稳健型',
    'C': '谨慎型'
  }
  return labels[key] || key
}

// 格式化日期
const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 生成测评报告HTML模板
const generateAssessmentReportHTML = (submission: Submission): string => {
  const details = submission.result_details || {}
  const candidateName = submission.candidate_name || '未知'
  const candidatePhone = submission.candidate_phone || '-'
  const questionnaireName = submission.questionnaire_name || '测评问卷'
  const questionnaireType = submission.questionnaire_type || 'CUSTOM'
  
  let resultSection = ''
  
  // MBTI结果
  if (details.mbti_type) {
    const dimensions = details.mbti_dimensions || {}
    resultSection = `
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="font-size: 48px; font-weight: bold;">${details.mbti_type}</div>
          <div>
            <div style="font-size: 24px; font-weight: bold;">${details.mbti_description || 'MBTI人格类型'}</div>
            <div style="opacity: 0.9; margin-top: 5px;">MBTI人格类型测评</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #667eea; padding-left: 12px;">维度分析</h3>
        ${Object.entries(dimensions).map(([key, dim]: [string, any]) => {
          const dimValue = typeof dim === 'object' ? dim.value : dim
          return `
          <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-weight: 500; color: #555;">${key} - ${getDimensionLabel(key)}</span>
              <span style="font-weight: bold; color: #667eea;">${dimValue}%</span>
            </div>
            <div style="background: #f0f0f0; height: 12px; border-radius: 6px; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #667eea, #764ba2); height: 100%; width: ${dimValue}%;"></div>
            </div>
          </div>
        `}).join('')}
      </div>
    `
  }
  
  // DISC结果
  if (details.disc_type) {
    const dimensions = details.disc_dimensions || {}
    resultSection = `
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="font-size: 48px; font-weight: bold;">${details.disc_type}</div>
          <div>
            <div style="font-size: 24px; font-weight: bold;">${details.disc_description || 'DISC行为风格'}</div>
            <div style="opacity: 0.9; margin-top: 5px;">DISC行为风格测评</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #f5576c; padding-left: 12px;">维度分析</h3>
        ${Object.entries(dimensions).map(([key, dim]: [string, any]) => {
          const dimValue = typeof dim === 'object' ? dim.value : dim
          return `
          <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-weight: 500; color: #555;">${key}型 - ${getDISCLabel(key)}</span>
              <span style="font-weight: bold; color: #f5576c;">${dimValue}%</span>
            </div>
            <div style="background: #f0f0f0; height: 12px; border-radius: 6px; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #f093fb, #f5576c); height: 100%; width: ${dimValue}%;"></div>
            </div>
          </div>
        `}).join('')}
      </div>
    `
  }
  
  // EPQ结果
  if (details.epq_personality_trait || details.personality_trait || details.epq_dimensions || details.dimensions) {
    const dimensions = details.epq_dimensions || details.dimensions || {}
    const personalityTrait = details.epq_personality_trait || details.personality_trait || '人格特征'
    resultSection = `
      <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="font-size: 36px;">🧠</div>
          <div>
            <div style="font-size: 24px; font-weight: bold;">${personalityTrait}</div>
            <div style="opacity: 0.9; margin-top: 5px;">EPQ人格测评</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 30px;">
        <h3 style="color: #333; font-size: 20px; margin-bottom: 20px; border-left: 4px solid #11998e; padding-left: 12px;">维度分析</h3>
        ${Object.entries(dimensions).map(([key, dim]: [string, any]) => {
          const dimLabel = dim.label || key
          const dimLevel = dim.level || '中'
          const rawScore = dim.value ?? dim.raw_score ?? 0
          const tScore = dim.t_score ?? 50
          return `
          <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="background: linear-gradient(135deg, #11998e, #38ef7d); color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;">${key}</span>
                <span style="font-weight: 500; color: #333;">${dimLabel}</span>
              </div>
              <span style="padding: 4px 12px; border-radius: 4px; font-size: 13px; font-weight: 500; background: ${dimLevel === '高' ? '#fee2e2' : dimLevel === '低' ? '#d1fae5' : '#fef3c7'}; color: ${dimLevel === '高' ? '#dc2626' : dimLevel === '低' ? '#059669' : '#d97706'};">${dimLevel}</span>
            </div>
            <div style="display: flex; gap: 20px; font-size: 14px; color: #666;">
              <span>原始分: ${rawScore}</span>
              <span style="color: #11998e; font-weight: 600;">T分: ${tScore}</span>
            </div>
            <div style="background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px;">
              <div style="background: linear-gradient(90deg, #11998e, #38ef7d); height: 100%; width: ${Math.min(tScore, 100)}%;"></div>
            </div>
          </div>
        `}).join('')}
      </div>
    `
  }
  
  // 普通问卷结果
  if (!resultSection && submission.total_score !== null && submission.total_score !== undefined) {
    resultSection = `
      <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 30px; text-align: center;">
        <div style="font-size: 48px; font-weight: bold;">${submission.total_score}</div>
        <div style="font-size: 16px; opacity: 0.9; margin-top: 5px;">总分</div>
        ${submission.grade ? `<div style="margin-top: 15px; display: inline-block; padding: 8px 20px; background: rgba(255,255,255,0.2); border-radius: 8px; font-size: 24px; font-weight: bold;">等级: ${submission.grade}</div>` : ''}
      </div>
    `
  }
  
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; color: #333;">
      <!-- 报告头部 -->
      <div style="text-align: center; margin-bottom: 40px; padding-bottom: 30px; border-bottom: 2px solid #e2e8f0;">
        <h1 style="font-size: 32px; color: #1e293b; margin: 0 0 10px;">测评报告</h1>
        <p style="color: #64748b; font-size: 14px; margin: 0;">${questionnaireName}</p>
      </div>
      
      <!-- 候选人信息 -->
      <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 24px; border-radius: 12px; margin-bottom: 30px;">
        <h3 style="color: #475569; font-size: 16px; margin: 0 0 16px; display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; width: 4px; height: 20px; background: #6366f1; border-radius: 2px;"></span>
          候选人信息
        </h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
          <div>
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">姓名</div>
            <div style="font-weight: 600; color: #1e293b;">${candidateName}</div>
          </div>
          <div>
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">联系方式</div>
            <div style="font-weight: 600; color: #1e293b;">${candidatePhone}</div>
          </div>
          <div>
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">问卷类型</div>
            <div style="font-weight: 600; color: #1e293b;">${questionnaireType}</div>
          </div>
          <div>
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">提交时间</div>
            <div style="font-weight: 600; color: #1e293b;">${formatDate(submission.submitted_at)}</div>
          </div>
        </div>
      </div>
      
      <!-- 测评结果 -->
      <div style="margin-bottom: 30px;">
        <h3 style="color: #475569; font-size: 16px; margin: 0 0 16px; display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; width: 4px; height: 20px; background: #6366f1; border-radius: 2px;"></span>
          测评结果
        </h3>
        ${resultSection || '<p style="color: #94a3b8;">暂无测评结果</p>'}
      </div>
      
      <!-- 页脚 -->
      <div style="text-align: center; padding-top: 30px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px;">
        <p>报告生成时间：${new Date().toLocaleString('zh-CN')}</p>
        <p>TalentLens 人才初步画像智能工具</p>
      </div>
    </div>
  `
}

/**
 * 导出报告
 * @param submission 提交记录
 * @param format 导出格式 'pdf' | 'image'
 * @returns Promise<void>
 */
export const exportReport = async (
  submission: Submission,
  format: 'pdf' | 'image' = 'pdf'
): Promise<{ success: boolean; message: string }> => {
  try {
    // 创建临时的HTML报告容器
    const reportContainer = document.createElement('div')
    reportContainer.style.cssText = `
      position: fixed;
      left: -9999px;
      top: 0;
      width: 800px;
      background: #ffffff;
      padding: 60px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    `
    
    // 生成报告HTML
    reportContainer.innerHTML = generateAssessmentReportHTML(submission)
    
    document.body.appendChild(reportContainer)
    
    // 使用html2canvas渲染
    const canvas = await html2canvas(reportContainer, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false
    })
    
    // 移除临时容器
    document.body.removeChild(reportContainer)
    
    const fileName = `测评报告_${submission.candidate_name || '未知'}_${submission.code}_${new Date().toISOString().slice(0, 10)}`
    
    if (format === 'image') {
      // 导出为图片
      return new Promise((resolve) => {
        canvas.toBlob((blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = `${fileName}.png`
            link.click()
            URL.revokeObjectURL(url)
            resolve({ success: true, message: '图片报告导出成功！' })
          } else {
            resolve({ success: false, message: '图片生成失败' })
          }
        })
      })
    } else {
      // 导出为PDF
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      })
      
      const imgWidth = 210 // A4宽度
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      
      // 如果内容超过一页，需要分页处理
      const pageHeight = 297 // A4高度
      let heightLeft = imgHeight
      let position = 0
      
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight
      
      while (heightLeft > 0) {
        position = heightLeft - imgHeight
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight
      }
      
      pdf.save(`${fileName}.pdf`)
      
      return { success: true, message: 'PDF报告导出成功！' }
    }
  } catch (error) {
    console.error('导出报告失败:', error)
    return { success: false, message: '导出报告失败，请重试' }
  }
}

export default exportReport

