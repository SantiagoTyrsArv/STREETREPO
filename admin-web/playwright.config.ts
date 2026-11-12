import { defineConfig, devices } from "@playwright/test";

/**
 * Pruebas de punta a punta del panel contra el stack de Docker Compose (decisión 77).
 * Se lanzan con `infra/scripts/e2e-panel.sh`, que levanta un stack aparte con datos de
 * demostración; no corren en la CI porque necesitan la base con los datos de OSM.
 */
export default defineConfig({
  testDir: "e2e",
  // Las pruebas comparten la base (estados y pesos): van de una en una y en orden.
  workers: 1,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
