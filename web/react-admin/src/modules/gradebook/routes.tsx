import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const GradebookPage = lazy(() => import("./pages").then(({ GradebookPage }) => ({ default: GradebookPage })));

export const gradebookRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(GradebookPage) }];
