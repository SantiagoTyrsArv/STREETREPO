import { useEffect, useRef } from "react";
import type { PromoVideo } from "../config/video";
import { COPY } from "../content/copy";
import { pauseSmoothScroll, resumeSmoothScroll } from "../scroll/useSmoothScroll";
import "./VideoDialog.css";

interface VideoDialogProps {
  video: PromoVideo;
  open: boolean;
  onClose: () => void;
}

/**
 * Reproductor en una ventana modal: el `iframe` de YouTube (dominio sin cookies) existe solo
 * mientras está abierta. Esc o el botón la cierran; el foco vuelve a quien la abrió y el *scroll*
 * suave se pausa mientras tanto.
 */
export function VideoDialog({ video, open, onClose }: VideoDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || !open) return;
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    pauseSmoothScroll();
    const onDialogClose = () => onClose();
    dialog.addEventListener("close", onDialogClose);
    return () => {
      dialog.removeEventListener("close", onDialogClose);
      if (dialog.open) dialog.close();
      resumeSmoothScroll();
      opener.current?.focus();
    };
  }, [open, onClose]);

  const src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(video.youtubeId)}?autoplay=1&rel=0&modestbranding=1`;
  return (
    <dialog ref={ref} className="video-dialog" aria-label={video.title}>
      <button type="button" className="video-dialog__close" onClick={() => ref.current?.close()}>
        {COPY.video.close}
      </button>
      <div className="video-dialog__frame">
        {open ? (
          <iframe
            src={src}
            title={video.title}
            allow="autoplay; encrypted-media; picture-in-picture"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : null}
      </div>
    </dialog>
  );
}
