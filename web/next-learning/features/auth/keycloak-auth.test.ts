import { afterEach, describe, expect, it, vi } from "vitest";

async function loadAuthMode(value?: string) {
  if (value === undefined) {
    delete process.env.NEXT_PUBLIC_AUTH_MODE;
  } else {
    process.env.NEXT_PUBLIC_AUTH_MODE = value;
  }
  vi.resetModules();
  return import("./keycloak-auth");
}

afterEach(() => {
  delete process.env.NEXT_PUBLIC_AUTH_MODE;
  vi.resetModules();
});

describe("learner Keycloak auth mode", () => {
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
