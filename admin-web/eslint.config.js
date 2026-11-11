import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["dist", "coverage", "playwright-report", "test-results", "src/api/schema.d.ts"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      jsxA11y.flatConfigs.recommended,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      // Guía 7.3: nada de HTML sin escapar ni sesión en el almacenamiento del navegador.
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: "No uses dangerouslySetInnerHTML (guía 7.3).",
        },
      ],
      "no-restricted-globals": [
        "error",
        { name: "localStorage", message: "La sesión no se guarda en localStorage (guía 7.3)." },
        { name: "sessionStorage", message: "La sesión vive en memoria (decisión 42)." },
      ],
    },
  },
);
