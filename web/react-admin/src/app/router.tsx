import { createBrowserRouter, Navigate } from "react-router-dom";
import { AdminLayout } from "@/shared/layout/AdminLayout";
import { RequireAuth } from "@/shared/auth/RequireAuth";
import { LoginPage } from "@/modules/auth/LoginPage";
import { LoginCallbackPage } from "@/modules/auth/LoginCallbackPage";
import { DashboardPage } from "@/modules/dashboard/DashboardPage";

import { coursesRoutes, authoringRoutes } from "@/modules/courses/routes";
import { courseModulesRoutes } from "@/modules/course-modules/routes";
import { identityRoutes } from "@/modules/identity/routes";
import { organizationRoutes } from "@/modules/organization/routes";
import { enrollmentsRoutes } from "@/modules/enrollments/routes";
import { assignmentsRoutes } from "@/modules/assignments/routes";
import { quizzesRoutes } from "@/modules/quizzes/routes";
import { gradebookRoutes } from "@/modules/gradebook/routes";
import { peerReviewRoutes } from "@/modules/peer-review/routes";
import { certificatesRoutes } from "@/modules/certificates/routes";
import { announcementsRoutes } from "@/modules/announcements/routes";
import { discussionsRoutes } from "@/modules/discussions/routes";
import { analyticsRoutes } from "@/modules/analytics/routes";
import { liveSessionsRoutes } from "@/modules/live-sessions/routes";
import { deadlinesRoutes } from "@/modules/deadlines/routes";
import { notificationsRoutes } from "@/modules/notifications/routes";
import { mediaRoutes } from "@/modules/media/routes";
import { portfolioRoutes } from "@/modules/portfolio/routes";
import { searchRoutes } from "@/modules/search/routes";
import { rolesRoutes } from "@/modules/roles/routes";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/login/callback", element: <LoginCallbackPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AdminLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "courses", children: coursesRoutes },
      { path: "authoring", children: authoringRoutes },
      { path: "course-modules", children: courseModulesRoutes },
      { path: "users", children: identityRoutes },
      { path: "organization", children: organizationRoutes },
      { path: "enrollments", children: enrollmentsRoutes },
      { path: "assignments", children: assignmentsRoutes },
      { path: "quizzes", children: quizzesRoutes },
      { path: "gradebook", children: gradebookRoutes },
      { path: "peer-review", children: peerReviewRoutes },
      { path: "certificates", children: certificatesRoutes },
      { path: "announcements", children: announcementsRoutes },
      { path: "discussions", children: discussionsRoutes },
      { path: "analytics", children: analyticsRoutes },
      { path: "live-sessions", children: liveSessionsRoutes },
      { path: "deadlines", children: deadlinesRoutes },
      { path: "notifications", children: notificationsRoutes },
      { path: "media", children: mediaRoutes },
      { path: "portfolio", children: portfolioRoutes },
      { path: "search", children: searchRoutes },
      { path: "roles", children: rolesRoutes }
    ]
  },
  { path: "*", element: <Navigate to="/" replace /> }
]);
