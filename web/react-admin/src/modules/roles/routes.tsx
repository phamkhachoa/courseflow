import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const RolesListPage = lazy(() => import("./pages").then(({ RolesListPage }) => ({ default: RolesListPage })));
const RoleCreatePage = lazy(() => import("./pages").then(({ RoleCreatePage }) => ({ default: RoleCreatePage })));
const RoleDetailPage = lazy(() => import("./pages").then(({ RoleDetailPage }) => ({ default: RoleDetailPage })));
const UserAssignmentsPage = lazy(() => import("./pages").then(({ UserAssignmentsPage }) => ({ default: UserAssignmentsPage })));

export const rolesRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(RolesListPage) },
  { path: "new", element: lazyRouteElement(RoleCreatePage) },
  { path: "user-assignments", element: lazyRouteElement(UserAssignmentsPage) },
  { path: ":roleId", element: lazyRouteElement(RoleDetailPage) }
];
