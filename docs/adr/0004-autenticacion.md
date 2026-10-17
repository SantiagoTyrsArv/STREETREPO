# 0004 · Autenticación y sesiones

- **Fecha:** 2026-10-16
- **Estado:** Aceptada (decisión menor, guía 3 y 7.1)
- **Refs:** HU-10, HU-11, propuestas 8 y 9, decisión 30b

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Hash de contraseñas | Argon2id con `argon2-cffi` (perfil RFC 9106 de baja memoria: 64 MiB, t = 3, p = 4); rehash automático en el inicio de sesión si los parámetros suben | Guía 7.1; recomendación de OWASP |
| Política de contraseñas | Solo longitud: 12 a 128 caracteres, sin exigir tipos de caracteres | OWASP ASVS 4.0 V2.1.1, V2.1.2 y V2.1.9 |
| Token de acceso | JWT HS256 con `PyJWT`, 15 min; claims obligatorios `sub`, `role`, `typ`, `iss`, `iat`, `exp`; algoritmo fijado al verificar; clave de ≥ 32 caracteres (`JWT_SECRET_KEY`); en producción la API no arranca sin ella | Guía 7.1; RFC 7518 §3.2 |
| Usuario en cada petición | El usuario y su rol se leen de la base en cada petición (no del claim) | Una cuenta desactivada, anonimizada o con rol cambiado pierde el acceso de inmediato |
| Token de refresco | Opaco (32 bytes aleatorios), 7 días, de un solo uso; se guarda solo su SHA-256 en `token_refresco` | Un token aleatorio de 256 bits no necesita hash lento |
| Rotación y reutilización | Cada refresco revoca el token usado y enlaza el nuevo (`reemplazado_por`); presentar un token ya rotado revoca toda la cadena de esa sesión; la fila se bloquea (`FOR UPDATE`) para serializar refrescos simultáneos | OWASP ASVS V3.5; propuesta 9 |
| Anti enumeración | El inicio de sesión responde igual y hace el mismo trabajo (verifica un hash de relleno) si el correo no existe | OWASP ASVS V2.2 |
| Correo | Se valida con `email-validator` (rechaza dominios reservados como `.test`) y se guarda en minúsculas | `usuario.correo` es UNIQUE |
| Administradores | Solo por CLI: `python -m app.cli create-admin --name … --email …` (contraseña sin eco, nunca en argumentos) | Decisión del responsable (2026-10-16); el registro público solo crea ciudadanos |
| Versión de la política | `PRIVACY_POLICY_VERSION` (por defecto `1.0`); el registro exige aceptar exactamente la vigente. `GET /api/v1/privacy-policy` (pública) la publica con `PRIVACY_POLICY_URL`, la dirección del texto; en producción la API no arranca sin ella ni si no usa https | Decisión del responsable (2026-10-16); propuestas 8, 27 y 33 |
| Transporte de tokens | En el cuerpo JSON (app móvil). Para el panel web se evaluará cookie `HttpOnly` + `SameSite` + CSRF en la fase 6 (guía 7.3) | Pendiente de la fase 6 |

## Riesgo aceptado: el registro revela si un correo ya tiene cuenta

`POST /api/v1/auth/register` responde **409** `EMAIL_ALREADY_REGISTERED` si el correo ya existe.
Con eso, cualquiera puede averiguar si una dirección tiene cuenta en Street Repo (enumeración de
cuentas, OWASP ASVS V2.2 y WSTG-IDNT-04). El inicio de sesión no tiene esta fuga, porque responde
igual y tarda lo mismo exista o no el correo.

**Por qué se acepta (decisión 30b, 2026-10-16):**

- La alternativa habitual es responder siempre igual y avisar por correo al titular de la cuenta.
  Eso exige enviar correos, y el MVP no los envía.
- El ciudadano que ya tiene cuenta necesita saberlo para iniciar sesión en vez de registrarse. El
  mensaje lo orienta sin culparlo (guía 9.2).
- El dato que se filtra es poco sensible: tener cuenta en una app de reportes viales no revela
  datos de salud, financieros ni de ubicación.

**Qué lo acota:**

- Límite de **10 registros por hora por IP** (decisión 25, [ADR 0005](0005-limite-de-intentos.md)):
  frena la enumeración masiva desde una misma dirección.
- `PATCH /api/v1/me` también responde 409 ante un correo repetido, pero exige sesión y la contraseña
  actual, y los fallos cuentan para el bloqueo progresivo (propuesta 26,
  [ADR 0006](0006-derechos-del-titular.md)).

**Límites conocidos:** el contador es por IP y vive en la memoria del proceso. Quien reparta
peticiones entre muchas IP puede consultar más correos, y el conteo se reinicia al reiniciar la API.
El límite global de solicitudes queda para la fase 8 (decisión 30c).

**Cuándo revisarlo:** si el sistema llega a enviar correos (verificación de cuenta o recuperación de
contraseña), cambiar el registro a una respuesta uniforme con aviso por correo.
