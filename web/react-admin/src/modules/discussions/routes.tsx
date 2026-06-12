import type { RouteObject } from "react-router-dom";
import { DiscussionListPage, DiscussionThreadPage } from "./pages";

export const discussionsRoutes: RouteObject[] = [
  { index: true, element: <DiscussionListPage /> },
  { path: ":threadId", element: <DiscussionThreadPage /> }
];
