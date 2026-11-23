import { lazy, Suspense, useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { COPY } from "../content/copy";
import { useMagnetic } from "../interaction/useMagnetic";
import { formatSize, type Release } from "../config/release";
import { ProximityText } from "../text/ProximityText";
import { KICKER_AXES, DOWNLOAD_CTA_AXES, LEAD_AXES } from "../text/proximity";
import "./DownloadSection.css";

// La librería del QR solo hace falta cuando hay un APK publicado: no viaja en la carga inicial.
const QrCode = lazy(() => import("./QrCode").then((module) => ({ default: module.QrCode })));

interface DownloadSectionProps {
  release: Release | null;
}

export function DownloadSection({ release }: DownloadSectionProps) {
  const copy = COPY.descarga;
  const ctaRef = useRef<HTMLAnchorElement>(null);
  const still = useReducedMotion();
  useMagnetic(ctaRef, Boolean(release) && !still);
  return (
    <section
      id="descarga"
      tabIndex={-1}
      className="download"
      aria-labelledby="descarga-titulo"
      data-accent="repair"
      data-ambient="visible"
    >
      <div className="download__intro">
        <ProximityText
          as="p"
          className="download__kicker"
          text={copy.kicker}
          by="char"
          axes={KICKER_AXES}
        />
        <h2 id="descarga-titulo" className="download__title">
          {copy.title}
        </h2>
        <ProximityText
          as="p"
          className="download__lead"
          text={copy.lead}
          by="word"
          axes={LEAD_AXES}
        />
      </div>

      {release ? (
        <div className="download__panel">
          <div className="download__main">
            <a ref={ctaRef} className="download__cta" href={release.apkUrl} download>
              <ProximityText text={copy.cta} by="char" axes={DOWNLOAD_CTA_AXES} />
            </a>
            <p className="download__meta">
              Versión {release.version} · {formatSize(release.sizeBytes)} · Android{" "}
              {release.minAndroid} o superior
            </p>
            <ol className="download__steps" aria-label={copy.stepsLabel}>
              {copy.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="download__checksum">
              {copy.checksumLabel}: <code>{release.sha256}</code>
            </p>
          </div>
          <figure className="download__qr">
            <Suspense fallback={<div className="download__qr-code" aria-hidden="true" />}>
              <QrCode value={release.apkUrl} label={copy.qrAlt} className="download__qr-code" />
            </Suspense>
            <figcaption>{copy.qrHint}</figcaption>
          </figure>
        </div>
      ) : (
        <div className="download__panel download__panel--soon">
          <p className="download__soon">{copy.soon}</p>
          <p className="download__soon-note">{copy.soonNote}</p>
        </div>
      )}
    </section>
  );
}
