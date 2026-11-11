import { useEffect, useId, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import iconPin from "../assets/icon-pin.svg";
import { formatCountdown, formatWait } from "../format/format";
import { useSession } from "./SessionProvider";
import "./login.css";

const INVALID_CREDENTIALS_MESSAGE = "Correo o contraseña incorrectos.";
const ROLE_REQUIRED_MESSAGE = "Esta cuenta no tiene acceso al panel.";
const TOO_MANY_ATTEMPTS_FALLBACK = "Espera un momento antes de intentarlo de nuevo.";
const HTTP_UNAUTHORIZED = 401;
const HTTP_TOO_MANY_REQUESTS = 429;
const MS_PER_SECOND = 1000;

type Failure =
  | { kind: "message"; text: string }
  /** Bloqueo por intentos: `until` es el instante (ms) en que se puede reintentar. */
  | { kind: "locked"; until: number | null };

/** `now` es el mismo instante con el que arranca la cuenta regresiva, para que no sobre un segundo. */
function toFailure(error: unknown, now: number): Failure {
  if (!(error instanceof ApiError)) {
    throw error;
  }
  if (error.status === HTTP_TOO_MANY_REQUESTS) {
    const seconds = error.details.retry_after_s;
    return {
      kind: "locked",
      until: typeof seconds === "number" ? now + seconds * MS_PER_SECOND : null,
    };
  }
  if (error.code === "ADMIN_ROLE_REQUIRED") {
    return { kind: "message", text: ROLE_REQUIRED_MESSAGE };
  }
  if (error.status === HTTP_UNAUTHORIZED) {
    return { kind: "message", text: INVALID_CREDENTIALS_MESSAGE };
  }
  return { kind: "message", text: error.message };
}

/** Inicio de sesión de funcionarios (Figma «Panel · Inicio de sesión» y su variante bloqueada). */
export function LoginPage() {
  const { signIn, notice } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const emailId = useId();
  const passwordId = useId();

  // Reloj de la cuenta regresiva: se pone en hora al fallar y avanza cada segundo.
  const [now, setNow] = useState(() => Date.now());
  const lockedUntil = failure?.kind === "locked" ? failure.until : null;
  useEffect(() => {
    if (lockedUntil === null) {
      return;
    }
    const timer = setInterval(() => setNow(Date.now()), MS_PER_SECOND);
    return () => clearInterval(timer);
  }, [lockedUntil]);
  const secondsLeft =
    lockedUntil === null ? 0 : Math.max(0, Math.ceil((lockedUntil - now) / MS_PER_SECOND));
  const locked = lockedUntil !== null && secondsLeft > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending || locked) {
      return;
    }
    setSending(true);
    setFailure(null);
    try {
      await signIn(email.trim(), password);
    } catch (error) {
      const failedAt = Date.now();
      setNow(failedAt);
      setFailure(toFailure(error, failedAt));
    } finally {
      setSending(false);
    }
  }

  let submitLabel = "Ingresar";
  if (sending) {
    submitLabel = "Ingresando…";
  } else if (locked) {
    submitLabel = `Reintentar en ${formatCountdown(secondsLeft)}`;
  }

  return (
    <main className="login">
      <div className="login__card">
        <div className="login__brand">
          <span className="brand-mark">
            <img src={iconPin} alt="" width={22} height={22} />
          </span>
          <div>
            <p className="login__brand-name">Street Repo</p>
            <p className="login__brand-caption">Panel administrativo</p>
          </div>
        </div>

        <h1 className="login__title">Ingreso de funcionarios</h1>
        <p className="login__intro">
          Acceso solo para cuentas de funcionario. Las cuentas las crea el administrador del
          sistema.
        </p>

        {notice && !failure ? (
          <p className="login__notice" role="status">
            {notice}
          </p>
        ) : null}

        {failure?.kind === "message" ? (
          <div className="alert" role="alert">
            <span className="alert__icon" aria-hidden="true">
              !
            </span>
            <p>{failure.text}</p>
          </div>
        ) : null}

        {failure?.kind === "locked" ? (
          <div className="alert" role="alert">
            <span className="alert__icon" aria-hidden="true">
              !
            </span>
            <div>
              <p className="alert__title">Demasiados intentos fallidos</p>
              <p>
                {locked
                  ? `Espera ${formatWait(secondsLeft)} antes de intentarlo de nuevo.`
                  : lockedUntil === null
                    ? TOO_MANY_ATTEMPTS_FALLBACK
                    : "Ya puedes intentarlo de nuevo."}
              </p>
            </div>
          </div>
        ) : null}

        <form className="login__form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor={emailId}>Correo institucional</label>
            <input
              id={emailId}
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor={passwordId}>Contraseña</label>
            <input
              id={passwordId}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <button type="submit" className="button login__submit" disabled={sending || locked}>
            {submitLabel}
          </button>
        </form>

        <p className="login__footnote">
          Acceso protegido: los intentos fallidos se limitan por correo y por dirección IP.
        </p>
      </div>
    </main>
  );
}
