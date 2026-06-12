import { PeerReviewView } from "@/features/peer-review/PeerReviewView";
import { PageShell } from "@/shared/ui";

export default async function PeerReviewPage({
  params
}: {
  params: Promise<{ assignmentId: string }>;
}) {
  const { assignmentId } = await params;
  return (
    <PageShell eyebrow="Chấm chéo" title="Đánh giá đồng cấp">
      <PeerReviewView assignmentId={assignmentId} />
    </PageShell>
  );
}
