/// Sanitized student view of a quiz, from `GET /v1/quizzes/{quizId}`.
///
/// Mirrors the student quiz API DTO: students never receive the answer
/// key (no `correctAnswer`, no option `correct` flag, no `feedback`). The full
/// `QuizDto` is only returned to staff or to a student with a GRADED attempt
/// when `showCorrectAnswers` is set — the learner app always treats it as the
/// sanitized shape.
class Quiz {
  const Quiz({
    required this.id,
    required this.title,
    required this.questions,
  });

  final String id;
  final String title;
  final List<QuizQuestion> questions;

  /// Total achievable points, summed from each question. Used to render a
  /// score out of a maximum since the submit response only carries the score.
  double get totalPoints =>
      questions.fold<double>(0, (sum, q) => sum + q.points);

  factory Quiz.fromJson(Map<String, dynamic> json) => Quiz(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    questions: (json['questions'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(QuizQuestion.fromJson)
        .toList(growable: false),
  );
}

/// Mirrors `StudentQuizQuestionDto` (id, type, stem, points, position, options).
class QuizQuestion {
  const QuizQuestion({
    required this.id,
    required this.type,
    required this.stem,
    required this.points,
    required this.options,
  });

  final String id;
  final String type;
  final String stem;
  final double points;
  final List<QuizOption> options;

  factory QuizQuestion.fromJson(Map<String, dynamic> json) => QuizQuestion(
    id: json['id'] as String? ?? '',
    type: json['type'] as String? ?? '',
    stem: json['stem'] as String? ?? '',
    points: (json['points'] as num?)?.toDouble() ?? 0,
    options: (json['options'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(QuizOption.fromJson)
        .toList(growable: false),
  );
}

/// Mirrors `StudentQuestionOptionDto` (id, label, content) — no `correct` flag.
class QuizOption {
  const QuizOption({required this.id, required this.label, this.content});

  final String id;
  final String label;
  final String? content;

  factory QuizOption.fromJson(Map<String, dynamic> json) => QuizOption(
    id: json['id'] as String? ?? '',
    label: json['label'] as String? ?? '',
    content: json['content'] as String?,
  );
}

/// Mirrors `QuizAttemptDto`, returned when starting and submitting an attempt.
/// `studentId` is set by the gateway identity, never sent by the client.
class QuizAttempt {
  const QuizAttempt({
    required this.id,
    this.status,
    this.score,
  });

  final String id;
  final String? status;
  final double? score;

  factory QuizAttempt.fromJson(Map<String, dynamic> json) => QuizAttempt(
    id: json['id'] as String? ?? '',
    status: json['status'] as String?,
    score: (json['score'] as num?)?.toDouble(),
  );
}

/// Display model for a graded attempt. The submit endpoint returns a
/// `QuizAttemptDto` carrying only `score`, so [maxScore] is derived from the
/// quiz's total question points.
class QuizResult {
  const QuizResult({required this.score, required this.maxScore});

  final double score;
  final double maxScore;

  double get percent => maxScore == 0 ? 0 : (score / maxScore) * 100;
}
