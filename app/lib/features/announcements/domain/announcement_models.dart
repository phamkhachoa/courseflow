/// Course/class announcement, read-only for learners.
/// From `GET /v1/announcements`.
class Announcement {
  const Announcement({
    required this.id,
    required this.title,
    required this.body,
    required this.courseTitle,
    required this.publishedAt,
  });

  final String id;
  final String title;
  final String body;
  final String courseTitle;
  final DateTime? publishedAt;

  factory Announcement.fromJson(Map<String, dynamic> json) => Announcement(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    body: json['body'] as String? ?? json['content'] as String? ?? '',
    courseTitle: json['courseTitle'] as String? ?? '',
    publishedAt: json['publishedAt'] is String
        ? DateTime.tryParse(json['publishedAt'] as String)
        : null,
  );
}
