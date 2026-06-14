import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const AssignmentCreatePage = lazy(() => import("./pages").then(({ AssignmentCreatePage }) => ({ default: AssignmentCreatePage })));
const AssignmentDetailPage = lazy(() => import("./pages").then(({ AssignmentDetailPage }) => ({ default: AssignmentDetailPage })));
const AssignmentListPage = lazy(() => import("./pages").then(({ AssignmentListPage }) => ({ default: AssignmentListPage })));
const RubricPage = lazy(() => import("./pages").then(({ RubricPage }) => ({ default: RubricPage })));
const SubmissionsPage = lazy(() => import("./pages").then(({ SubmissionsPage }) => ({ default: SubmissionsPage })));

export const assignmentsRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(AssignmentListPage) },
  { path: "new", element: lazyRouteElement(AssignmentCreatePage) },
  { path: ":id", element: lazyRouteElement(AssignmentDetailPage) },
  { path: ":id/submissions", element: lazyRouteElement(SubmissionsPage) },
  { path: ":id/rubric", element: lazyRouteElement(RubricPage) }
];
