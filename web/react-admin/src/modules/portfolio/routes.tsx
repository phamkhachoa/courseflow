import type { RouteObject } from "react-router-dom";
import { PortfolioPage } from "./pages";

export const portfolioRoutes: RouteObject[] = [{ index: true, element: <PortfolioPage /> }];
