import type { RouteObject } from "react-router-dom";
import { LiveSessionDetailPage, LiveSessionsPage } from "./pages";

export const liveSessionsRoutes: RouteObject[] = [
  { index: true, element: <LiveSessionsPage /> },
  { path: ":sessionId", element: <LiveSessionDetailPage /> },
];
