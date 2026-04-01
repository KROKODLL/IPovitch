import { loadDataUrlAsImage } from "./reactFlowSnapshot";

type PdfReportInput = {
  dataUrl: string;
  fileName: string;
  titleLine: string;
};

export async function downloadTopologyPdfReport({
  dataUrl,
  fileName,
  titleLine,
}: PdfReportInput): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const img = await loadDataUrlAsImage(dataUrl);
  const iw = img.naturalWidth;
  const ih = img.naturalHeight;
  if (iw < 1 || ih < 1) {
    return;
  }
  const pdf = new jsPDF({ format: "a4", orientation: "landscape", unit: "pt" });
  const margin = 48;
  const headerBottom = 56;
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const maxW = pageW - margin * 2;
  const maxH = pageH - margin - headerBottom;
  const scale = Math.min(maxW / iw, maxH / ih);
  const dw = iw * scale;
  const dh = ih * scale;
  const x = margin + (maxW - dw) / 2;
  const y = headerBottom + (maxH - dh) / 2;
  pdf.setFontSize(11);
  pdf.text(titleLine, margin, 32);
  pdf.setFontSize(8);
  pdf.setTextColor(130);
  pdf.text(new Date().toISOString(), margin, 44);
  pdf.setTextColor(0);
  pdf.addImage(dataUrl, "PNG", x, y, dw, dh);
  pdf.save(fileName);
}
