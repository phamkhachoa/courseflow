"use client";

import { useEffect, useState } from "react";
import { learnerSession, type StoredSession } from "@/shared/api/client";

export function useLearnerSession() {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSession(learnerSession.read());
    setHydrated(true);
    return learnerSession.subscribe((nextSession) => {
      setSession(nextSession);
      setHydrated(true);
    });
  }, []);

  return { session, hydrated };
}
