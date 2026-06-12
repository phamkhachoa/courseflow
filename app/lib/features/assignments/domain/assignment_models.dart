/// Assignment from `/v1/assignments?courseId=`. Mirrors assignment-service
/// `AssignmentDto`. The list response describes the assignment only; it carries
/// no per-student submission flag, so submission state is not modelled here.
class Assignment {
  const Assignment({
    required this.id,
    required this.courseId,
    required this.title,
    required this.instructions,
    required this.dueAt,
    required this.maxScore,
    required this.status,
  });

  final String id;
  final String courseId;
  final String title;
  final String instructions;
  final DateTime? dueAt;
  final double maxScore;
  final String status;

  bool get isOverdue => dueAt != null && dueAt!.isBefore(DateTime.now());

  factory Assignment.fromJson(Map<String, dynamic> json) => Assignment(
    id: json['id'] as String? ?? '',
    courseId: json['courseId'] as String? ?? '',
    title: json['title'] as String? ?? '',
    instructions: json['instructions'] as String? ?? '',
    dueAt: _parseDate(json['dueAt']),
    maxScore: (json['maxScore'] as num?)?.toDouble() ?? 0,
    status: json['status'] as String? ?? '',
  );
}

DateTime? _parseDate(Object? value) =>
    value is String ? DateTime.tryParse(value) : null;
