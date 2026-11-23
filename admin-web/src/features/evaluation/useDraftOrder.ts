import { useCallback, useEffect, useState } from "react";

/** Clave del borrador en `sessionStorage`: vive solo en esta pestaña (diseño, sección 6). */
export function draftKey(roundId: string, zoneId: number): string {
  return `evaluation:${roundId}:${zoneId}`;
}

function sameReports(a: readonly string[], b: readonly string[]): boolean {
  if (a.length !== b.length) {
    return false;
  }
  const expected = new Set(b);
  return new Set(a).size === a.length && a.every((id) => expected.has(id));
}

/** El borrador guardado, solo si tiene exactamente los reportes que da el servidor. */
function readDraft(key: string, initialIds: readonly string[]): string[] | null {
  try {
    const stored: unknown = JSON.parse(sessionStorage.getItem(key) ?? "null");
    if (
      Array.isArray(stored) &&
      stored.every((id) => typeof id === "string") &&
      sameReports(stored, initialIds)
    ) {
      return stored;
    }
  } catch {
    // Un borrador ilegible se descarta y se empieza con el orden del servidor.
  }
  return null;
}

export type DraftOrder = {
  ids: string[];
  moveUp: (id: string) => void;
  moveDown: (id: string) => void;
  move: (from: number, to: number) => void;
  reset: () => void;
};

/**
 * Orden que arma el evaluador antes de enviarlo. Se guarda en `sessionStorage` para no
 * perderlo al recargar; nunca se envía solo.
 */
export function useDraftOrder(
  roundId: string,
  zoneId: number,
  initialIds: readonly string[],
): DraftOrder {
  const key = draftKey(roundId, zoneId);
  const [ids, setIds] = useState<string[]>(() => readDraft(key, initialIds) ?? [...initialIds]);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (touched) {
      sessionStorage.setItem(key, JSON.stringify(ids));
    }
  }, [key, ids, touched]);

  const move = useCallback((from: number, to: number) => {
    setIds((current) => {
      if (from === to || from < 0 || to < 0 || from >= current.length || to >= current.length) {
        return current;
      }
      const next = [...current];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved!);
      return next;
    });
    setTouched(true);
  }, []);

  const moveBy = useCallback(
    (id: string, offset: number) => {
      const from = ids.indexOf(id);
      if (from !== -1) {
        move(from, from + offset);
      }
    },
    [ids, move],
  );

  const reset = useCallback(() => {
    sessionStorage.removeItem(key);
    setTouched(false);
    setIds([...initialIds]);
  }, [key, initialIds]);

  return {
    ids,
    moveUp: (id) => moveBy(id, -1),
    moveDown: (id) => moveBy(id, 1),
    move,
    reset,
  };
}
