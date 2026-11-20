import { useCallback, useState } from "react";
import type { PromoVideo } from "../config/video";
import { COPY } from "../content/copy";
import { VideoDialog } from "./VideoDialog";
import "./VideoSection.css";

/** «Street Repo en 60 segundos»: portada local y el reproductor al tocar; oculta sin video. */
export function VideoSection({ video }: { video: PromoVideo | null }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  if (!video) return null;
  const copy = COPY.video;
  return (
    <section
      id="video"
      className="video-section"
      aria-labelledby="video-titulo"
      data-accent="signal"
      data-ambient="visible"
    >
      <p className="video-section__kicker">{copy.kicker}</p>
      <h2 id="video-titulo" className="video-section__title">
        {copy.title}
      </h2>
      <figure className="video-section__poster">
        <img src={video.poster} alt="" width={1600} height={900} loading="lazy" decoding="async" />
        <button
          type="button"
          className="video-section__play"
          aria-label={`${copy.play}: ${video.title}`}
          onClick={() => setOpen(true)}
        >
          <span aria-hidden="true" />
        </button>
        {video.aiGenerated ? (
          <figcaption className="video-section__ai">{copy.aiLabel}</figcaption>
        ) : null}
      </figure>
      <VideoDialog video={video} open={open} onClose={close} />
    </section>
  );
}
