import type { RouteObject } from "react-router-dom";
import { OrganizationPage } from "./pages";

export const organizationRoutes: RouteObject[] = [{ index: true, element: <OrganizationPage /> }];
