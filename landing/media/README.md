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
