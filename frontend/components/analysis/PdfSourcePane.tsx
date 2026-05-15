"use client";

import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

export function PdfSourcePane({ document, requestedPage }: { document: DocumentRead; requestedPage?: number | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [status, setStatus] = useState("Loading PDF...");
  const [failed, setFailed] = useState(false);

  if (document.source_type !== "pdf" || !document.has_original_file) return null;
  const fileUrl = api.documentFileUrl(document.id);

  useEffect(() => {
    if (requestedPage && requestedPage > 0) {
      setPageNumber(requestedPage);
    }
  }, [requestedPage]);

  useEffect(() => {
    let cancelled = false;

    async function renderPage() {
      setFailed(false);
      setStatus("Loading PDF...");
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.mjs", import.meta.url).toString();
        const pdf = await pdfjs.getDocument(fileUrl).promise;
        if (cancelled) return;
        setPageCount(pdf.numPages);
        const safePage = Math.min(Math.max(pageNumber, 1), pdf.numPages);
        if (safePage !== pageNumber) {
          setPageNumber(safePage);
          return;
        }
        const page = await pdf.getPage(safePage);
        if (cancelled) return;
        const containerWidth = canvasRef.current?.parentElement?.clientWidth ?? 520;
        const initialViewport = page.getViewport({ scale: 1 });
        const scale = Math.min(2, Math.max(0.8, (containerWidth - 32) / initialViewport.width));
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d");
        if (!canvas || !context) return;
        renderTaskRef.current?.cancel();
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.width = "100%";
        canvas.style.height = "auto";
        const renderTask = page.render({ canvas, canvasContext: context, viewport });
        renderTaskRef.current = renderTask;
        await renderTask.promise;
        if (!cancelled) setStatus("");
      } catch (err) {
        if (!cancelled) {
          setFailed(true);
          setStatus(err instanceof Error ? err.message : "Could not render this PDF.");
        }
      }
    }

    renderPage();
    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
    };
  }, [fileUrl, pageNumber]);

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Original PDF</p>
          <h2 className="text-sm font-semibold text-ink">{document.title}</h2>
        </div>
        <a
          href={fileUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface"
        >
          <ExternalLink size={14} />
          Open
        </a>
      </div>
      <div className="flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2">
        <button
          type="button"
          onClick={() => setPageNumber((value) => Math.max(1, value - 1))}
          disabled={pageNumber <= 1 || !pageCount}
          className="inline-flex items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:opacity-40"
        >
          <ChevronLeft size={14} />
          Previous
        </button>
        <p className="text-xs font-semibold text-neutral-600">
          PDF page {pageNumber} {pageCount ? `/ ${pageCount}` : ""}
        </p>
        <button
          type="button"
          onClick={() => setPageNumber((value) => Math.min(pageCount || value, value + 1))}
          disabled={!pageCount || pageNumber >= pageCount}
          className="inline-flex items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:opacity-40"
        >
          Next
          <ChevronRight size={14} />
        </button>
      </div>
      <div className="h-[calc(100vh-220px)] min-h-[620px] overflow-auto bg-neutral-100 p-4">
        {status ? (
          <div className="mb-3 rounded-md border border-line bg-panel px-3 py-2 text-xs leading-5 text-neutral-600">
            {failed ? "PDF preview failed. Use Open to view the source file in a browser tab." : status}
          </div>
        ) : null}
        <canvas ref={canvasRef} className="mx-auto block max-w-full bg-white shadow-material" />
      </div>
    </section>
  );
}
