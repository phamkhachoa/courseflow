import type { RouteObject } from "react-router-dom";
import { AttemptDetailPage, EffectiveScorePage, QuizzesPage } from "./pages";

export const quizzesRoutes: RouteObject[] = [
  { index: true, element: <QuizzesPage /> },
  { path: ":attemptId/detail", element: <AttemptDetailPage /> },
  { path: "score", element: <EffectiveScorePage /> }
];
