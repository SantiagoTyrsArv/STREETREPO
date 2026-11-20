# Medios de la página

Los originales (imágenes y videos generados) **no** están en el repositorio: viven en
`landing/media/originals/` (excluida de git) y en el historial de Higgsfield. Aquí se registra
cada pieza para poder reproducirla.

## Marca

### Archivos

| Archivo                                             | Uso                                                                              |
| --------------------------------------------------- | -------------------------------------------------------------------------------- |
| `src/assets/brand/symbol.svg`                       | Símbolo completo (con el Galeras)                                                |
| `src/assets/brand/symbol-compact.svg`               | Símbolo sin volcán, para tamaños menores a 48 px                                 |
| `src/components/Logo.tsx`                           | Componente: `variant` horizontal · apilado · símbolo; `tone` light · dark · mono |
| `public/favicon.svg`, `public/apple-touch-icon.png` | Íconos del navegador (`node scripts/build-icons.mjs`)                            |

### Uso

- **Construcción:** círculo de radio 46 en una cuadrícula de 96; el monograma «SR», el horizonte,
  el volcán y la vía se recortan en negativo (máscara), así el símbolo funciona sobre cualquier fondo.
- **Color:** papel `#F5F3EE` sobre fondos oscuros; tinta `#1B2430` sobre fondos claros; `mono`
  hereda el color del texto. No se usa el ámbar en el símbolo.
- **Área de reserva:** alrededor del símbolo, como mínimo el alto de la «S» (un tercio del diámetro).
- **Tamaño mínimo:** 24 px. Por debajo de 48 px se usa la versión compacta (sin volcán).
- **Logotipo:** símbolo + «Street Repo» en Archivo 800, interletraje −0,02 em. En el encabezado
  (horizontal) va la versión compacta; en la apertura, la apilada con el volcán.
- **No:** deformar, rotar, añadir sombras o degradados, cambiar la tipografía del nombre.

### Generaciones de Higgsfield (exploración; no son el logo final)

| Ronda | Modelo                                              | Piezas          | Trabajos                                                                                                                                                |
| ----- | --------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `gpt_image_2_6` (calidad baja)                      | 12 direcciones  | `b12e83f8`, `cc1e3c9a`, `0f9d58ee`, `e736e4f4`, `e55803fe` (5), `214e92d5`, `33b40c02`, `6f47a7ab`, `adfc09fc`, `895d2648`, `3f4af7d1` (11), `dd3fdddc` |
| 2     | `gpt_image_2_6` (calidad media), referencias 5 y 11 | 8 combinaciones | `91aac135` (elegida), `75bb1477`, `ce93c23f`, `35a92c5d`, `3a27d42e`, `df3c9ec6`, `575a9571`, `525c6ba2`                                                |

El símbolo final se redibujó a mano en SVG a partir de la ronda 2, propuesta 1 (2026-11-19).

## Escenas (capítulos de secuencia)

Generadas por el responsable en claude.ai con [`higgsfield-prompts.md`](higgsfield-prompts.md)
(2026-11-19) y convertidas con `node scripts/build-sequences.ts` (decisión 107 de la bitácora).
Los prompts completos de los cuadros clave están en ese archivo. La semilla de cada cuadro clave se
puede recuperar desde Higgsfield con su `job_id`.

### Cuadros clave aprobados (imagen, 2k, el trabajo reporta `nano_banana_2`)

| Escena    | Formato | Inicio (variante · `job_id`)                | Fin (variante · `job_id`)                   |
| --------- | ------- | ------------------------------------------- | ------------------------------------------- |
| Apertura  | 16:9    | v1 · `cb6b2af4-dda2-43c2-8772-04db08b78671` | v1 · `94525cb2-f34e-4cb7-8548-d23c8282d591` |
| Apertura  | 9:16    | v1 · `e30c55fe-6830-4aa0-b0d5-edd483dc2aa2` | v2 · `93fbc405-46b7-442f-ba89-46dc51f78714` |
| Problema  | 16:9    | v1 · `209278f8-a12b-4221-9886-dbbc6714ddd7` | v1 · `4f783d91-598e-49d2-925a-940fdd5d9728` |
| Problema  | 9:16    | v2 · `beca98d2-a334-4cea-bae4-e91806e1a2ab` | v2 · `c895bf1b-85a5-4d49-a01c-d130374450f8` |
| Priorizar | 16:9    | v3 · `3a293639-433a-4968-8176-77deebaa890e` | v3 · `94d93cb3-bd97-4c12-b2c1-16dd7407ae2c` |
| Priorizar | 9:16    | v3 · `114816e3-27f3-427f-b57b-895afb23671f` | v3 · `559e2363-d172-4397-aafa-bbb26b612eb6` |
| Reparado  | 16:9    | v1 · `98ac7449-8e5f-438d-b766-441314df58b7` | v2 · `ae167653-28d8-43c3-9d28-95f168775ce5` |
| Reparado  | 9:16    | v1 · `0e22f1b7-099e-4b3e-8d90-ca19d159b4cb` | v1 · `ee1f78af-da3a-4d3a-bb7e-7b38acd3f378` |

### Videos (`seedance_2_5`, 720p, 8 s, imagen inicial y final, sin audio)

Se generaron 3 tomas por escena y formato; la elegida está marcada. El sufijo común de los prompts es
«slow, smooth, continuous camera move, no cuts, no shake, no people, cinematic, 8 seconds».

| Escena    | Prompt (antes del sufijo)                                                                                                                                                          |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Apertura  | Slow descending crane move from the night sky down towards the city of Pasto at blue hour, revealing the Galeras volcano, clouds drifting gently.                                  |
| Problema  | Slow forward dolly along the rainy street at night that ends descending into a low close-up of the pothole filled with rippling rainwater reflecting the amber streetlight.        |
| Priorizar | Static top-down aerial view with a very slow push-in; thin electric blue light lines progressively draw along the streets and converge on glowing points.                          |
| Reparado  | Slow rising and backward camera move from the close-up of the freshly repaired asphalt at dawn up to a wide view of the dry street at sunrise with the Galeras volcano at the end. |

| Escena    | Formato | Toma | `job_id`                               | Semilla    | Elegida                     |
| --------- | ------- | ---- | -------------------------------------- | ---------- | --------------------------- |
| Apertura  | 16:9    | 1    | `1b547d09-44a3-43c4-ba0d-5760c341f85c` | 1081510440 | no (corte duro a los 6,5 s) |
| Apertura  | 16:9    | 2    | `ef52698b-e5bf-43b2-96e9-5745ba66cade` | 781385057  |                             |
| Apertura  | 16:9    | 3    | `b429d2a9-d1f3-46ee-8cf7-d62f586f917a` | 497030137  | **sí**                      |
| Apertura  | 9:16    | 1    | `83ab8262-87e7-415b-9f35-2d265266ea80` | 1901212740 | **sí**                      |
| Apertura  | 9:16    | 2    | `3af2a32a-f374-42eb-a260-0df788c19f64` | 58568136   |                             |
| Apertura  | 9:16    | 3    | `adf48328-edce-4160-aafb-436503c98a0b` | 2043110928 |                             |
| Problema  | 16:9    | 1    | `6e0d30fb-e41e-41ea-9a55-87a0fe6fd6bb` | 1677655203 | **sí**                      |
| Problema  | 16:9    | 2    | `cb928ea4-be6e-4e1f-a1ee-65dd2ebfa230` | 2061266607 |                             |
| Problema  | 16:9    | 3    | `d0db22a7-0f0b-4cca-8ccc-966fd05637d5` | 376071294  |                             |
| Problema  | 9:16    | 1    | `03c4bdee-1e70-4422-8ae6-b16e564e6054` | 946482246  |                             |
| Problema  | 9:16    | 2    | `afcb735e-5d9b-4d27-a1d5-392f06d595af` | 1582367456 |                             |
| Problema  | 9:16    | 3    | `1be60ea7-3c53-4bae-86e8-5aebbd0accdc` | 2031693057 | **sí**                      |
| Priorizar | 16:9    | 1    | `a15ec8c7-86ae-4a42-a1a1-d135f7f4bffa` | 138107081  |                             |
| Priorizar | 16:9    | 2    | `77d4b948-ced9-4382-a13b-1eb0678c2810` | 17713451   |                             |
| Priorizar | 16:9    | 3    | `703006ba-1f36-48a8-88ea-c455136442aa` | 2077758511 | **sí**                      |
| Priorizar | 9:16    | 1    | `555a86b2-ce25-4c23-a87d-6f1399ff7f62` | 1109062166 |                             |
| Priorizar | 9:16    | 2    | `6a950866-6adc-4a26-9397-1daeb24f8665` | 373141011  | **sí**                      |
| Priorizar | 9:16    | 3    | `ca32035e-4263-402d-badc-e817ec61bbeb` | 863062057  |                             |
| Reparado  | 16:9    | 1    | `aef1a1d9-9230-4d07-bc02-f23b1b371265` | 725049144  |                             |
| Reparado  | 16:9    | 2    | `3a5017c4-566c-4b2c-8b4f-2ad8796e5fb8` | 746106866  | **sí**                      |
| Reparado  | 16:9    | 3    | `39fa32a6-385a-4eb4-aa84-ee9f923ee81e` | 126479910  |                             |
| Reparado  | 9:16    | 1    | `a7ef330c-ddb6-4755-9b1f-3c1f844f8fb5` | 988756837  |                             |
| Reparado  | 9:16    | 2    | `d5012f68-101a-45e5-a1c4-983888eaf6d9` | 1133233929 | **sí**                      |
| Reparado  | 9:16    | 3    | `2c6093b9-3a3b-45bf-abd5-38e6ec465988` | 1926351267 |                             |

### Secuencias publicadas (`public/media/<capítulo>/`)

Reproducir (con los originales en `media/originals/scenes/video/`):

```sh
node scripts/build-sequences.ts apertura  media/originals/scenes/video/apertura-16x9-t3.mp4  media/originals/scenes/video/apertura-9x16-t1.mp4  --fps 16
node scripts/build-sequences.ts problema  media/originals/scenes/video/problema-16x9-t1.mp4  media/originals/scenes/video/problema-9x16-t3.mp4  --fps 16
node scripts/build-sequences.ts priorizar media/originals/scenes/video/priorizar-16x9-t3.mp4 media/originals/scenes/video/priorizar-9x16-t2.mp4 --fps 16
node scripts/build-sequences.ts reparado  media/originals/scenes/video/reparado-16x9-t2.mp4  media/originals/scenes/video/reparado-9x16-t2.mp4  --fps 16
```

- 16 fps, 129 cuadros por escena; WebP calidad 75; escritorio 1280 × 720 y móvil 720 × 1280 (el
  tamaño nativo de los videos). `key.webp` es el primer cuadro de escritorio.
- Peso: escritorio 19 MB y móvil 23 MB en total (presupuesto del diseño: ≤ 45 MB y ≤ 25 MB). A
  24 fps el móvil pesaba 33 MB.
