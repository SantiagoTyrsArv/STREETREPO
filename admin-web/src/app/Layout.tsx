import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import iconMap from "../assets/icon-map.svg";
import iconPin from "../assets/icon-pin.svg";
import iconSliders from "../assets/icon-sliders.svg";
import { useSession } from "../auth/SessionProvider";
import "./layout.css";

const MENU = [
  { to: "/priorizacion", label: "Priorización", icon: iconMap },
  { to: "/pesos", label: "Pesos del modelo", icon: iconSliders },
] as const;

const INITIALS_LENGTH = 2;

/** Iniciales del avatar: primera letra de las dos primeras palabras del nombre. */
function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, INITIALS_LENGTH)
    .map((word) => word.charAt(0).toUpperCase())
    .join("");
}

/** Armazón del panel: barra lateral (Figma 8:3) y el contenido de la ruta. */
export function Layout() {
  const { user, signOut } = useSession();
  const [signingOut, setSigningOut] = useState(false);
  const name = user?.name ?? "";

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="brand-mark">
            <img src={iconPin} alt="" width={22} height={22} />
          </span>
          <div>
            <p className="sidebar__brand-name">Street Repo</p>
            <p className="sidebar__caption">Panel de gestión</p>
          </div>
        </div>

        <nav className="sidebar__menu" aria-label="Secciones del panel">
          {MENU.map((item) => (
            <NavLink key={item.to} to={item.to} className="sidebar__link">
              <img src={item.icon} alt="" width={20} height={20} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__user">
          <span className="sidebar__avatar" aria-hidden="true">
            {initials(name)}
          </span>
          <div className="sidebar__user-text">
            <p className="sidebar__user-name">{name}</p>
            <p className="sidebar__caption">Sec. de Infraestructura</p>
          </div>
        </div>
        <button
          type="button"
          className="sidebar__sign-out"
          onClick={handleSignOut}
          disabled={signingOut}
        >
          Cerrar sesión
        </button>
      </aside>

      <main className="layout__content">
        <Outlet />
      </main>
    </div>
  );
}
