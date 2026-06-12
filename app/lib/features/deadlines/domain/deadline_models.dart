/// An upcoming deadline reminder, from
/// `GET /v1/deadlines/reminders/due`.
class DeadlineReminder {
  const DeadlineReminder({
    required this.id,
    required this.title,
    required this.courseTitle,
    required this.dueAt,
  });

  final String id;
  final String title;
  final String courseTitle;
  final DateTime? dueAt;

  factory DeadlineReminder.fromJson(Map<String, dynamic> json) =>
      DeadlineReminder(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        courseTitle: json['courseTitle'] as String? ?? '',
        dueAt: json['dueAt'] is String
            ? DateTime.tryParse(json['dueAt'] as String)
            : null,
      );
}
