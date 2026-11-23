import { useEffect, useLayoutEffect } from "react";

/**
 * `useLayoutEffect` en el navegador y `useEffect` en el prerenderizado, donde ninguno de los dos
 * corre: evita el aviso de React en el servidor sin cambiar el comportamiento en el cliente.
 */
export const useIsomorphicLayoutEffect =
  typeof window === "undefined" ? useEffect : useLayoutEffect;
