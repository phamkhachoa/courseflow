import type { RouteObject } from "react-router-dom";
import { RolesListPage, RoleCreatePage, RoleDetailPage, UserAssignmentsPage } from "./pages";

export const rolesRoutes: RouteObject[] = [
  { index: true, element: <RolesListPage /> },
  { path: "new", element: <RoleCreatePage /> },
  { path: "user-assignments", element: <UserAssignmentsPage /> },
  { path: ":roleId", element: <RoleDetailPage /> }
];
