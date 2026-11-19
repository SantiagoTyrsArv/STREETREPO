import { afterEach, describe, expect, it, vi } from "vitest";
import { bindAnchorNavigation } from "./anchors";

function setup() {
  document.body.innerHTML = `
    <a id="salto" href="#descarga">Saltar</a>
    <a id="roto" href="#no-existe">Roto</a>
    <a id="externo" href="https://example.invalid/">Externo</a>
    <section id="descarga" tabindex="-1">Descarga</section>`;
  const scrollTo = vi.fn();
  const unbind = bindAnchorNavigation(document, scrollTo);
  return { scrollTo, unbind };
}

function click(id: string, init: MouseEventInit = {}) {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true, ...init });
  document.getElementById(id)?.dispatchEvent(event);
  return event;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("bindAnchorNavigation", () => {
  it("lleva el desplazamiento y el foco al destino del enlace interno", () => {
    const { scrollTo, unbind } = setup();

    const event = click("salto");

    const target = document.getElementById("descarga");
    expect(event.defaultPrevented).toBe(true);
    expect(scrollTo).toHaveBeenCalledWith(target);
    expect(document.activeElement).toBe(target);
    expect(window.location.hash).toBe("#descarga");
    unbind();
  });

  it("no toca enlaces externos, destinos inexistentes ni clics con modificadores", () => {
    const { scrollTo, unbind } = setup();

    expect(click("externo").defaultPrevented).toBe(false);
    expect(click("roto").defaultPrevented).toBe(false);
    expect(click("salto", { ctrlKey: true }).defaultPrevented).toBe(false);
    expect(scrollTo).not.toHaveBeenCalled();
    unbind();
  });

  it("deja de escuchar al desvincularse", () => {
    const { scrollTo, unbind } = setup();
    unbind();

    click("salto");

    expect(scrollTo).not.toHaveBeenCalled();
  });
});
