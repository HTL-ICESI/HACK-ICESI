"use client";

import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";

const ACCEPT = ".zip,.txt,.pdf,.docx";

/** Dropzone que acepta un ZIP (recomendado) o múltiples contratos sueltos. */
export function BatchDropzone({
  onFiles,
  busy,
}: {
  onFiles: (files: File[]) => void;
  busy?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handle(files: FileList | null) {
    if (!files || files.length === 0) return;
    onFiles(Array.from(files));
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handle(e.dataTransfer.files);
      }}
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
        dragging ? "border-acento bg-acento/5" : "border-n300 bg-card"
      }`}
    >
      <UploadCloud className="size-9 text-acento" aria-hidden />
      <p className="mt-4 font-display text-lg font-medium text-toga">
        Sube los contratos del cliente
      </p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        Arrastra un <strong>.zip</strong> con todos los contratos (recomendado) o
        selecciona varios archivos <code>.txt / .pdf / .docx</code> a la vez.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => handle(e.target.files)}
      />
      <Button
        className="mt-5"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
      >
        {busy ? "Procesando…" : "Seleccionar archivos"}
      </Button>
    </div>
  );
}
