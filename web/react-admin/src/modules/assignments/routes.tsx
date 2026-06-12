import type { RouteObject } from "react-router-dom";
import { AssignmentCreatePage, AssignmentDetailPage, AssignmentListPage, RubricPage, SubmissionsPage } from "./pages";

export const assignmentsRoutes: RouteObject[] = [
  { index: true, element: <AssignmentListPage /> },
  { path: "new", element: <AssignmentCreatePage /> },
  { path: ":id", element: <AssignmentDetailPage /> },
  { path: ":id/submissions", element: <SubmissionsPage /> },
  { path: ":id/rubric", element: <RubricPage /> }
];
