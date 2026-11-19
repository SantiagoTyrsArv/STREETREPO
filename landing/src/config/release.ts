/**
 * Versión publicada del APK. Mientras sea `null`, la sección de descarga muestra «Próximamente».
 * Para publicar: subir el APK firmado, calcular su SHA-256 y llenar este objeto.
 */
export interface Release {
  version: string;
  apkUrl: string;
  sizeBytes: number;
  sha256: string;
  /** Versión mínima de Android, p. ej. "8.0". */
  minAndroid: string;
}

export const RELEASE: Release | null = null;

const BYTES_PER_MB = 1024 * 1024;

/** Tamaño en MB con un decimal y coma decimal (es-CO). */
export function formatSize(bytes: number): string {
  const mb = (bytes / BYTES_PER_MB).toFixed(1).replace(".", ",");
  return `${mb} MB`;
}
