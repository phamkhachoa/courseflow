import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const CertificatesPage = lazy(() => import("./pages").then(({ CertificatesPage }) => ({ default: CertificatesPage })));

export const certificatesRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(CertificatesPage) }];
