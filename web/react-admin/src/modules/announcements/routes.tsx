import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const AnnouncementCreatePage = lazy(() => import("./pages").then(({ AnnouncementCreatePage }) => ({ default: AnnouncementCreatePage })));
const AnnouncementDetailPage = lazy(() => import("./pages").then(({ AnnouncementDetailPage }) => ({ default: AnnouncementDetailPage })));
const AnnouncementListPage = lazy(() => import("./pages").then(({ AnnouncementListPage }) => ({ default: AnnouncementListPage })));

export const announcementsRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(AnnouncementListPage) },
  { path: "new", element: lazyRouteElement(AnnouncementCreatePage) },
  { path: ":id", element: lazyRouteElement(AnnouncementDetailPage) }
];
