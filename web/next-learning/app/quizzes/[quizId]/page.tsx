import { QuizRunner } from "@/features/quiz-attempts/QuizRunner";
import { PageShell } from "@/shared/ui";

export default async function QuizPage({ params }: { params: Promise<{ quizId: string }> }) {
  const { quizId } = await params;
  return (
    <PageShell eyebrow="Trắc nghiệm" title="Làm bài">
      <QuizRunner quizId={quizId} />
    </PageShell>
  );
}
