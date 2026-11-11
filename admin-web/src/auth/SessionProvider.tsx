import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createApiClient, type ApiClient } from "../api/client";
import type { components } from "../api/schema";
import { config } from "../config";
import { webLogin, webLogout, webRefresh, type WebTokens } from "./session";

type UserResponse = components["schemas"]["UserResponse"];

export type SessionStatus = "checking" | "signed-in" | "signed-out";

export type Session = {
  status: SessionStatus;
  user: { name: string } | null;
  /** Aviso para el inicio de sesión cuando la sesión terminó sin que la persona la cerrara. */
  notice: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  api: ApiClient;
};

export const SESSION_ENDED_MESSAGE = "Tu sesión terminó. Inicia sesión de nuevo.";
const ME_PATH = "/api/v1/me";
/** El acceso se renueva antes de vencer, al 80 % de su vida. */
const REFRESH_AT_FRACTION = 0.8;
const MS_PER_SECOND = 1000;

export const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession debe usarse dentro de <SessionProvider>.");
  }
  return session;
}

type Props = {
  children: ReactNode;
  /** Se llama al terminar la sesión, para borrar de memoria los datos consultados. */
  onSessionCleared?: () => void;
};

type State = { status: SessionStatus; user: { name: string } | null; notice: string | null };

export function SessionProvider({ children, onSessionCleared }: Props) {
  const [state, setState] = useState<State>({ status: "checking", user: null, notice: null });
  // El acceso vive solo en memoria (decisión 42): nunca en localStorage ni en el estado visible.
  const accessToken = useRef<string | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshing = useRef<Promise<string | null> | null>(null);
  const scheduledRefresh = useRef<() => void>(() => {});
  const onCleared = useRef(onSessionCleared);
  useEffect(() => {
    onCleared.current = onSessionCleared;
  }, [onSessionCleared]);

  const clearSession = useCallback((notice: string | null) => {
    accessToken.current = null;
    if (refreshTimer.current !== null) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
    setState({ status: "signed-out", user: null, notice });
    onCleared.current?.();
  }, []);

  const applyTokens = useCallback((tokens: WebTokens) => {
    accessToken.current = tokens.accessToken;
    if (refreshTimer.current !== null) {
      clearTimeout(refreshTimer.current);
    }
    refreshTimer.current = setTimeout(
      () => scheduledRefresh.current(),
      tokens.expiresIn * REFRESH_AT_FRACTION * MS_PER_SECOND,
    );
  }, []);

  /**
   * Un solo refresco a la vez: la cookie rota en cada uso y repetirla revoca la sesión.
   * Lo comparten el arranque (que React repite en desarrollo), el temporizador y los 401.
   */
  const refreshSession = useCallback((): Promise<string | null> => {
    refreshing.current ??= webRefresh()
      .then((tokens) => {
        if (tokens === null) {
          accessToken.current = null;
          return null;
        }
        applyTokens(tokens);
        return tokens.accessToken;
      })
      .finally(() => {
        refreshing.current = null;
      });
    return refreshing.current;
  }, [applyTokens]);

  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: config.apiBaseUrl,
        getAccessToken: () => accessToken.current,
        refresh: refreshSession,
        onSessionEnded: () => clearSession(SESSION_ENDED_MESSAGE),
      }),
    [refreshSession, clearSession],
  );

  useEffect(() => {
    scheduledRefresh.current = () => {
      refreshSession().then(
        (token) => {
          if (token === null) {
            clearSession(SESSION_ENDED_MESSAGE);
          }
        },
        // Sin red no se cierra la sesión: el siguiente 401 vuelve a intentar el refresco.
        () => {},
      );
    };
  }, [refreshSession, clearSession]);

  const loadUser = useCallback(async () => {
    const me = await api.get<UserResponse>(ME_PATH);
    setState({ status: "signed-in", user: { name: me.name }, notice: null });
  }, [api]);

  // Al cargar la página, la cookie de refresco recupera la sesión.
  useEffect(() => {
    let cancelled = false;
    refreshSession()
      .then(async (token) => {
        if (cancelled) {
          return;
        }
        if (token === null) {
          clearSession(null);
          return;
        }
        await loadUser();
      })
      .catch(() => {
        // Sin respuesta del servidor: se muestra el inicio de sesión, que informa el fallo al intentar.
        if (!cancelled) {
          clearSession(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refreshSession, loadUser, clearSession]);

  useEffect(
    () => () => {
      if (refreshTimer.current !== null) {
        clearTimeout(refreshTimer.current);
      }
    },
    [],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      applyTokens(await webLogin(email, password));
      await loadUser();
    },
    [applyTokens, loadUser],
  );

  const signOut = useCallback(async () => {
    try {
      await webLogout();
    } catch {
      // Aunque el servidor no responda, este navegador olvida el acceso.
    } finally {
      clearSession(null);
    }
  }, [clearSession]);

  const session = useMemo<Session>(
    () => ({ ...state, signIn, signOut, api }),
    [state, signIn, signOut, api],
  );

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}
