import { useCallback, useState } from "react";
import type { PromoVideo } from "../config/video";
import { COPY } from "../content/copy";
import { VideoDialog } from "./VideoDialog";
import "./VideoSection.css";

/** Botón «Ver el video» de la portada; no aparece si no hay video configurado. */
export function VideoButton({ video }: { video: PromoVideo | null }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  if (!video) return null;
  return (
    <>
      <button type="button" className="video-button" onClick={() => setOpen(true)}>
        <span className="video-button__icon" aria-hidden="true" />
        {COPY.video.open}
      </button>
      <VideoDialog video={video} open={open} onClose={close} />
    </>
  );
}
