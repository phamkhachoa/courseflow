import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const LiveSessionDetailPage = lazy(() => import("./pages").then(({ LiveSessionDetailPage }) => ({ default: LiveSessionDetailPage })));
const LiveSessionsPage = lazy(() => import("./pages").then(({ LiveSessionsPage }) => ({ default: LiveSessionsPage })));

export const liveSessionsRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(LiveSessionsPage) },
  { path: ":sessionId", element: lazyRouteElement(LiveSessionDetailPage) },
];
