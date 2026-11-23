import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { useClientCheck } from "./useClientCheck";

function Probe({ check }: { check: () => boolean }) {
  return <p>{useClientCheck(check) ? "sí" : "no"}</p>;
}

describe("useClientCheck", () => {
  it("devuelve false en el HTML del servidor", () => {
    expect(renderToString(<Probe check={() => true} />)).toContain("no");
  });

  it("devuelve el valor real tras el montaje", () => {
    render(<Probe check={() => true} />);
    expect(screen.getByText("sí")).toBeInTheDocument();
  });
});
