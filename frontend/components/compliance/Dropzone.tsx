import { useRef } from "react";
import { FileCheck2, FileUp, Loader2, ScanText, TriangleAlert } from "lucide-react";

import { StatusBadge } from "@/components/thesis/StatusBadge";
import { Progress } from "@/components/ui/progress";
import { formatConfidence } from "@/lib/format";
import type { IngestResponse } from "@/lib/types";

interface DropzoneProps {
  onLoad: (file?: File) => void;
  loading: boolean;
  result: IngestResponse | null;
}

export function Dropzone({ onLoad, loading, result }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  if (result) {
    return <IngestResult result={result} />;
  }

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    onLoad(files[0]);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.pdf,.docx,.docm"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        disabled={loading}
        className="flex w-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-n300 bg-card px-6 py-10 text-center transition-colors hover:border-acento/50 hover:bg-acento-soft/30 disabled:cursor-wait"
      >
        <span className="flex size-12 items-center justify-center rounded-full bg-acento-soft text-acento">
          {loading ? (
            <Loader2 className="size-5 animate-spin" />
          ) : (
            <FileUp className="size-5" />
          )}
        </span>
        <span className="text-sm font-medium text-toga">
          {loading ? "Leyendo el documento…" : "Cargar un contrato o RIT"}
        </span>
        <span className="max-w-xs text-xs text-muted-foreground">
          Arrastra el archivo o haz clic para seleccionarlo (PDF / TXT / DOCX).
          Sin archivo, se usa el contrato de ejemplo.
        </span>
      </button>
    </>
  );
}

const STATUS_COPY = {
  digital: {
    icon: FileCheck2,
    tone: "text-ok",
    title: "Documento legible (digital)",
    badge: <StatusBadge kind="calculado" label="digital" />,
  },
  ocr: {
    icon: ScanText,
    tone: "text-info",
    title: "Leído por OCR",
    badge: <StatusBadge kind="info" label="OCR" />,
  },
  needs_human: {
    icon: TriangleAlert,
    tone: "text-warn",
    title: "Requiere revisión humana",
    badge: <StatusBadge kind="needs_human" />,
  },
} as const;

function IngestResult({ result }: { result: IngestResponse }) {
  const meta = STATUS_COPY[result.status];
  const Icon = meta.icon;
  return (
    <div className="rounded-2xl border border-n300/60 bg-card p-5 shadow-hairline">
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 ${meta.tone}`}>
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-toga">{meta.title}</p>
            {meta.badge}
          </div>
          <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
            {result.doc_id}
          </p>
          <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
            {result.text}
          </p>
          {result.status === "ocr" && (
            <div className="mt-3 max-w-xs">
              <div className="mb-1 flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                <span>confianza de lectura</span>
                <span>{formatConfidence(result.confidence)}</span>
              </div>
              <Progress value={Math.round(result.confidence * 100)} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
