import type { RouteObject } from "react-router-dom";
import { CourseListPage } from "./pages/CourseListPage";
import { CourseDetailPage } from "./pages/CourseDetailPage";
import { CourseCreatePage } from "./pages/CourseCreatePage";
import { CourseAuthoringPage } from "./pages/CourseAuthoringPage";
import { CourseAuthoringCreatePage } from "./pages/CourseAuthoringCreatePage";
import { CourseDraftPage } from "./pages/CourseDraftPage";

export const coursesRoutes: RouteObject[] = [
  { index: true, element: <CourseListPage /> },
  { path: "new", element: <CourseCreatePage /> },
  { path: ":courseId", element: <CourseDetailPage /> }
];

export const authoringRoutes: RouteObject[] = [
  { index: true, element: <CourseAuthoringPage /> },
  { path: "new", element: <CourseAuthoringCreatePage /> },
  { path: ":courseId/draft", element: <CourseDraftPage /> }
];
