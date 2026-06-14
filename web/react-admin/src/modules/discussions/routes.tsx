import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const DiscussionListPage = lazy(() => import("./pages").then(({ DiscussionListPage }) => ({ default: DiscussionListPage })));
const DiscussionThreadPage = lazy(() => import("./pages").then(({ DiscussionThreadPage }) => ({ default: DiscussionThreadPage })));

export const discussionsRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(DiscussionListPage) },
  { path: ":threadId", element: lazyRouteElement(DiscussionThreadPage) }
];
