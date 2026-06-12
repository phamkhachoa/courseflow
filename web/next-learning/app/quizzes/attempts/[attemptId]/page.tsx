import { AttemptReview } from "@/features/quiz-attempts/AttemptReview";
import { PageShell } from "@/shared/ui";

export default async function AttemptReviewPage({
  params
}: {
  params: Promise<{ attemptId: string }>;
}) {
  const { attemptId } = await params;
  return (
    <PageShell eyebrow="Trắc nghiệm" title="Xem lại bài làm">
      <AttemptReview attemptId={attemptId} />
    </PageShell>
  );
}
