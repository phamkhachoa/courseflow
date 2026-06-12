import { LearningPathsView } from "@/features/learning-paths/LearningPathsView";
import { PageShell } from "@/shared/ui";

export default function LearningPathsPage() {
  return (
    <PageShell
      eyebrow="Lộ trình"
      title="Learning paths"
      description="Tạo lộ trình học theo mục tiêu cá nhân, dùng recommendation realtime từ search-service."
    >
      <LearningPathsView />
    </PageShell>
  );
}
