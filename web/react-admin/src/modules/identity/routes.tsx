import type { RouteObject } from "react-router-dom";
import { UserCreatePage, UserDetailPage, UserListPage } from "./pages";

export const identityRoutes: RouteObject[] = [
  { index: true, element: <UserListPage /> },
  { path: "new", element: <UserCreatePage /> },
  { path: ":id", element: <UserDetailPage /> }
];
