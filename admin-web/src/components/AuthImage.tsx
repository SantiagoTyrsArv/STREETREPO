import { useEffect, useState } from "react";
import { useSession } from "../auth/SessionProvider";

type Props = {
  /** Ruta de la API, por ejemplo `/api/v1/reports/{id}/photo/thumbnail`. */
  src: string;
  alt: string;
  className?: string;
};

type Loaded = { src: string; url: string | null };

/**
 * Imagen protegida: una etiqueta `<img>` no envía el token, así que se pide con el cliente
 * de la API y se muestra desde memoria. La URL de objeto se libera al desmontar.
 */
export function AuthImage({ src, alt, className }: Props) {
  const { api } = useSession();
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    api.getBlob(src).then(
      (blob) => {
        if (cancelled) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setLoaded({ src, url: objectUrl });
      },
      () => {
        if (!cancelled) {
          setLoaded({ src, url: null });
        }
      },
    );
    return () => {
      cancelled = true;
      if (objectUrl !== null) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [api, src]);

  // Lo cargado para otra ruta no se muestra mientras llega la nueva.
  const current = loaded?.src === src ? loaded : null;
  if (current === null) {
    return <div className={className} role="status" aria-label="Cargando imagen…" />;
  }
  if (current.url === null) {
    return <div className={className}>No se pudo cargar la imagen.</div>;
  }
  return <img className={className} src={current.url} alt={alt} />;
}
