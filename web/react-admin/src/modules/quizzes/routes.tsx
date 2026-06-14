import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const AttemptDetailPage = lazy(() => import("./pages").then(({ AttemptDetailPage }) => ({ default: AttemptDetailPage })));
const EffectiveScorePage = lazy(() => import("./pages").then(({ EffectiveScorePage }) => ({ default: EffectiveScorePage })));
const QuizzesPage = lazy(() => import("./pages").then(({ QuizzesPage }) => ({ default: QuizzesPage })));

export const quizzesRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(QuizzesPage) },
  { path: ":attemptId/detail", element: lazyRouteElement(AttemptDetailPage) },
  { path: "score", element: lazyRouteElement(EffectiveScorePage) }
];
