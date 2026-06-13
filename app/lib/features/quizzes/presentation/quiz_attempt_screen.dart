import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../application/quiz_attempt_controller.dart';
import '../domain/quiz_models.dart';

/// Learner quiz-taking flow: starts an attempt on open, collects answers,
/// submits, then shows the score.
class QuizAttemptScreen extends ConsumerWidget {
  const QuizAttemptScreen({super.key, required this.quizId});

  final String quizId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = quizAttemptControllerProvider(quizId);
    final state = ref.watch(provider);
    return Scaffold(
      appBar: AppBar(title: const Text('Quiz')),
      body: AsyncValueView<QuizAttemptState>(
        value: state,
        onRetry: () => ref.invalidate(provider),
        data: (attempt) {
          if (attempt.isComplete) {
            return _ResultView(result: attempt.result!);
          }
          return _AttemptForm(quizId: quizId, attempt: attempt);
        },
      ),
    );
  }
}

class _AttemptForm extends ConsumerWidget {
  const _AttemptForm({required this.quizId, required this.attempt});

  final String quizId;
  final QuizAttemptState attempt;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final quiz = attempt.quiz!;
    final controller =
        ref.read(quizAttemptControllerProvider(quizId).notifier);
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            children: [
              Text(quiz.title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              ...quiz.questions.asMap().entries.map((entry) {
                final i = entry.key;
                final q = entry.value;
                return _QuestionCard(
                  index: i + 1,
                  question: q,
                  selectedOptionId: attempt.answers[q.id],
                  onSelect: (optionId) =>
                      controller.selectAnswer(q.id, optionId),
                );
              }),
              if (attempt.error != null) ...[
                const SizedBox(height: AppTheme.gap),
                Text(attempt.error!,
                    style: TextStyle(
                        color: Theme.of(context).colorScheme.error)),
              ],
            ],
          ),
        ),
        SafeArea(
          minimum: const EdgeInsets.all(AppTheme.pagePadding),
          child: FilledButton(
            onPressed: attempt.allAnswered && !attempt.submitting
                ? controller.submit
                : null,
            child: attempt.submitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : Text(attempt.allAnswered
                    ? 'Submit'
                    : 'Answer all questions (${attempt.answers.length}/${quiz.questions.length})'),
          ),
        ),
      ],
    );
  }
}

class _QuestionCard extends StatelessWidget {
  const _QuestionCard({
    required this.index,
    required this.question,
    required this.selectedOptionId,
    required this.onSelect,
  });

  final int index;
  final QuizQuestion question;
  final String? selectedOptionId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppTheme.gap),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$index. ${question.stem}',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            RadioGroup<String>(
              groupValue: selectedOptionId,
              onChanged: (value) {
                if (value != null) onSelect(value);
              },
              child: Column(
                children: question.options
                    .map(
                      (o) => RadioListTile<String>(
                        contentPadding: EdgeInsets.zero,
                        title: Text(o.label),
                        value: o.id,
                      ),
                    )
                    .toList(growable: false),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultView extends StatelessWidget {
  const _ResultView({required this.result});

  final QuizResult result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final passed = result.percent >= 50;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.pagePadding),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              passed ? Icons.celebration_outlined : Icons.replay_outlined,
              size: 56,
              color: passed ? theme.colorScheme.primary : theme.colorScheme.error,
            ),
            const SizedBox(height: AppTheme.gap),
            Text('${result.score.toStringAsFixed(0)} / ${result.maxScore.toStringAsFixed(0)}',
                style: theme.textTheme.headlineMedium),
            const SizedBox(height: 4),
            Text('${result.percent.toStringAsFixed(0)}%',
                style: theme.textTheme.titleMedium
                    ?.copyWith(color: theme.colorScheme.outline)),
          ],
        ),
      ),
    );
  }
}
