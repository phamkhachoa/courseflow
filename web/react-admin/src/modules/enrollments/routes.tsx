import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const EnrollmentsPage = lazy(() => import("./pages").then(({ EnrollmentsPage }) => ({ default: EnrollmentsPage })));

export const enrollmentsRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(EnrollmentsPage) }];
