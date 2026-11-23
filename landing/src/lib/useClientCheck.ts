import { useEffect, useState } from "react";

/**
 * Resultado de una comprobación que solo existe en el navegador (WebGL, canvas, orientación).
 * Devuelve `false` en el servidor y en el primer render del cliente, y el valor real después del
 * montaje: así el HTML prerenderizado y la hidratación coinciden.
 */
export function useClientCheck(check: () => boolean): boolean {
  const [value, setValue] = useState(false);
  useEffect(() => {
    setValue(check());
    // La comprobación se hace una vez, al montar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return value;
}
