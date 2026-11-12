import { expect, test, type Page } from "@playwright/test";

/**
 * Flujos críticos del panel (HU-08, HU-12 y HU-14) contra la API y la base reales, con los
 * datos de `seed-demo`. Las credenciales llegan por variables de entorno: nunca van en el
 * repositorio.
 */
const email = process.env.E2E_ADMIN_EMAIL;
const password = process.env.E2E_ADMIN_PASSWORD;

test.beforeAll(() => {
  if (!email || !password) {
    throw new Error(
      "Faltan E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD. Usa infra/scripts/e2e-panel.sh, que crea la cuenta.",
    );
  }
});

async function signIn(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeVisible();
  await page.getByLabel("Correo institucional").fill(email ?? "");
  await page.getByLabel("Contraseña").fill(password ?? "");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: "Priorización de reportes" })).toBeVisible();
}

function rankingRows(page: Page) {
  return page.locator("table.ranking tbody tr");
}

test("login_and_see_ranking", async ({ page }) => {
  // El proveedor de teselas bloquea las peticiones sin Referer (responde una imagen de
  // «Access blocked»): con «Referrer-Policy: no-referrer» de nginx, el mapa debe enviarlo igual.
  const tile = page.waitForRequest((request) => /\/\d+\/\d+\/\d+\.png/.test(request.url()));
  await signIn(page);
  expect(await (await tile).headerValue("referer")).toBe(`${new URL(page.url()).origin}/`);

  // Ranking con los reportes de demostración, de mayor a menor U.
  await expect(rankingRows(page).first()).toBeVisible();
  const scores = (await page.locator("table.ranking td.ranking__score").allTextContents()).map(
    (text) => Number(text.replace(",", ".")),
  );
  expect(scores.length).toBeGreaterThan(1);
  expect(scores).toEqual([...scores].sort((a, b) => b - a));

  // Mapa de calor con la atribución obligatoria de OpenStreetMap.
  const map = page.getByRole("region", { name: "Mapa de calor", exact: true });
  await expect(map.locator(".leaflet-container")).toBeVisible();
  await expect(map.getByRole("link", { name: "OpenStreetMap" })).toBeVisible();

  // La sesión vive en memoria: al recargar se recupera con la cookie de refresco.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Priorización de reportes" })).toBeVisible();
  await expect(rankingRows(page).first()).toBeVisible();

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeVisible();
  // Sin sesión, una ruta protegida vuelve al inicio de sesión.
  await page.goto("/pesos");
  await expect(page.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeVisible();
});

test("change_status_appears_in_history", async ({ page }) => {
  const note = `Prueba E2E ${Date.now()}: cuadrilla asignada`;
  await signIn(page);

  await page.getByLabel("Estado", { exact: true }).selectOption({ label: "Estado: evaluados" });
  await expect(rankingRows(page).first().getByText("Evaluado")).toBeVisible();
  await rankingRows(page).first().getByRole("link").click();
  await expect(page).toHaveURL(/\/reportes\/[0-9a-f-]{36}$/);

  await page.getByRole("radio", { name: "Priorizado" }).check();
  await page.getByLabel("Observación (queda en el historial)").fill(note);
  await page.getByRole("button", { name: "Guardar cambio" }).click();

  await expect(page.getByText("Estado actualizado.")).toBeVisible();
  const lastChange = page.locator("ol.history li").last();
  await expect(lastChange).toContainText("Evaluado → Priorizado");
  await expect(lastChange).toContainText(note);
  // El servidor ya no ofrece volver a «Priorizado»: solo queda avanzar a «Reparado».
  await expect(page.getByRole("radio", { name: "Priorizado" })).toHaveCount(0);
  await expect(page.getByRole("radio", { name: "Reparado" })).toBeVisible();

  // Sigue ahí al recargar: quedó guardado, no solo en la pantalla.
  await page.reload();
  await expect(page.locator("ol.history li").last()).toContainText(note);
});

test("save_weights_creates_version", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Pesos del modelo" }).click();
  await expect(
    page.getByRole("heading", { name: "Pesos del modelo de priorización" }),
  ).toBeVisible();

  const severity = page.getByRole("textbox", { name: /Severidad/ });
  const flow = page.getByRole("textbox", { name: /Flujo vehicular/ });
  const proximity = page.getByRole("textbox", { name: /Proximidad/ });
  const save = page.getByRole("button", { name: "Guardar y recalcular puntajes" });
  await expect(severity).toHaveValue(/^\d,\d\d$/);
  // Alterna entre dos configuraciones para que la prueba se pueda repetir.
  const next =
    (await severity.inputValue()) === "0,50" ? ["0,40", "0,40", "0,20"] : ["0,50", "0,30", "0,20"];
  const [w1, w2, w3] = next as [string, string, string];

  // Mientras no sumen 1,00 no se puede guardar.
  await severity.fill("0,9");
  await expect(page.getByText("Deben sumar exactamente 1,00")).toBeVisible();
  await expect(save).toBeDisabled();

  await severity.fill(w1);
  await flow.fill(w2);
  await proximity.fill(w3);
  await expect(page.getByText("Los pesos suman 1,00")).toBeVisible();
  await save.click();

  await expect(page.getByText(/Pesos guardados\. Se recalcul/)).toBeVisible();
  const newest = page.locator("ul.versions li").first();
  await expect(newest).toContainText(`${w1} / ${w2} / ${w3}`);
  await expect(newest).toContainText("Vigente");
  await expect(page.locator("ul.versions").getByText("Vigente")).toHaveCount(1);

  // El ranking usa los pesos nuevos: la fórmula del encabezado los muestra.
  await page.getByRole("link", { name: "Priorización" }).click();
  const short = (weight: string) => weight.replace(/0$/, ""); // «0,40» se muestra «0,4»
  await expect(page.locator(".page__subtitle")).toContainText(
    `U = ${short(w1)}·S + ${short(w2)}·F + ${short(w3)}·P`,
  );
});
