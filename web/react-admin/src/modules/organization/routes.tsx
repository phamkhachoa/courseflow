import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const OrganizationPage = lazy(() => import("./pages").then(({ OrganizationPage }) => ({ default: OrganizationPage })));

export const organizationRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(OrganizationPage) }];
