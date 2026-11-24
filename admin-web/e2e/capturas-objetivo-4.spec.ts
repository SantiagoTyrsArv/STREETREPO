import { expect, test, type Page } from "@playwright/test";

/**
 * Capturas del objetivo 4 (HU-09) para la evidencia en Linear. No es una prueba: recorre el
 * flujo de `validation.spec.ts` y guarda pantallas en `docs/capturas/objetivo-4/`. Solo corre a
 * pedido: `CAPTURAS=1 infra/scripts/e2e-panel.sh e2e/capturas-objetivo-4.spec.ts` (datos de
 * demostración); sin `CAPTURAS` se omite, para no abrir rondas en cada ejecución de las E2E.
 */
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };
const evaluator = {
  email: process.env.E2E_EVALUATOR_EMAIL,
  password: process.env.E2E_EVALUATOR_PASSWORD,
};
const OUT = "../docs/capturas/objetivo-4";

test.skip(!process.env.CAPTURAS, "Solo se ejecuta con CAPTURAS=1.");

test.use({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });

async function signIn(page: Page, account: typeof admin, home: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Correo institucional").fill(account.email ?? "");
  await page.getByLabel("Contraseña").fill(account.password ?? "");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: home })).toBeVisible();
}

async function shot(page: Page, name: string, fullPage = false): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage });
}

test("capturas del objetivo 4", async ({ page, browser }) => {
  test.setTimeout(180_000);
  const roundName = "Ronda de demostración";

  await signIn(page, admin, "Priorización de reportes");
  await page.getByRole("link", { name: "Comparación" }).click();
  await expect(page.getByRole("table", { name: "Zonas del estudio" })).toBeVisible();
  await shot(page, "01-zonas-del-estudio");

  await page.getByRole("tab", { name: "Rondas" }).click();
  await page.getByLabel("Nombre de la ronda").fill(roundName);
  await page.getByLabel(/Reportes por zona/).fill("5");
  await shot(page, "02-abrir-ronda");
  await page.getByRole("button", { name: "Abrir ronda" }).click();
  await expect(
    page.getByRole("table", { name: `Avance de la ronda «${roundName}»` }),
  ).toBeVisible();
  await shot(page, "03-ronda-abierta-avance");

  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
    locale: "es-CO",
    timezoneId: "America/Bogota",
  });
  const ev = await ctx.newPage();
  await signIn(ev, evaluator, "Mis evaluaciones");
  await shot(ev, "04-evaluador-mis-evaluaciones");

  const zoneLinks = ev.getByRole("link", { name: /^Ordenar la zona / });
  const zones = await zoneLinks.count();
  for (let i = 0; i < zones; i += 1) {
    await ev
      .getByRole("link", { name: /^Ordenar la zona / })
      .first()
      .click();
    await expect(ev.getByRole("heading", { name: /^Zona / })).toBeVisible();
    if (i === 0) await shot(ev, "05-vista-a-ciegas", true);
    const list = ev
      .getByRole("list", { name: "Reportes de la zona, del más urgente al menos urgente" })
      .getByRole("heading");
    await expect(list).toHaveCount(5);
    const titles = await list.allTextContents();
    await ev
      .getByRole("button", { name: `Subir ${titles[titles.length - 1]}` })
      .first()
      .click();
    await ev.getByRole("button", { name: "Enviar este orden" }).click();
    if (i === 0) await shot(ev, "06-confirmar-envio");
    await ev.getByRole("button", { name: "Sí, enviar" }).click();
    await expect(ev.getByRole("status").filter({ hasText: /Enviaste el orden/ })).toBeVisible();
    await ev.goto("/");
    await expect(ev.getByRole("heading", { name: "Mis evaluaciones" })).toBeVisible();
  }
  await shot(ev, "07-evaluador-zonas-enviadas");
  await ctx.close();

  await page.reload();
  await page.getByRole("tab", { name: "Rondas" }).click();
  await expect(
    page.getByRole("table", { name: `Avance de la ronda «${roundName}»` }),
  ).toContainText("Evaluador 1");
  await shot(page, "08-avance-con-evaluador");
  await page.getByRole("button", { name: "Cerrar ronda" }).click();
  await page.getByRole("button", { name: "Sí, cerrar la ronda" }).click();
  await expect(page.getByRole("button", { name: "Abrir ronda" })).toBeVisible();

  await page.getByRole("tab", { name: "Resultados" }).click();
  await expect(
    page.getByRole("region", { name: `Cifras de la ronda «${roundName}»` }),
  ).toBeVisible();
  await shot(page, "09-resultados", true);
});
