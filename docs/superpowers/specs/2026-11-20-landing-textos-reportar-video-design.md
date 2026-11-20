# Página de presentación: textos vivos, Reportar en video y video promocional — diseño

Fecha: 2026-11-20 · Proyecto: `landing/` (decisión 99, Linear ARE-46) · Estado: propuesta para aprobar

## 1. Intención

Después del fondo vivo (decisión 108), el responsable quiere que **los textos también se sientan
vivos** y que la sección **Reportar muestre la app en uso real**, no capturas sueltas. Además
quiere un **video promocional** (que él producirá, hiperrealista, alojado en YouTube) y le pidió al
asistente proponer agregados: aceptó una **calculadora de urgencia** y una **barra de progreso por
capítulos**. Público: el jurado de la sustentación.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos (entrega 1 — textos y secciones)**
1. Portada con **título enmascarado**: la escena de Pasto se ve solo a través de «STREET REPO» y al
   hacer *scroll* la cámara atraviesa las letras; con un **indicador de *scroll*** visible al cargar.
2. **Reparado**: el título funciona como **lupa** sobre la escena (dentro de las letras la misma
   escena, más clara y nítida).
3. Resto de títulos: **revelado por líneas desde una máscara** (con leve desenfoque y giro al entrar)
   y ***warp*** con el puntero o el dedo.
4. ***Variable proximity***: antetítulos y botones por letra; textos de apoyo por palabra.
5. Fórmula «U = 0,5·S + 0,3·F + 0,2·P» con **contorno** (*stroke*) que se rellena y **descifrado
   técnico** (*scramble*) al entrar.
6. **Calculadora de urgencia** en vivo con la fórmula real.
7. **Barra de progreso por capítulos** para saltar entre secciones.
8. Fondo ambiental **verde en Descarga** (el botón sigue ámbar).
9. **Video promocional**: botón «Ver el video» en la portada y sección «Street Repo en 60 segundos»
   antes de la descarga; ambos abren el mismo reproductor. Oculto mientras no haya video.

**Objetivos (entrega 2 — Reportar)**
10. La pantalla del teléfono 3D muestra un **video real de la app** que **avanza con el *scroll***.
11. Al avanzar, del teléfono sale un **abanico de 3 teléfonos** que muestra el multirreporte.
12. El texto de Reportar entra con ***slide in words***.

**No objetivos**
- Producir el video promocional (lo hace el responsable; la página deja el espacio listo).
- Antes/después en Reparado (descartado: competiría con la lupa).
- Otra librería de animación (Motion, React Bits): se usa GSAP, que ya está.

**Anti-objetivos (fracaso aunque «funcione»)**
- Texto ilegible o inaccesible: el lector de pantalla debe leer cada título y párrafo una sola vez,
  completo; contraste ≥ 4,5:1 (≥ 3:1 solo para texto ≥ 24 px).
- Tirones en el celular o en el portátil (meta de la decisión 108: sin cuadros > 50 ms con CPU ×4).
- Datos o pantallas inventadas: la calculadora usa las reglas reales; los teléfonos muestran la app
  real con datos de demostración; el video del problema se marca «Recreación generada con IA».
- Que YouTube cargue sin que la persona lo pida (peso y cookies).

## 3. Restricciones

- Stack de la página: React 18, TypeScript estricto, GSAP 3.15 + Lenis, R3F para el teléfono.
- Colores solo desde `tokens.css`; movimiento reducido apaga todo efecto (contenido completo y quieto).
- Instrument Serif (títulos) **no es variable**: el *variable proximity* se aplica a Archivo y
  Manrope en sus versiones variables (`@fontsource-variable/archivo`, ejes `wght` y `wdth`;
  `@fontsource-variable/manrope`, eje `wght`), que sustituyen a las estáticas.
- Reglas del modelo (AGENTS.md 2.2): S baja 3 · media 6 · alta 10; F primary 10 · secondary 7 ·
  tertiary 5 · residential/unclassified/service 2 (y 2 sin vía); P = 10 si d ≤ 100 m, lineal hasta
  0 a 500 m; U con dos decimales, mitad hacia arriba; pesos por defecto 0,5 / 0,3 / 0,2.
- La guía 10.4 dice que ninguna regla de negocio vive en el cliente: la calculadora es una
  **réplica didáctica** de la página de presentación, no un cálculo del sistema; se prueba con la
  tabla de la guía 8.3 para que no se desvíe.
- Privacidad: YouTube solo por `youtube-nocookie.com` y solo al tocar reproducir. El futuro
  `vercel.json` (tarea 2) debe permitir ese dominio en `frame-src`.
- Presupuesto de medios (diseño de la página, 7.2): la entrega 2 suma como mucho 6 MB en móvil.

## 4. Enfoques considerados (cómo hacer los efectos de texto)

| Enfoque | A favor | En contra |
|---|---|---|
| **A. Plugins de GSAP (SplitText, ScrambleText) + componentes propios (elegido)** | Sin librerías nuevas; todo en el reloj de GSAP/Lenis; liviano | El *warp*, la proximidad y las máscaras son trabajo propio |
| B. Motion + componentes de React Bits | Efectos hechos | Segunda librería de animación compitiendo por el *scroll*; más peso |
| C. Todo a mano | Control total | Reimplementar el partido de líneas accesible y el descifrado sin ganancia |

## 5. Lo que decidió el responsable

- Enfoque A; dos entregas (textos y secciones, después Reportar).
- Video de la app que **avanza con el *scroll***.
- *Masked heading*: **portada** con la escena solo dentro de «STREET REPO» y zoom que atraviesa las
  letras; **Reparado** como lupa; el resto, revelado por líneas.
- Agregados: calculadora de urgencia y barra de progreso.
- Video promocional en los dos lugares (portada y sección final).
- Descarga en verde.

## 6. Diseño

### 6.1 Portada enmascarada e indicador de *scroll*
- Al cargar: pantalla oscura; la escena de Apertura (la secuencia de cuadros existente) se ve solo
  a través de «STREET REPO» en Archivo variable muy grueso y ancho, centrado. Técnica: una capa
  `--night` encima de la escena con el texto recortado (SVG con `mask` o equivalente).
- Al hacer *scroll* (primer ~30 % del recorrido de Apertura), la capa escala desde el centro de una
  letra hasta que la escena llena la pantalla; después aparecen el logotipo, el `h1` «Cada calle
  cuenta.» y el texto, como hoy. «STREET REPO» de la máscara es decorativo (`aria-hidden`); el `h1`
  sigue siendo el título accesible.
- Indicador de *scroll* abajo al centro: «Desliza» con una línea que cae en bucle (en táctil, un
  dedo que sube). Desaparece al empezar el *scroll* y no vuelve.
- Movimiento reducido: sin máscara (portada actual con el cuadro clave) e indicador estático.

### 6.2 Reparado como lupa
- El título de Reparado muestra dentro de las letras la misma escena, más clara y contrastada,
  sobre el fondo oscurecido. Debe funcionar en Chrome Android y Safari iOS; si el navegador no
  soporta la técnica, el título se ve como un título normal legible.

### 6.3 Títulos: revelado por líneas y *warp*
- `RevealText` pasa a partir por **líneas** (SplitText con máscara), cada línea sube desde abajo con
  leve desenfoque y giro, ligado al progreso del capítulo (como hoy). El contenido accesible es el
  texto entero.
- ***Warp***: cerca del puntero (o del dedo apoyado) las letras del título se desplazan e inclinan
  levemente alejándose del punto (radio ~140 px, desplazamiento máx. ~6 px), con suavizado, y
  vuelven al soltar. Solo títulos visibles; nunca altera la legibilidad en reposo.

### 6.4 *Variable proximity*
- Antetítulos (Archivo) y botones: por letra, el grosor sube hasta +300 y el ancho hasta +15 cerca
  del puntero o del dedo (radio ~140 px).
- Textos de apoyo (Manrope): por palabra, grosor 400 → 600, sin cambiar el ancho (sin saltos de
  línea).
- En reposo el texto es exactamente el de hoy.

### 6.5 Fórmula
- Al entrar: los caracteres se descifran (ScrambleText con dígitos y signos) en el contorno
  (`stroke`, relleno transparente); al terminar, el relleno sube de abajo arriba hasta quedar
  sólida. S, F y P se tiñen del azul del capítulo.

### 6.6 Calculadora de urgencia
- Sección propia después de Priorizar («Pruébalo»), translúcida al fondo azul.
- Controles accesibles (teclado y lector de pantalla), con valores reales:
  - S: baja / media / alta (3 / 6 / 10).
  - F: tipo de vía (principal 10 · secundaria 7 · terciaria 5 · residencial 2 · sin vía 2 con la
    marca «Revisar vía»).
  - P: distancia al servicio crítico más cercano, deslizador de 0 a 600 m.
- Resultado en vivo: U con dos decimales y coma, la cuenta desglosada
  (0,5·S + 0,3·F + 0,2·P) y una barra 0–10. Nota: «Con los pesos por defecto; la Secretaría puede
  ajustarlos».
- Lógica en funciones puras probadas con la tabla de la guía 8.3 (8,70 · 8,00 · 7,25 · 6,50 · 6,10 ·
  3,60) y los bordes d = 100 m y d = 500 m.

### 6.7 Barra de progreso
- Escritorio: puntos fijos a la derecha, uno por capítulo (Apertura, Problema, Reportar, Priorizar,
  Pruébalo, Panel, Reparado, Video si existe, Descarga); el activo resaltado; nombre al pasar el
  mouse o con foco; son enlaces (teclado) que llevan a cada capítulo.
- Celular: una línea fina arriba que se llena con el avance (los puntos serían blancos táctiles
  < 44 px).

### 6.8 Descarga en verde
- La sección Descarga pasa a `data-accent="repair"`; el botón de descarga sigue ámbar.

### 6.9 Video promocional
- Configuración `config/video.ts`: `VIDEO: { youtubeId, title, poster, aiGenerated } | null`
  (hoy `null`: no se muestra nada).
- Portada: botón «Ver el video» junto al texto de Apertura.
- Sección «Street Repo en 60 segundos» antes de Descarga: portada local (WebP) con botón de
  reproducir y, si `aiGenerated`, la etiqueta «Recreación generada con IA».
- Ambos abren el mismo reproductor en una ventana (`<dialog>` modal): foco atrapado, Esc cierra,
  el foco vuelve al botón, el *scroll* (Lenis) se pausa. El `iframe` de `youtube-nocookie.com` se
  crea solo al abrir y se destruye al cerrar.

### 6.10 Reportar en video y abanico (entrega 2)
- Grabación en el emulador (como la tarea 7: AVD `streetrepo_pixel7`, stack aparte con OSM y
  `seed-demo`, cuenta temporal que se suprime al terminar): el flujo real de reportar (foto y
  ubicación → severidad → enviado). Se convierte en una secuencia de cuadros de la pantalla
  (ancho ~540 px, 12–16 fps) que se pinta como textura del teléfono según el progreso.
- Abanico (último tercio del recorrido): detrás del teléfono salen dos más, girados ± ~18°, con
  pantallas reales: «Posible duplicado» (HU-15) y la ficha del mapa con «Confirmar este daño»
  (HU-16). Pie de imagen accesible que describe las tres.
- Texto de Reportar con *slide in words* (palabras que entran deslizándose de lado, en cascada).
- Movimiento reducido: las capturas fijas de hoy.

## 7. Pruebas y verificación

- Unitarias: calculadora (tabla 8.3 y bordes), proximidad y *warp* (funciones puras de distancia →
  grosor/desplazamiento), barra de progreso (capítulo activo), reproductor (abre, cierra con Esc,
  devuelve el foco, crea y destruye el `iframe`, oculto si `VIDEO` es `null`), accesibilidad de
  títulos partidos (el nombre accesible es el texto completo), movimiento reducido en cada pieza.
- Navegador: escritorio y celular emulado con CPU ×4 (sin cuadros > 50 ms), contraste medido,
  Lighthouse móvil 100 en accesibilidad y buenas prácticas.

## 8. Decisiones del asistente (para revisión)

- Fuentes variables de Archivo y Manrope en lugar de las estáticas (mismo diseño, más ejes).
- Proximidad por palabra en los párrafos (por letra serían cientos de elementos y se leería peor).
- La calculadora en una sección propia, no dentro de la escena fijada de Priorizar (los controles
  dentro de una sección fijada con *scroll* son incómodos en el celular).
- Línea de progreso en el celular en vez de puntos.
- Video de Reportar como secuencia de cuadros, no `<video>` buscado con el *scroll* (se traba en
  celulares).

## 9. Lo que queda al constructor

- La técnica exacta de la máscara de la portada y de la lupa (SVG `mask`, `mask-image`,
  `backdrop-filter`), siempre con respaldo legible.
- Los tramos de progreso, radios y curvas exactas, ajustados a ojo.
- Qué letra hace de centro del zoom de la portada.
