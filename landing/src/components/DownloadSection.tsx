import { COPY } from "../content/copy";
import { formatSize, type Release } from "../config/release";
import { QrCode } from "./QrCode";
import "./DownloadSection.css";

interface DownloadSectionProps {
  release: Release | null;
}

export function DownloadSection({ release }: DownloadSectionProps) {
  const copy = COPY.descarga;
  return (
    <section id="descarga" tabIndex={-1} className="download" aria-labelledby="descarga-titulo">
      <div className="download__intro">
        <p className="download__kicker">{copy.kicker}</p>
        <h2 id="descarga-titulo" className="download__title">
          {copy.title}
        </h2>
        <p className="download__lead">{copy.lead}</p>
      </div>

      {release ? (
        <div className="download__panel">
          <div className="download__main">
            <a className="download__cta" href={release.apkUrl} download>
              {copy.cta}
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
            <QrCode value={release.apkUrl} label={copy.qrAlt} className="download__qr-code" />
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
