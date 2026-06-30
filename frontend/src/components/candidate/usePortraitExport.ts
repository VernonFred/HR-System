import { ref, type ComputedRef, type Ref } from 'vue';
import domtoimage from 'dom-to-image-more';
import jsPDF from 'jspdf';
import type { CandidateProfile } from '../../types/candidate';

export function usePortraitExport(
  profile: Ref<CandidateProfile | null>,
  displayData: ComputedRef<CandidateProfile>,
) {
  const isExporting = ref(false);
  const showExportMenu = ref(false);

  const exportAsPNG = async () => {
    if (!profile.value) return;

    isExporting.value = true;
    showExportMenu.value = false;

    try {
      // 等待DOM和动画完成
      await new Promise(resolve => setTimeout(resolve, 500));

      const element = document.querySelector('.portrait-card') as HTMLElement;
      if (!element) {
        console.error('找不到 .portrait-card 元素');
        alert('导出失败：找不到画像元素');
        return;
      }

      console.log('开始导出PNG（使用 dom-to-image-more），元素尺寸:', element.offsetWidth, 'x', element.offsetHeight);

      // 使用 dom-to-image-more 替代 html2canvas
      const dataUrl = await domtoimage.toPng(element, {
        width: element.offsetWidth,
        height: element.offsetHeight,
        style: {
          transform: 'scale(1)',
          transformOrigin: 'top left'
        },
        quality: 1.0,
        bgcolor: '#f8fafc'
      });

      console.log('图片生成成功');

      const link = document.createElement('a');
      const levelLabel = 'AI画像';
      link.download = `候选人画像-${displayData.value.name}-${levelLabel}-${Date.now()}.png`;
      link.href = dataUrl;
      link.click();

      console.log(`PNG导出成功 (${levelLabel})`);
    } catch (error) {
      console.error('导出PNG失败:', error);
      alert('导出失败，请重试。错误信息：' + (error as Error).message);
    } finally {
      isExporting.value = false;
    }
  };

  const exportAsPDF = async () => {
    if (!profile.value) return;

    isExporting.value = true;
    showExportMenu.value = false;

    try {
      // 等待DOM和动画完成
      await new Promise(resolve => setTimeout(resolve, 500));

      const element = document.querySelector('.portrait-card') as HTMLElement;
      if (!element) {
        console.error('找不到 .portrait-card 元素');
        alert('导出失败：找不到画像元素');
        return;
      }

      console.log('开始导出PDF（使用 dom-to-image-more），元素尺寸:', element.offsetWidth, 'x', element.offsetHeight);

      // 使用 dom-to-image-more 生成图片
      const imgData = await domtoimage.toPng(element, {
        width: element.offsetWidth,
        height: element.offsetHeight,
        style: {
          transform: 'scale(1)',
          transformOrigin: 'top left'
        },
        quality: 1.0,
        bgcolor: '#f8fafc'
      });

      console.log('PDF 图片生成成功');

      // 创建临时图片以获取尺寸
      const tempImg = new Image();
      tempImg.src = imgData;
      await new Promise((resolve) => {
        tempImg.onload = resolve;
      });

      const imgWidth = tempImg.width;
      const imgHeight = tempImg.height;

      // A4 尺寸：210mm x 297mm
      const pageWidth = 210;
      const pageHeight = 297;
      const margin = 5; // 页边距
      const contentWidth = pageWidth - 2 * margin;

      // 计算图片在PDF中的尺寸（基于实际图片尺寸）
      const pdfImgWidth = contentWidth;
      const pdfImgHeight = (imgHeight * pdfImgWidth) / imgWidth;

      // 创建PDF，根据内容高度决定是否需要多页
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      // 如果内容超过一页，需要分页处理
      const contentHeight = pageHeight - 2 * margin;
      if (pdfImgHeight <= contentHeight) {
        // 内容可以放在一页
        pdf.addImage(imgData, 'PNG', margin, margin, pdfImgWidth, pdfImgHeight);
      } else {
        // 需要多页 - 使用简化的分页方式
        const totalPages = Math.ceil(pdfImgHeight / contentHeight);
        console.log(`PDF需要 ${totalPages} 页，每页高度 ${contentHeight}mm，总高度 ${pdfImgHeight}mm`);

        for (let pageNum = 0; pageNum < totalPages; pageNum++) {
          if (pageNum > 0) {
            pdf.addPage();
          }

          // 计算当前页应该截取的高度
          const remainingImgHeight = pdfImgHeight - (pageNum * contentHeight);
          const heightOnPage = Math.min(contentHeight, remainingImgHeight);

          console.log(`第 ${pageNum + 1} 页: heightOnPage=${heightOnPage}`);

          // 使用图片偏移的方式添加到PDF（简化分页）
          const yOffset = -(pageNum * contentHeight);
          pdf.addImage(imgData, 'PNG', margin, margin + yOffset, pdfImgWidth, pdfImgHeight);
        }
      }

      const levelLabel = 'AI画像';
      pdf.save(`候选人画像-${displayData.value.name}-${levelLabel}-${Date.now()}.pdf`);
      console.log(`PDF导出成功 (${levelLabel})`);
    } catch (error) {
      console.error('导出PDF失败:', error);
      alert('导出失败，请重试。错误信息：' + (error as Error).message);
    } finally {
      isExporting.value = false;
    }
  };

  const exportAsWord = () => {
    if (!profile.value) return;

    showExportMenu.value = false;
    alert('Word导出功能开发中，敬请期待！\n建议使用 PDF 格式导出。');
  };


  return {
    isExporting,
    showExportMenu,
    exportAsPNG,
    exportAsPDF,
    exportAsWord,
  };
}
