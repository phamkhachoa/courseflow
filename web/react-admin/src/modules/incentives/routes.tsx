import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { lazyRouteElement } from "@/shared/routing/lazy-route";

const IncentiveDashboardPage = lazy(() => import("./pages").then(({ IncentiveDashboardPage }) => ({ default: IncentiveDashboardPage })));
const ApplicationRegistryPage = lazy(() => import("./pages").then(({ ApplicationRegistryPage }) => ({ default: ApplicationRegistryPage })));
const AuditExplorerPage = lazy(() => import("./pages").then(({ AuditExplorerPage }) => ({ default: AuditExplorerPage })));
const CampaignCreatePage = lazy(() => import("./pages").then(({ CampaignCreatePage }) => ({ default: CampaignCreatePage })));
const CampaignListPage = lazy(() => import("./pages").then(({ CampaignListPage }) => ({ default: CampaignListPage })));
const CampaignWorkspacePage = lazy(() => import("./pages").then(({ CampaignWorkspacePage }) => ({ default: CampaignWorkspacePage })));
const CouponCatalogPage = lazy(() => import("./pages").then(({ CouponCatalogPage }) => ({ default: CouponCatalogPage })));
const RedemptionDetailPage = lazy(() => import("./pages").then(({ RedemptionDetailPage }) => ({ default: RedemptionDetailPage })));
const RedemptionSupportPage = lazy(() => import("./pages").then(({ RedemptionSupportPage }) => ({ default: RedemptionSupportPage })));
const RetentionConsolePage = lazy(() => import("./pages").then(({ RetentionConsolePage }) => ({ default: RetentionConsolePage })));
const ReviewQueuePage = lazy(() => import("./pages").then(({ ReviewQueuePage }) => ({ default: ReviewQueuePage })));
const LoyaltyControlPlanePage = lazy(() =>
  import("./loyalty-page").then(({ LoyaltyControlPlanePage }) => ({ default: LoyaltyControlPlanePage }))
);
const CouponImportConsolePage = lazy(() =>
  import("./operations-pages").then(({ CouponImportConsolePage }) => ({ default: CouponImportConsolePage }))
);
const ReconciliationPage = lazy(() => import("./operations-pages").then(({ ReconciliationPage }) => ({ default: ReconciliationPage })));
const IncentiveOpsConsolePage = lazy(() =>
  import("./ops-console-page").then(({ IncentiveOpsConsolePage }) => ({ default: IncentiveOpsConsolePage }))
);

export const incentivesRoutes: RouteObject[] = [
  { index: true, element: lazyRouteElement(IncentiveDashboardPage) },
  { path: "applications", element: lazyRouteElement(ApplicationRegistryPage) },
  { path: "campaigns", element: lazyRouteElement(CampaignListPage) },
  { path: "campaigns/new", element: lazyRouteElement(CampaignCreatePage) },
  { path: "campaigns/:campaignId", element: lazyRouteElement(CampaignWorkspacePage) },
  { path: "campaigns/:campaignId/versions/:versionNumber", element: lazyRouteElement(CampaignWorkspacePage) },
  { path: "coupons", element: lazyRouteElement(CouponCatalogPage) },
  { path: "review", element: lazyRouteElement(ReviewQueuePage) },
  { path: "coupon-imports", element: lazyRouteElement(CouponImportConsolePage) },
  { path: "redemptions", element: lazyRouteElement(RedemptionSupportPage) },
  { path: "redemptions/:redemptionId", element: lazyRouteElement(RedemptionDetailPage) },
  { path: "ops-console", element: lazyRouteElement(IncentiveOpsConsolePage) },
  { path: "reconciliation", element: lazyRouteElement(ReconciliationPage) },
  { path: "loyalty", element: lazyRouteElement(LoyaltyControlPlanePage) },
  { path: "retention", element: lazyRouteElement(RetentionConsolePage) },
  { path: "audit", element: lazyRouteElement(AuditExplorerPage) }
];
