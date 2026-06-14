import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const AnalyticsPage = lazy(() => import("./pages").then(({ AnalyticsPage }) => ({ default: AnalyticsPage })));
const ReportingPage = lazy(() => import("./reporting-page").then(({ ReportingPage }) => ({ default: ReportingPage })));

export const analyticsRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(AnalyticsPage) },
  { path: "reporting", element: lazyRouteElement(ReportingPage) }
];
