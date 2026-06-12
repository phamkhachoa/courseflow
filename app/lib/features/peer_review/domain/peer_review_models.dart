/// A review the learner is assigned to complete, from
/// `GET /v1/peer-reviews/...` (assigned review queue).
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
        assignmentTitle: json['assignmentTitle'] as String? ?? '',
        submissionExcerpt: json['submissionExcerpt'] as String? ?? '',
        dueAt: json['dueAt'] is String
            ? DateTime.tryParse(json['dueAt'] as String)
            : null,
        submitted: json['submitted'] as bool? ?? false,
      );
}
