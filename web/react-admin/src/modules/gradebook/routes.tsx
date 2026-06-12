import type { RouteObject } from "react-router-dom";
import { GradebookPage } from "./pages";

export const gradebookRoutes: RouteObject[] = [{ index: true, element: <GradebookPage /> }];
