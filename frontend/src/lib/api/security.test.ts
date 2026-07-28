import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Garantiza que la API key de analista no se filtre al bundle del navegador:
 * ningún módulo client-safe referencia ANALYST_API_KEY / X-API-Key.
 */
describe("seguridad BFF", () => {
  it("el cliente de navegador no menciona la API key", () => {
    const clientSrc = readFileSync(
      join(process.cwd(), "src/lib/api/client.ts"),
      "utf8",
    );
    expect(clientSrc).not.toMatch(/ANALYST_API_KEY/);
    expect(clientSrc).not.toMatch(/X-API-Key/);
    expect(clientSrc).not.toMatch(/NEXT_PUBLIC_.*KEY/);
  });

  it("solo el servidor inyecta X-API-Key", () => {
    const serverSrc = readFileSync(
      join(process.cwd(), "src/lib/api/server.ts"),
      "utf8",
    );
    expect(serverSrc).toMatch(/ANALYST_API_KEY/);
    expect(serverSrc).toMatch(/X-API-Key/);
  });
});
