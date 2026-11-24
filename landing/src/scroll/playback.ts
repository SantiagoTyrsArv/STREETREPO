/** Tope de espera de los cuadros de una escena: con red lenta se reproduce igual (diseño 4.2). */
export const MAX_FRAME_WAIT_MS = 2500;
/** El capítulo se dispara cuando ocupa ~40 % de la ventana, se llegue bajando o subiendo. */
export const TRIGGER_START = "top 60%";
export const TRIGGER_END = "bottom 40%";
/** Sus cuadros empiezan a cargar cuando falta ~1,5 pantallas para llegar. */
export const NEAR_START = "top 250%";
/**
 * Capítulo guiado por el *scroll* (la portada): el progreso va de 0, con la sección arriba, a 1,
 * cuando su final llega al final de la ventana. Mientras tanto la escena queda fija (CSS `sticky`).
 */
export const SCRUB_START = "top top";
export const SCRUB_END = "bottom bottom";

interface StartState {
  triggered: boolean;
  ready: boolean;
  waitedMs: number;
}

/** La reproducción empieza al entrar, con los cuadros listos o al cumplirse el tope de espera. */
export function shouldStart({ triggered, ready, waitedMs }: StartState): boolean {
  return triggered && (ready || waitedMs >= MAX_FRAME_WAIT_MS);
}
