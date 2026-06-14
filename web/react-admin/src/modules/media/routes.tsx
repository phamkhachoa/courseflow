import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const MediaPage = lazy(() => import("./pages").then(({ MediaPage }) => ({ default: MediaPage })));

export const mediaRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(MediaPage) }];
