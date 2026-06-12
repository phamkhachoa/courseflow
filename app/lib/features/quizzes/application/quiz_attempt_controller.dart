import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/quiz_repository.dart';
import '../domain/quiz_models.dart';

/// Drives a single quiz-taking session: load quiz, collect answers, submit.
class QuizAttemptState {
  const QuizAttemptState({
    this.quiz,
    this.attemptId,
    this.answers = const {},
    this.result,
    this.submitting = false,
    this.error,
  });

  final Quiz? quiz;
  final String? attemptId;

  /// questionId -> selected optionId.
  final Map<String, String> answers;
  final QuizResult? result;
  final bool submitting;
  final String? error;

  bool get isReady => quiz != null && attemptId != null;
  bool get isComplete => result != null;
  bool get allAnswered =>
      quiz != null && answers.length == quiz!.questions.length;

  QuizAttemptState copyWith({
    Quiz? quiz,
    String? attemptId,
    Map<String, String>? answers,
    QuizResult? result,
    bool? submitting,
    String? error,
    bool clearError = false,
  }) {
    return QuizAttemptState(
      quiz: quiz ?? this.quiz,
      attemptId: attemptId ?? this.attemptId,
      answers: answers ?? this.answers,
      result: result ?? this.result,
      submitting: submitting ?? this.submitting,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class QuizAttemptController
    extends AutoDisposeFamilyAsyncNotifier<QuizAttemptState, String> {
  @override
  Future<QuizAttemptState> build(String quizId) async {
    final repo = ref.watch(quizRepositoryProvider);
    final quiz = await repo.getQuiz(quizId);
    final attempt = await repo.startAttempt(quizId);
    return QuizAttemptState(quiz: quiz, attemptId: attempt.id);
  }

  void selectAnswer(String questionId, String optionId) {
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData(
      current.copyWith(
        answers: {...current.answers, questionId: optionId},
        clearError: true,
      ),
    );
  }

  Future<void> submit() async {
    final current = state.valueOrNull;
    if (current == null || current.attemptId == null || current.quiz == null) {
      return;
    }
    state = AsyncData(current.copyWith(submitting: true, clearError: true));
    try {
      final quiz = current.quiz!;
      // The backend grades single-choice answers against the option label, so
      // translate the selected optionId into its label before submitting.
      final answers = <String, String>{};
      for (final q in quiz.questions) {
        final selectedId = current.answers[q.id];
        if (selectedId == null) continue;
        final option = q.options.firstWhere(
          (o) => o.id == selectedId,
          orElse: () => QuizOption(id: selectedId, label: selectedId),
        );
        answers[q.id] = option.label;
      }
      final attempt = await ref
          .read(quizRepositoryProvider)
          .submitAttempt(
            attemptId: current.attemptId!,
            answers: answers,
          );
      final result = QuizResult(
        score: attempt.score ?? 0,
        maxScore: quiz.totalPoints,
      );
      state = AsyncData(current.copyWith(result: result, submitting: false));
    } catch (e) {
      state = AsyncData(
        current.copyWith(submitting: false, error: e.toString()),
      );
    }
  }
}

final quizAttemptControllerProvider = AsyncNotifierProvider.autoDispose
    .family<QuizAttemptController, QuizAttemptState, String>(
      QuizAttemptController.new,
    );
