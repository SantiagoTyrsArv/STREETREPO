import { useState } from "react";
import { ApiError } from "../../api/client";
import { useSession } from "../../auth/SessionProvider";

export type ExportKind = "ficha" | "resumen" | "reportes" | "avisos";

/** Las cuatro exportaciones de la ronda (ADR 0008). Ficha y resumen exigen la ronda cerrada. */
export const EXPORTS: ReadonlyArray<{ kind: ExportKind; label: string; primary?: boolean }> = [
  { kind: "ficha", label: "Exportar ficha (CSV)", primary: true },
  { kind: "resumen", label: "Resumen (CSV)" },
  { kind: "reportes", label: "Reportes para revisión (CSV)" },
  { kind: "avisos", label: "Avisos de duplicado (CSV)" },
];

const DOWNLOAD_PROBLEM = "No pudimos descargar el archivo. Inténtalo de nuevo.";

export function exportPath(roundId: string, kind: ExportKind): string {
  return `/api/v1/admin/evaluation-rounds/${roundId}/export/${kind}.csv`;
}

/** Guarda el archivo en el equipo con un enlace temporal; la URL se libera enseguida. */
function saveFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Descarga con el cliente de la API: un enlace directo no llevaría el token de acceso, que
 * vive en memoria (decisión 42). El nombre del archivo es el que da el servidor.
 */
export function useDownload(roundId: string) {
  const { api } = useSession();
  const [pending, setPending] = useState<ExportKind | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  async function download(kind: ExportKind) {
    setPending(kind);
    setProblem(null);
    try {
      const file = await api.getFile(exportPath(roundId, kind));
      saveFile(file.blob, file.filename ?? `ronda-${kind}.csv`);
    } catch (error) {
      setProblem(error instanceof ApiError ? error.message : DOWNLOAD_PROBLEM);
    } finally {
      setPending(null);
    }
  }

  return { download, pending, problem };
}
