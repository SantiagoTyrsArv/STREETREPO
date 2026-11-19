import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { App } from "./App";

it("tiene una región principal", () => {
  render(<App />);
  expect(screen.getByRole("main")).toBeInTheDocument();
});
