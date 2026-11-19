# Paquete de generación para Higgsfield — escenas de la página

> Para usar en **Claude (claude.ai)** con el conector de Higgsfield, donde están las generaciones
> ilimitadas de prueba. Copia este archivo completo en una conversación nueva de Claude y escribe:
> «Sigue estas instrucciones paso a paso.»
> Plan: `docs/superpowers/plans/2026-11-19-landing-descarga-apk.md`, tarea 4.

---

## Instrucciones para Claude

Eres el operador de Higgsfield para la página de presentación de **Street Repo**, una app
ciudadana para reportar daños en las vías de Pasto (Nariño, Colombia). Vas a generar las
imágenes y los videos de cuatro escenas de un recorrido cinematográfico guiado por el _scroll_.

Reglas:

1. **Usa siempre las generaciones ilimitadas** (`use_unlim: true`). Si un modelo no las admite o
   la asignación se agota, **detente y avísame**; no gastes créditos sin preguntarme.
2. Trabaja **por fases y espera mi aprobación** al final de cada una (marcadas con 🛑). No pases a
   los videos sin que yo apruebe los cuadros clave.
3. Usa los modelos indicados. Si uno no está disponible, propón el más parecido con
   `models_explore` y espera mi respuesta.
4. Genera **variantes** (indicadas en cada paso) y muéstramelas juntas con
   `show_generation_by_ids`, numeradas.
5. Al final de cada fase, entrégame una **tabla** con: escena, formato, cuadro o toma, número de
   variante y **job_id**. Esa tabla la copio al repositorio.
6. Nunca incluyas texto, letreros legibles, placas de vehículos, logotipos ni personas
   reconocibles en las imágenes.

### Modelos

| Uso                             | Modelo                                   | Parámetros                                                                                                                                   |
| ------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Cuadros clave                   | `nano_banana_pro`                        | `resolution: "4k"`                                                                                                                           |
| Edición «misma calle, reparada» | `nano_banana_pro` con `image_references` | `resolution: "4k"`                                                                                                                           |
| Videos                          | `seedance_2_5`                           | `mode: "omni_reference"`, `resolution: "1080p"`, `duration: 8`, `generate_audio: false`, `bitrate_mode: "high"`, `start_image` y `end_image` |

### Biblia de estilo (prefijo de TODOS los prompts de imagen)

```
Cinematic still, photorealistic, shot on ARRI Alexa 35 with a 35mm anamorphic lens, shallow
depth of field, subtle film grain, deep night-blue shadows (#0A0E13), restrained minimal
composition with generous negative space, editorial luxury brand film aesthetic. Location:
Pasto, a high-altitude Andean city in southern Colombia: low colonial and modern buildings,
narrow streets, humid air, the Galeras volcano on the horizon. No text, no readable signs, no
license plates, no logos, no recognizable people.
```

Cada escena tiene un **único color de acento**; el resto de la imagen es frío y oscuro:

| Escena    | Acento                                                   |
| --------- | -------------------------------------------------------- |
| Apertura  | ninguno (azul noche y luces cálidas tenues de la ciudad) |
| Problema  | ámbar `#F5B800` (luz de alumbrado de sodio)              |
| Priorizar | azul señal `#4C8DFF` (líneas de datos)                   |
| Reparado  | verde `#3DD68C` muy sutil (vegetación al amanecer)       |

---

## Fase 1 — Cuadros clave (inicio y fin de cada escena) 🛑

Para cada cuadro genera **3 variantes en 16:9** y **3 en 9:16** (9:16 es la versión para celular:
recompón la escena en vertical, no la recortes). En total: 4 escenas × 2 cuadros × 2 formatos × 3
variantes = 48 imágenes. Agrega el prefijo de la biblia a cada prompt.

### 1. Apertura

- **Inicio:** `Night sky over the Andes before dawn, the dark silhouette of the Galeras volcano barely visible against a deep blue sky, thin clouds drifting, a faint line of city lights at the very bottom of the frame, vast negative space above.`
- **Fin:** `Aerial view of the city of Pasto at blue hour, the valley filled with soft warm city lights, the Galeras volcano dominant on the horizon with mist at its base, the camera closer and lower than the opening shot, calm and majestic.`

### 2. Problema (acento ámbar)

- **Inicio:** `Wide street-level shot of a narrow street in Pasto at night under light rain, wet asphalt reflecting amber sodium streetlights, low buildings on both sides, empty street, a dark pothole visible in the middle distance.`
- **Fin:** `Low close-up of a deep pothole in wet asphalt at night, rainwater filling it and rippling, the amber streetlight reflected in the water, cracked edges of the asphalt in sharp detail, background softly out of focus.`

### 3. Priorizar (acento azul señal)

- **Inicio:** `Top-down aerial view of the city of Pasto at night, dark street grid with sparse warm lights, completely calm, abstract and graphic composition.`
- **Fin:** `Same top-down aerial view of the city at night, now thin glowing electric blue (#4C8DFF) lines trace several streets and converge on a few bright pulsing points, like a data network mapping priorities over the city, elegant and minimal, no text or numbers.`

### 4. Reparado (acento verde sutil) — debe ser **la misma calle** de la escena 2

Genera estos dos cuadros **editando** los cuadros aprobados de la escena 2 (pásalos como
`image_references`), conservando el encuadre, la calle y los edificios:

- **Inicio** (a partir del **fin** de la escena 2): `Same exact framing and street as the reference, but at dawn: the pothole is now perfectly repaired with fresh smooth dark asphalt, the street is dry, soft early morning light, a hint of green from trees and plants along the street (#3DD68C, very subtle).`
- **Fin** (a partir del **inicio** de la escena 2): `Same exact framing and street as the reference, but at sunrise: the street is fully repaired and dry, golden-cool morning light, clear sky with the Galeras volcano visible at the end of the street, calm and hopeful, subtle green vegetation.`

Como la escena 4 depende de la 2: primero genera y muéstrame las escenas 1, 2 y 3; cuando apruebe
la escena 2, genera la 4.

🛑 **Muéstrame las variantes de cada escena y espera a que elija una por cuadro y formato.**

---

## Fase 2 — Videos 🛑

Para cada escena y cada formato (16:9 y 9:16), genera **3 tomas** con `seedance_2_5`, usando el
cuadro de inicio aprobado como `start_image` y el de fin como `end_image`. En total: 4 escenas × 2
formatos × 3 tomas = 24 videos.

Prompts de movimiento (en todos: `slow, smooth, continuous camera move, no cuts, no shake, no
people, cinematic, 8 seconds`):

| Escena    | Movimiento                                                                                                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Apertura  | `Slow descending crane move from the night sky down towards the city of Pasto at blue hour, revealing the Galeras volcano, clouds drifting gently.`                                  |
| Problema  | `Slow forward dolly along the rainy street at night that ends descending into a low close-up of the pothole filled with rippling rainwater reflecting the amber streetlight.`        |
| Priorizar | `Static top-down aerial view with a very slow push-in; thin electric blue light lines progressively draw along the streets and converge on glowing points.`                          |
| Reparado  | `Slow rising and backward camera move from the close-up of the freshly repaired asphalt at dawn up to a wide view of the dry street at sunrise with the Galeras volcano at the end.` |

🛑 **Muéstrame las tomas de cada escena y espera a que elija una por formato.**

---

## Fase 3 — Entrega

Entrégame una única tabla final con lo aprobado:

| Escena   | Formato | Pieza         | job_id |
| -------- | ------- | ------------- | ------ |
| apertura | 16:9    | cuadro inicio | …      |
| apertura | 16:9    | cuadro fin    | …      |
| apertura | 16:9    | video         | …      |
| …        | …       | …             | …      |

(4 escenas × 2 formatos × 3 piezas = 24 filas.)

---

## Después, en Claude Code

Pega la tabla final en Claude Code. Con los `job_id`, Claude Code descarga los originales a
`landing/media/originals/scenes/`, los convierte en secuencias de cuadros
(`scripts/build-sequences`) y registra cada pieza en `landing/media/README.md`.
