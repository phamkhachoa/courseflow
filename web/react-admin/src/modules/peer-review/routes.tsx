import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const PeerReviewPage = lazy(() => import("./pages").then(({ PeerReviewPage }) => ({ default: PeerReviewPage })));

export const peerReviewRoutes: RouteObject[] = [{ index: true, element: lazyRouteElement(PeerReviewPage) }];
