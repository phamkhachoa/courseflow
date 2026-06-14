import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const UserCreatePage = lazy(() => import("./pages").then(({ UserCreatePage }) => ({ default: UserCreatePage })));
const UserDetailPage = lazy(() => import("./pages").then(({ UserDetailPage }) => ({ default: UserDetailPage })));
const UserListPage = lazy(() => import("./pages").then(({ UserListPage }) => ({ default: UserListPage })));

export const identityRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(UserListPage) },
  { path: "new", element: lazyRouteElement(UserCreatePage) },
  { path: ":id", element: lazyRouteElement(UserDetailPage) }
];
