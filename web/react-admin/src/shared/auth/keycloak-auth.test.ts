import { afterEach, describe, expect, it, vi } from "vitest";

async function loadAuthMode(value?: string) {
  if (value === undefined) {
    vi.unstubAllEnvs();
  } else {
    vi.stubEnv("VITE_AUTH_MODE", value);
  }
  vi.resetModules();
  return import("./keycloak-auth");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("admin Keycloak auth mode", () => {
  it("defaults to Keycloak when auth mode is not configured", async () => {
    const auth = await loadAuthMode();

    expect(auth.keycloakAuthEnabled).toBe(true);
  });

  it("only disables Keycloak for explicit legacy mode", async () => {
    const legacy = await loadAuthMode("legacy");
    expect(legacy.keycloakAuthEnabled).toBe(false);

    const keycloak = await loadAuthMode("keycloak");
    expect(keycloak.keycloakAuthEnabled).toBe(true);
  });
});
