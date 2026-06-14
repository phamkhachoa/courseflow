import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const SearchPage = lazy(() => import("./pages").then(({ SearchPage }) => ({ default: SearchPage })));

export const searchRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(SearchPage) }];
