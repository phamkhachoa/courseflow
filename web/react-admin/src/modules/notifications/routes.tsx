import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const NotificationsPage = lazy(() => import("./pages").then(({ NotificationsPage }) => ({ default: NotificationsPage })));

export const notificationsRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(NotificationsPage) }];
