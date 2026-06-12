"use client";

import { useEffect } from "react";

export function ScrollToTopOnMount() {
  useEffect(() => {
    if (window.location.hash) return;
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, []);

  return null;
}
