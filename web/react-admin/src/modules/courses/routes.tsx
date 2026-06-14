import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const CourseListPage = lazy(() => import("./pages/CourseListPage").then(({ CourseListPage }) => ({ default: CourseListPage })));
const CourseDetailPage = lazy(() => import("./pages/CourseDetailPage").then(({ CourseDetailPage }) => ({ default: CourseDetailPage })));
const CourseCreatePage = lazy(() => import("./pages/CourseCreatePage").then(({ CourseCreatePage }) => ({ default: CourseCreatePage })));
const CourseAuthoringPage = lazy(() => import("./pages/CourseAuthoringPage").then(({ CourseAuthoringPage }) => ({ default: CourseAuthoringPage })));
const CourseAuthoringCreatePage = lazy(() =>
  import("./pages/CourseAuthoringCreatePage").then(({ CourseAuthoringCreatePage }) => ({ default: CourseAuthoringCreatePage }))
);
const CourseDraftPage = lazy(() => import("./pages/CourseDraftPage").then(({ CourseDraftPage }) => ({ default: CourseDraftPage })));

export const coursesRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(CourseListPage) },
  { path: "new", element: lazyRouteElement(CourseCreatePage) },
  { path: ":courseId", element: lazyRouteElement(CourseDetailPage) }
];

export const authoringRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(CourseAuthoringPage) },
  { path: "new", element: lazyRouteElement(CourseAuthoringCreatePage) },
  { path: ":courseId/draft", element: lazyRouteElement(CourseDraftPage) }
];
