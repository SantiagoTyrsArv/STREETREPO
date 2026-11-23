/**
 * Roles del personal que entra al panel (ADR 0008). El servidor vuelve a verificar el rol en
 * cada ruta: esto solo decide qué pantallas se muestran.
 */
export type StaffRole = "administrador" | "evaluador";

const STAFF_ROLES: readonly string[] = ["administrador", "evaluador"] satisfies StaffRole[];

export function isStaffRole(role: string): role is StaffRole {
  return STAFF_ROLES.includes(role);
}

/** Pantalla de inicio de cada rol. */
export const HOME_PATHS: Record<StaffRole, string> = {
  administrador: "/priorizacion",
  evaluador: "/evaluacion",
};
