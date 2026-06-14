import { LoyaltyWalletView } from "@/features/loyalty/LoyaltyWalletView";
import { PageShell } from "@/shared/ui";

export default function LoyaltyPage() {
  return (
    <PageShell
      eyebrow="Điểm thưởng"
      title="Ví loyalty"
      description="Theo dõi điểm, expiry buckets, reward khả dụng và lịch sử đổi thưởng."
    >
      <LoyaltyWalletView />
    </PageShell>
  );
}
