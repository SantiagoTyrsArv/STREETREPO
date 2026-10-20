# 0005 · Límite de intentos y bloqueo progresivo

- **Fecha:** 2026-10-16
- **Estado:** Aceptada con condiciones del responsable (decisión menor, guía 7.1 y 7.3)
- **Refs:** HU-10

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Bloqueo por cuenta | Tras 5 fallos seguidos con el mismo correo, cada fallo bloquea el inicio de sesión 1, 2, 4, 8 y hasta 15 min; los fallos se olvidan tras 1 h sin fallar y un inicio de sesión correcto los borra. Durante el bloqueo se responde **429** `TOO_MANY_LOGIN_ATTEMPTS` con `Retry-After`, sin verificar la contraseña | Frena la fuerza bruta sobre una cuenta (OWASP ASVS V2.2.1); el tope de 15 min limita el daño si alguien bloquea a propósito la cuenta de otro |
| Anti enumeración | El bloqueo se aplica a cualquier correo, exista o no la cuenta; las cuentas inactivas cuentan como fallo | Si solo se bloquearan las cuentas reales, el bloqueo revelaría qué correos están registrados |
| Minimización | La clave del contador es el SHA-256 del correo normalizado, no el correo | Guía 7.2: no guardar datos personales donde no hace falta |
| Límite por IP | Ventana deslizante: inicio de sesión **30 por 5 min**, registro **30 por hora** (configurable con `REGISTER_PER_IP_PER_HOUR`; era 10, decisión 58); al superarlo se responde **429** `RATE_LIMITED` con `Retry-After` y `details.retry_after_s` | Anti abuso y anti spam (guía 7.3). Holgado a propósito porque en la universidad o en redes móviles muchos ciudadanos comparten IP (NAT) |
| Almacenamiento | **En memoria del proceso**, detrás de los puertos `RateLimiter` y `LoginAttemptStore`; cada aplicación crea los suyos en `app.state`. Máximo 10 000 claves por almacén; al llenarse se descarta la menos reciente | La API corre en un solo proceso uvicorn; no exige tablas nuevas ni Redis, que no está en el stack (cambiarlo requiere el protocolo 0.3) |
| Valores | Constantes con nombre: `DEFAULT_LOCKOUT_POLICY` (`auth/domain/lockout.py`) y `LOGIN_LIMIT_PER_IP` / `REGISTER_LIMIT_PER_IP` (`core/rate_limiting.py`) | Guía 8.1: sin números mágicos |

## Condiciones del responsable (2026-10-16)

| # | Condición | Cómo se cumple |
|---|---|---|
| 1 | Un solo proceso | El contenedor arranca uvicorn con `--workers 1` (`infra/docker/api.Dockerfile`). Verificarlo de nuevo al montar el despliegue HTTPS (HU-17) |
| 2 | `FORWARDED_ALLOW_IPS` con la dirección del proxy, nunca `*` | Variable en `Settings`, `docker-compose.yml` y `.env.example`, con `127.0.0.1` por defecto. La API **no arranca** si incluye `*`; hay prueba en `tests/unit/test_config.py`. Uvicorn lee la misma variable |
| 3 | Purga o tope de entradas, con prueba | Cada almacén guarda como máximo 10 000 claves y descarta la menos reciente; hay pruebas en `test_rate_limit.py` y `test_login_lockout.py` |
| 4 | Mantener el bloqueo por correo con respuesta idéntica exista o no la cuenta | Así está implementado; el riesgo de bloqueo intencional se acepta (ver abajo) |
| 5 | Mencionarlo en la tesis como limitación conocida | Pendiente en el documento: contadores en memoria, un solo proceso y reinicio del conteo al reiniciar la API |

## Limitaciones conocidas

- **Un solo proceso.** Con varios *workers* o réplicas cada uno lleva su propia cuenta, lo que multiplica el límite real, y las cuentas se pierden al reiniciar la API. Si se escala, sustituir las implementaciones en memoria por unas en PostgreSQL o Redis, sin tocar los casos de uso.
- **IP real detrás de un proxy.** Uvicorn arranca con `--proxy-headers` y por defecto solo confía en `127.0.0.1`. Cuando se ponga el proxy HTTPS (HU-17, fase 6), hay que poner su dirección en `FORWARDED_ALLOW_IPS`. Si no se hace, todos los clientes compartirían el cupo de la IP del proxy.
- **Bloqueo intencional.** Alguien que conozca un correo puede mantener esa cuenta bloqueada hasta 15 min seguidos. Es el compromiso habitual del bloqueo por cuenta. El límite por IP lo encarece.
- **Concurrencia.** Varios intentos simultáneos con el mismo correo pueden pasar la verificación antes de que se registre el fallo. El límite por IP acota ese margen.
- **Pendiente:** el límite en la creación de reportes llega con la fase 5. Reutilizará `limit_per_client_ip` o un límite por usuario.
