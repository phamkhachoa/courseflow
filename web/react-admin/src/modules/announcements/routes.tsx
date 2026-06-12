import type { RouteObject } from "react-router-dom";
import { AnnouncementCreatePage, AnnouncementDetailPage, AnnouncementListPage } from "./pages";

export const announcementsRoutes: RouteObject[] = [
  { index: true, element: <AnnouncementListPage /> },
  { path: "new", element: <AnnouncementCreatePage /> },
  { path: ":id", element: <AnnouncementDetailPage /> }
];
