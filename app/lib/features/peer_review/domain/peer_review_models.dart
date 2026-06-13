/// A review the learner is assigned to complete, from
/// `GET /v1/peer-reviews/review-assignments/mine`.
class PeerReviewAssignment {
  const PeerReviewAssignment({
    required this.id,
    required this.assignmentTitle,
    required this.submissionExcerpt,
    required this.dueAt,
    required this.submitted,
  });

  final String id;
  final String assignmentTitle;
  final String submissionExcerpt;
  final DateTime? dueAt;
  final bool submitted;

  factory PeerReviewAssignment.fromJson(Map<String, dynamic> json) =>
      PeerReviewAssignment(
        id: json['id'] as String? ?? '',
        assignmentTitle: json['assignmentTitle'] as String? ??
            _label('Assignment', json['assignmentId'] as String?),
        submissionExcerpt: json['submissionExcerpt'] as String? ??
            _label('Submission', json['submissionId'] as String?),
        dueAt: json['dueAt'] is String
            ? DateTime.tryParse(json['dueAt'] as String)
            : null,
        submitted: json['submitted'] as bool? ??
            ((json['status'] as String? ?? '').toUpperCase() == 'REVIEWED'),
      );

  static String _label(String prefix, String? id) =>
      id == null || id.isEmpty ? prefix : '$prefix $id';
}
