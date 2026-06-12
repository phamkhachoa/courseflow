import { describe, expect, it, beforeEach } from "vitest";
import { sessionStore } from "@/shared/auth/session-store";

describe("sessionStore", () => {
  beforeEach(() => localStorage.clear());

  it("returns null when nothing stored", () => {
    expect(sessionStore.read()).toBeNull();
  });

  it("round-trips a session", () => {
    const session = {
      accessToken: "a",
      refreshToken: "r",
      user: { id: 1, email: "x@y.z", fullName: "X", role: "ADMIN", status: "ACTIVE" }
    };
    sessionStore.write(session);
    expect(sessionStore.read()).toEqual(session);
  });

  it("clears the session", () => {
    sessionStore.write({
      accessToken: "a",
      refreshToken: "r",
      user: { id: 1, email: "x@y.z", fullName: "X", role: "ADMIN", status: "ACTIVE" }
    });
    sessionStore.clear();
    expect(sessionStore.read()).toBeNull();
  });

  it("returns null on corrupt JSON", () => {
    localStorage.setItem("courseflow.admin.session", "{not-json");
    expect(sessionStore.read()).toBeNull();
  });
});
