import QRCode from "qrcode";
import { useMemo } from "react";

/** Margen en módulos alrededor del código (la norma pide 4). */
const QUIET_ZONE = 4;

/** Convierte la matriz del QR en un único trazado SVG, un cuadro de 1×1 por módulo oscuro. */
function modulesPath(text: string): { d: string; size: number } {
  const { modules } = QRCode.create(text, { errorCorrectionLevel: "M" });
  const n = modules.size;
  let d = "";
  for (let row = 0; row < n; row++) {
    for (let col = 0; col < n; col++) {
      if (modules.get(row, col)) {
        d += `M${col + QUIET_ZONE} ${row + QUIET_ZONE}h1v1h-1z`;
      }
    }
  }
  return { d, size: n + QUIET_ZONE * 2 };
}

interface QrCodeProps {
  value: string;
  label: string;
  className?: string;
}

/** QR generado en el cliente, sin servicios externos. */
export function QrCode({ value, label, className }: QrCodeProps) {
  const { d, size } = useMemo(() => modulesPath(value), [value]);
  return (
    <svg
      className={className}
      role="img"
      aria-label={label}
      viewBox={`0 0 ${size} ${size}`}
      shapeRendering="crispEdges"
    >
      <rect width={size} height={size} fill="#fff" />
      <path d={d} fill="#000" />
    </svg>
  );
}
