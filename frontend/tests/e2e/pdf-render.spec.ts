import { test, expect, mockAnalysis } from "./fixtures";

function samplePdf() {
  const stream = "BT /F1 24 Tf 40 240 Td (Portable PDF fixture) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf);
}

for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
  test(`bundled PDF worker renders without private files at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.route("**/documents/portable-pdf", (route) => route.fulfill({ json: {
      id: "portable-pdf", title: "Portable PDF", source_type: "pdf", content: "Portable PDF fixture",
      has_original_file: true, original_mime_type: "application/pdf", created_at: new Date(0).toISOString(),
    } }));
    await page.route("**/documents/portable-pdf/file", (route) => route.fulfill({ contentType: "application/pdf", body: samplePdf() }));
    await page.route("**/documents/portable-pdf/sections", (route) => route.fulfill({ json: [{
      index: 0, section_number: 1, total_sections: 1, text: "Portable PDF fixture", preview: "Portable PDF fixture",
      char_count: 20, analyzed: true, source_label: "PDF page 1", title: "Fixture", continuation: false,
    }] }));
    await page.route("**/documents/portable-pdf/sections/0/analysis", (route) => route.fulfill({ json: { ...mockAnalysis, document_id: "portable-pdf" } }));
    await page.goto("/analysis/portable-pdf?ready=1");
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible();
    await expect.poll(() => canvas.evaluate((element: HTMLCanvasElement) => {
      const pixels = element.getContext("2d")?.getImageData(0, 0, element.width, element.height).data;
      if (!pixels) return 0;
      let dark = 0;
      for (let i = 0; i < pixels.length; i += 4) if (pixels[i] < 128 && pixels[i + 3] > 0) dark++;
      return dark;
    })).toBeGreaterThan(100);
    await page.screenshot({ path: testInfo.outputPath("pdf.png") });
  });
}
