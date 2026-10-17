# 0006 · Derechos del titular: actualizar y suprimir

- **Fecha:** 2026-10-16
- **Estado:** Aceptada
- **Refs:** HU-11, propuestas 10 y 26, decisión 23a

## Rutas

| Ruta | Derecho (Ley 1581) | Comportamiento |
|---|---|---|
| `GET /api/v1/me` | Conocer | Datos personales guardados y consentimiento (versión y fecha) |
| `PATCH /api/v1/me` | Actualizar y rectificar | Cambia `name` o `email`; solo cambian los campos enviados. Cambiar el correo exige `current_password` |
| `POST /api/v1/me/data-deletion-requests` | Suprimir | Exige `current_password`; atiende la solicitud de inmediato y responde **201** con la constancia (`status = atendida`) |

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Confirmar la contraseña (propuesta 26) | Suprimir la cuenta o cambiar el correo exige la contraseña actual. Si falta: **422** `PASSWORD_CONFIRMATION_REQUIRED`; si no coincide: **403** `PASSWORD_CONFIRMATION_FAILED` | OWASP ASVS V3.7: una acción irreversible o que permite tomar la cuenta exige volver a autenticarse; un token de acceso robado no basta |
| Bloqueo compartido | Los fallos de confirmación cuentan para el mismo bloqueo progresivo del inicio de sesión (decisión 25) y responden **429** `TOO_MANY_LOGIN_ATTEMPTS` | Sin esto, con un token robado se podría adivinar la contraseña por `/me` saltándose el bloqueo |
| Supresión inmediata (decisión 23a) | En **una sola transacción** se crea la constancia `atendida` (`fecha_solicitud = fecha_atencion`), se borra la descripción de los reportes del titular, se anonimiza la cuenta y se revocan todas sus sesiones. Si algo falla, no se aplica nada | Decisión del responsable (2026-10-16) |
| Anonimización (propuesta 10) | `nombre` = «Titular suprimido»; `correo` = `suprimido-<id>@anonimo.invalid` (único; `.invalid` está reservado por el RFC 2606); `password_hash` = un marcador que no es un hash Argon2, así que ninguna contraseña coincide; `activo = false` | La fila se conserva porque los reportes y la constancia la referencian (`RESTRICT`) |
| Qué se conserva | Los reportes (ubicación, severidad, estado, evaluación), las confirmaciones, el rol, la fecha de registro y la versión y fecha del consentimiento | El daño vial no es un dato personal y le sirve a la Secretaría; el consentimiento es la constancia de que hubo autorización |
| Acceso tras la supresión | El token de acceso deja de servir de inmediato (el usuario se lee de la base en cada petición) y los de refresco quedan revocados. El correo queda libre para un registro nuevo | ADR 0004 |
| Correo repetido | **409** `EMAIL_ALREADY_REGISTERED` | Igual que en el registro |

## Pendiente

- **Fotos** (propuesta 10): la propuesta pide anonimizar también las fotos con rostros o placas. Su trato se define en la fase 5, cuando exista su almacenamiento; queda un `TODO(propuesta-10)` en `RequestDataDeletion` (decisión del responsable del 2026-10-16).
- **Tesis:** describir el tratamiento de la supresión (anonimización, qué se conserva y por qué) y la confirmación con contraseña.
