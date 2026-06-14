import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const CourseModulesPage = lazy(() => import("./pages").then(({ CourseModulesPage }) => ({ default: CourseModulesPage })));

export const courseModulesRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(CourseModulesPage) }];
