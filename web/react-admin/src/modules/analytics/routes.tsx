import type { RouteObject } from "react-router-dom";
import { AnalyticsPage } from "./pages";
import { ReportingPage } from "./reporting-page";

export const analyticsRoutes: RouteObject[] = [
  { index: true, element: <AnalyticsPage /> },
  { path: "reporting", element: <ReportingPage /> }
];
