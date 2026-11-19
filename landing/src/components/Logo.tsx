import { useId } from "react";
import "./Logo.css";

type Variant = "horizontal" | "stacked" | "symbol";
type Tone = "light" | "dark" | "mono";

interface LogoProps {
  variant?: Variant;
  tone?: Tone;
  /** Versión sin volcán para tamaños pequeños (favicon, encabezado compacto). */
  compact?: boolean;
  className?: string;
}

/*
 * Geometría del símbolo (cuadrícula de 96). Es la misma de src/assets/brand/symbol.svg;
 * si cambia una, cambia la otra.
 */
const MONOGRAM =
  "M9 51.4H34.6A7.6 7.6 0 0 0 34.6 36.2H25.4A7.6 7.6 0 0 1 25.4 21H61.4A7.6 7.6 0 0 1 61.4 36.2H50L56.4 47.2Q60.4 53.4 65 53.4";
const VOLCANO = "M68 56.3Q73 55.6 75.4 49.6L77.4 46.6H81.6L83.6 49.6Q86.8 55.4 94 56.3Z";
const ROAD = [
  "M77 57L18.5 84.8L31.5 91.6Z",
  "M77 57L39.6 94.4L47.4 95Z",
  "M77 57L56.4 94.6L66.6 90.6Z",
];

const TONE_COLOR: Record<Tone, string> = {
  light: "var(--paper)",
  dark: "var(--ink)",
  mono: "currentColor",
};

function Symbol({ tone, compact }: { tone: Tone; compact: boolean }) {
  const maskId = `sr-cut-${useId().replace(/:/g, "")}`;
  return (
    <svg className="logo__symbol" viewBox="0 0 96 96" aria-hidden="true" focusable="false">
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="96" height="96">
          <circle cx="48" cy="48" r="46" fill="#fff" />
          <path d={MONOGRAM} fill="none" stroke="#000" strokeWidth="5.8" strokeLinejoin="round" />
          <path d="M1 56.3H95" stroke="#000" strokeWidth="1.5" />
          {compact ? null : <path d={VOLCANO} fill="#000" />}
          {ROAD.map((d) => (
            <path key={d} d={d} fill="#000" />
          ))}
        </mask>
      </defs>
      <circle cx="48" cy="48" r="46" fill={TONE_COLOR[tone]} mask={`url(#${maskId})`} />
    </svg>
  );
}

/** Marca de Street Repo: símbolo solo o símbolo + nombre (horizontal o apilado). */
export function Logo({
  variant = "horizontal",
  tone = "light",
  compact = false,
  className,
}: LogoProps) {
  const classes = ["logo", `logo--${variant}`, `logo--${tone}`, className]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={classes} role="img" aria-label="Street Repo">
      <Symbol tone={tone} compact={compact || variant === "horizontal"} />
      {variant === "symbol" ? null : (
        <span className="logo__wordmark" aria-hidden="true">
          Street Repo
        </span>
      )}
    </span>
  );
}
