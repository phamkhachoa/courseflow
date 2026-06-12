/// Enrollment status for the current learner in a course.
enum EnrollmentState { notEnrolled, enrolled, waitlisted, full }

class Enrollment {
  const Enrollment({required this.state, this.position});

  final EnrollmentState state;

  /// Waitlist position when [state] is [EnrollmentState.waitlisted].
  final int? position;

  const Enrollment.notEnrolled() : this(state: EnrollmentState.notEnrolled);

  /// Parses either an `EnrollmentDto` (status ACTIVE/DROPPED/COMPLETED) or a
  /// `WaitlistEntryDto` (status WAITING, plus a `position`).
  factory Enrollment.fromJson(Map<String, dynamic> json) {
    final raw = (json['status'] as String? ?? 'NOT_ENROLLED').toUpperCase();
    final state = switch (raw) {
      'ACTIVE' || 'ENROLLED' || 'COMPLETED' => EnrollmentState.enrolled,
      'WAITING' || 'WAITLISTED' || 'PROMOTED' => EnrollmentState.waitlisted,
      'FULL' => EnrollmentState.full,
      _ => EnrollmentState.notEnrolled,
    };
    return Enrollment(
      state: state,
      position: (json['position'] as num?)?.toInt(),
    );
  }
}
