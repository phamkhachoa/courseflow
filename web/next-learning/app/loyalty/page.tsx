import { LoyaltyWalletView } from "@/features/loyalty/LoyaltyWalletView";
import { PageShell } from "@/shared/ui";

export default function LoyaltyPage() {
  return (
    <PageShell
      eyebrow="Ưu đãi học tập"
      title="Incentive Hub"
      description="Theo dõi coupon, điểm, reward, benefit pending, lý do chưa đủ điều kiện và support case."
    >
      <LoyaltyWalletView />
    </PageShell>
  );
}
