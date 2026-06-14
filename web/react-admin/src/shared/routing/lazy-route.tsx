import { Suspense, type ComponentType } from "react";
import { Spinner } from "@/shared/ui";

function RouteFallback() {
  return (
    <div className="flex min-h-80 items-center justify-center p-6">
      <Spinner />
    </div>
  );
}

export function lazyRouteElement(Page: ComponentType) {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Page />
    </Suspense>
  );
}
