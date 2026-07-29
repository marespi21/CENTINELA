import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Limpia el DOM después de cada test para que los renders no se acumulen entre
// casos (evita "Found multiple elements" cuando dos tests renderizan el mismo
// texto). vitest.config.ts no usa globals, así que se registra explícitamente.
afterEach(() => cleanup());
