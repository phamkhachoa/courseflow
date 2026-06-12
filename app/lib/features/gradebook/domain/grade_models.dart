/// A single gradebook line for the learner. Mirrors gradebook-service
/// `GradeEntryDto`. There is no per-entry `feedback` field on the current
/// contract; the displayed score is the late-penalty-`adjustedScore` (falling
/// back to `rawScore`).
class GradeEntry {
  const GradeEntry({
    required this.gradeItemId,
    required this.title,
    required this.categoryName,
    required this.score,
    required this.maxScore,
    required this.letter,
    required this.status,
    required this.isLate,
  });

  final String gradeItemId;
  final String title;
  final String categoryName;
  final double? score;
  final double maxScore;
  final String letter;
  final String status;
  final bool isLate;

  bool get graded => status == 'GRADED' || score != null;
  double get percent =>
      (score == null || maxScore == 0) ? 0 : (score! / maxScore) * 100;

  factory GradeEntry.fromJson(Map<String, dynamic> json) {
    // Prefer the adjusted (post-late-penalty) score; fall back to the raw score.
    final adjusted = (json['adjustedScore'] as num?)?.toDouble();
    final raw = (json['rawScore'] as num?)?.toDouble();
    return GradeEntry(
      gradeItemId:
          json['gradeItemId'] as String? ?? json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      categoryName: json['categoryName'] as String? ?? '',
      score: adjusted ?? raw,
      maxScore: (json['maxScore'] as num?)?.toDouble() ?? 0,
      letter: json['letter'] as String? ?? '',
      status: json['status'] as String? ?? '',
      isLate: json['isLate'] as bool? ?? false,
    );
  }
}

/// Aggregated course view. Mirrors `StudentGradebookDto`: the server computes
/// `finalScore`/`finalLetter` from category weights (P0-4), so the app shows
/// that figure when present rather than recomputing from entries.
class CourseGrades {
  const CourseGrades({
    required this.entries,
    this.finalScore,
    this.finalLetter,
    this.gradingSchemeName,
  });

  final List<GradeEntry> entries;
  final double? finalScore;
  final String? finalLetter;
  final String? gradingSchemeName;

  /// Server-computed weighted final score when available, otherwise a simple
  /// points-earned / points-possible fallback across graded entries.
  double get overallPercent {
    if (finalScore != null) return finalScore!;
    final graded = entries.where((e) => e.graded).toList();
    if (graded.isEmpty) return 0;
    final earned = graded.fold<double>(0, (sum, e) => sum + e.score!);
    final possible = graded.fold<double>(0, (sum, e) => sum + e.maxScore);
    return possible == 0 ? 0 : (earned / possible) * 100;
  }

  factory CourseGrades.fromJson(Object? data) {
    final map = data is Map<String, dynamic> ? data : const <String, dynamic>{};
    final list = data is Map<String, dynamic> ? data['entries'] : data;
    final rows = (list as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(GradeEntry.fromJson)
        .toList(growable: false);
    return CourseGrades(
      entries: rows,
      finalScore: (map['finalScore'] as num?)?.toDouble(),
      finalLetter: map['finalLetter'] as String?,
      gradingSchemeName: map['gradingSchemeName'] as String?,
    );
  }
}
