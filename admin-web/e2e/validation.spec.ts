import { expect, test, type Page } from "@playwright/test";

/**
 * Comparación con el panel de referencia (objetivo 4, HU-09) de punta a punta: el
 * administrador abre una ronda, la evaluadora ordena una zona a ciegas con el teclado y la
 * envía, y el administrador la cierra, ve los resultados y descarga la ficha. Usa las zonas
 * de prueba que crea `infra/scripts/e2e-panel.sh`; los datos son de demostración.
 */
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };
const evaluator = {
  email: process.env.E2E_EVALUATOR_EMAIL,
  password: process.env.E2E_EVALUATOR_PASSWORD,
};

test.beforeAll(() => {
  if (!admin.email || !admin.password || !evaluator.email || !evaluator.password) {
    throw new Error(
      "Faltan las credenciales E2E del administrador o de la evaluadora. Usa infra/scripts/e2e-panel.sh.",
    );
  }
});

async function signIn(page: Page, account: typeof admin, home: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Correo institucional").fill(account.email ?? "");
  await page.getByLabel("Contraseña").fill(account.password ?? "");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: home })).toBeVisible();
}

function cardTitles(page: Page) {
  return page
    .getByRole("list", { name: "Reportes de la zona, del más urgente al menos urgente" })
    .getByRole("heading")
    .allTextContents();
}

test("ronda de evaluación completa", async ({ page, browser }) => {
  const roundName = `E2E ${Date.now()}`;

  // 1. El administrador ve las zonas y abre la ronda.
  await signIn(page, admin, "Priorización de reportes");
  await page.getByRole("link", { name: "Comparación" }).click();
  await expect(page.getByRole("table", { name: "Zonas del estudio" })).toContainText("E2E Oeste");
  await expect(
    page
      .getByRole("region", { name: "Mapa de las zonas del estudio" })
      .locator(".leaflet-container"),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Rondas" }).click();
  await page.getByLabel("Nombre de la ronda").fill(roundName);
  await page.getByLabel(/Reportes por zona/).fill("5");
  await page.getByRole("button", { name: "Abrir ronda" }).click();
  const progress = page.getByRole("table", { name: `Avance de la ronda «${roundName}»` });
  await expect(progress).toContainText("Ningún evaluador todavía");

  // 2. La evaluadora, en otra sesión, ordena una zona a ciegas.
  const evaluatorContext = await browser.newContext();
  const evalPage = await evaluatorContext.newPage();
  await signIn(evalPage, evaluator, "Mis evaluaciones");
  await expect(evalPage.getByRole("link", { name: "Priorización" })).toHaveCount(0);
  await evalPage
    .getByRole("link", { name: /^Ordenar la zona / })
    .first()
    .click();
  await expect(evalPage.getByRole("heading", { name: /^Zona / })).toBeVisible();
  // Nada del motor en la vista a ciegas.
  await expect(evalPage.locator("body")).not.toContainText(/puntaje|urgencia|confirmaci/i);

  const before = await cardTitles(evalPage);
  expect(before).toHaveLength(5);
  // Arrastre con el teclado (@dnd-kit): tomar la primera tarjeta y bajarla una posición.
  const handle = evalPage.getByRole("button", { name: `Arrastrar ${before[0]}` }).first();
  await handle.focus();
  // @dnd-kit mide las tarjetas al tomar una: cada tecla espera el estado que deja la anterior.
  await evalPage.keyboard.press("Space");
  await expect(handle).toHaveAttribute("aria-pressed", "true");
  const cards = evalPage
    .getByRole("list", { name: "Reportes de la zona, del más urgente al menos urgente" })
    .getByRole("listitem");
  const top = async (index: number) => (await cards.nth(index).boundingBox())?.y ?? 0;
  await evalPage.keyboard.press("ArrowDown");
  // Durante el arrastre la tarjeta solo se desplaza (y la página puede moverse con ella):
  // basta con que quede por debajo de su vecina.
  await expect.poll(async () => (await top(0)) - (await top(1))).toBeGreaterThan(0);
  await evalPage.keyboard.press("Space");
  await expect.poll(() => cardTitles(evalPage)).toEqual([before[1], before[0], ...before.slice(2)]);
  // Y con los botones: la última sube una posición. Se busca el botón dentro de la quinta
  // tarjeta y no por su nombre: dos reportes de la muestra pueden tener la misma vía
  // («Vía sin nombre») y el nombre señalaría a otra tarjeta.
  await cards
    .nth(4)
    .getByRole("button", { name: /^Subir / })
    .click();
  await expect
    .poll(async () => (await cardTitles(evalPage)).slice(3))
    .toEqual([before[4], before[3]]);
  const sent = await cardTitles(evalPage);

  // El borrador sobrevive a una recarga.
  await evalPage.reload();
  await expect.poll(() => cardTitles(evalPage)).toEqual(sent);

  await evalPage.getByRole("button", { name: "Enviar este orden" }).click();
  await evalPage.getByRole("button", { name: "Sí, enviar" }).click();
  await expect(evalPage.getByRole("status").filter({ hasText: /Enviaste el orden/ })).toBeVisible();
  await expect(evalPage.getByText("Enviada", { exact: true })).toBeVisible();
  await evaluatorContext.close();

  // 3. El administrador ve el avance, cierra la ronda y revisa los resultados.
  await page.reload();
  await page.getByRole("tab", { name: "Rondas" }).click();
  await expect(progress).toContainText("Evaluador 1");
  await page.getByRole("button", { name: "Cerrar ronda" }).click();
  await page.getByRole("button", { name: "Sí, cerrar la ronda" }).click();
  await expect(page.getByRole("button", { name: "Abrir ronda" })).toBeVisible();

  await page.getByRole("tab", { name: "Resultados" }).click();
  await expect(
    page.getByRole("region", { name: `Cifras de la ronda «${roundName}»` }),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Prueba entre zonas" })).toContainText(
    "No se calculó",
  );
  await expect(page.getByRole("table", { name: /^Ranking comparado · zona / })).toBeVisible();
  await expect(
    page.getByText(
      "Estos valores describen la ronda; la interpretación de las hipótesis se hace en la tesis.",
    ),
  ).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar ficha (CSV)" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^ronda-e2e-\d+-ficha\.csv$/);
  const content = await (await file.createReadStream()).toArray();
  const text = Buffer.concat(content).toString("utf-8");
  expect(text.startsWith("﻿id_reporte,zona,concentracion")).toBe(true);
  expect(text).toContain("orden_evaluador_1");
  expect(text).not.toContain(evaluator.email ?? "");
});
