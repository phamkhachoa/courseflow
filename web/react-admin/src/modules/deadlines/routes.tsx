import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const DeadlinesPage = lazy(() => import("./pages").then(({ DeadlinesPage }) => ({ default: DeadlinesPage })));

export const deadlinesRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(DeadlinesPage) }];
