import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const PortfolioPage = lazy(() => import("./pages").then(({ PortfolioPage }) => ({ default: PortfolioPage })));

export const portfolioRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(PortfolioPage) }];
