import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * Revisión automática de accesibilidad del panel (fase 8, WCAG 2.2 AA) con axe, contra la API
 * y la base reales del stack de E2E. Falla con hallazgos serios o críticos; los menores se
 * listan en el informe `docs/accesibilidad/revision-fase-8.md`.
 *
 * Abre una ronda de evaluación para revisar la vista a ciegas y la cierra al final, para no
 * dejarle una ronda abierta a `validation.spec.ts`.
 */
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };
const evaluator = {
  email: process.env.E2E_EVALUATOR_EMAIL,
  password: process.env.E2E_EVALUATOR_PASSWORD,
};

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test.beforeAll(() => {
  if (!admin.email || !admin.password || !evaluator.email || !evaluator.password) {
    throw new Error("Faltan las credenciales de E2E. Usa infra/scripts/e2e-panel.sh.");
  }
});

async function expectNoSeriousViolations(page: Page, screen: string): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  if (process.env.A11Y_LIST) {
    // Para el informe: todos los hallazgos, también los moderados y menores.
    console.log(
      `A11Y|${screen}|total|${results.violations.length}|${results.passes.length} reglas cumplidas`,
    );
    for (const v of results.violations) {
      console.log(`A11Y|${screen}|${v.impact}|${v.id}|${v.help}|${v.nodes.length}`);
    }
  }
  const serious = results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => ({
      screen,
      id: v.id,
      impact: v.impact,
      help: v.help,
      targets: v.nodes.map((n) => n.target.join(" ")).slice(0, 5),
    }));
  expect(serious, `Hallazgos serios o críticos en «${screen}»`).toEqual([]);
}

async function signIn(page: Page, account: typeof admin, home: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Correo institucional").fill(account.email ?? "");
  await page.getByLabel("Contraseña").fill(account.password ?? "");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: home })).toBeVisible();
}

test("inicio de sesión, también con el error de credenciales", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeVisible();
  await expectNoSeriousViolations(page, "Inicio de sesión");

  // Un correo que no existe: no suma intentos fallidos a la cuenta real de las pruebas.
  await page.getByLabel("Correo institucional").fill(`nadie-${Date.now()}@example.com`);
  await page.getByLabel("Contraseña").fill("contraseña-equivocada");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expectNoSeriousViolations(page, "Inicio de sesión con error");
});

test("pantallas del administrador y del evaluador", async ({ page, browser }) => {
  await signIn(page, admin, "Priorización de reportes");
  await expect(page.locator("table.ranking tbody tr").first()).toBeVisible();
  await expectNoSeriousViolations(page, "Priorización");

  await page.locator("table.ranking a.ranking__address").first().click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expectNoSeriousViolations(page, "Detalle y estado");

  await page.goto("/pesos");
  const severity = page.getByRole("textbox", { name: /Severidad/ });
  await expect(severity).toBeVisible();
  await expectNoSeriousViolations(page, "Pesos del modelo");
  await severity.fill("0,49");
  await expect(page.getByRole("alert")).toContainText("Deben sumar exactamente 1,00");
  await expectNoSeriousViolations(page, "Pesos del modelo con error de suma");

  await page.goto("/comparacion");
  await expect(page.getByRole("table", { name: "Zonas del estudio" })).toBeVisible();
  await expectNoSeriousViolations(page, "Comparación · Zonas");

  const roundName = `A11y ${Date.now()}`;
  await page.getByRole("tab", { name: "Rondas" }).click();
  await page.getByLabel("Nombre de la ronda").fill(roundName);
  await page.getByLabel(/Reportes por zona/).fill("5");
  await page.getByRole("button", { name: "Abrir ronda" }).click();
  await expect(
    page.getByRole("table", { name: `Avance de la ronda «${roundName}»` }),
  ).toBeVisible();
  await expectNoSeriousViolations(page, "Comparación · Rondas");

  const evaluatorContext = await browser.newContext();
  const evalPage = await evaluatorContext.newPage();
  await signIn(evalPage, evaluator, "Mis evaluaciones");
  await expectNoSeriousViolations(evalPage, "Mis evaluaciones");
  await evalPage
    .getByRole("link", { name: /^Ordenar la zona / })
    .first()
    .click();
  await expect(evalPage.getByRole("heading", { name: /^Zona / })).toBeVisible();
  await expectNoSeriousViolations(evalPage, "Vista a ciegas");
  await evaluatorContext.close();

  await page.getByRole("button", { name: "Cerrar ronda" }).click();
  await page.getByRole("button", { name: "Sí, cerrar la ronda" }).click();
  await expect(page.getByRole("button", { name: "Abrir ronda" })).toBeVisible();
  await page.getByRole("tab", { name: "Resultados" }).click();
  await expect(
    page.getByRole("region", { name: `Cifras de la ronda «${roundName}»` }),
  ).toBeVisible();
  await expectNoSeriousViolations(page, "Comparación · Resultados");
});
