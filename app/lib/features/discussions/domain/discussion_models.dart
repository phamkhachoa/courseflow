/// Discussion thread, from `GET /v1/discussions/threads`.
class DiscussionThread {
  const DiscussionThread({
    required this.id,
    required this.title,
    required this.authorName,
    required this.commentCount,
    required this.createdAt,
  });

  final String id;
  final String title;
  final String authorName;
  final int commentCount;
  final DateTime? createdAt;

  factory DiscussionThread.fromJson(Map<String, dynamic> json) =>
      DiscussionThread(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        authorName: json['authorName'] as String? ?? 'Anonymous',
        commentCount: (json['commentCount'] as num?)?.toInt() ?? 0,
        createdAt: json['createdAt'] is String
            ? DateTime.tryParse(json['createdAt'] as String)
            : null,
      );
}

class DiscussionComment {
  const DiscussionComment({
    required this.id,
    required this.authorName,
    required this.body,
    required this.createdAt,
  });

  final String id;
  final String authorName;
  final String body;
  final DateTime? createdAt;

  factory DiscussionComment.fromJson(Map<String, dynamic> json) =>
      DiscussionComment(
        id: json['id'] as String? ?? '',
        authorName: json['authorName'] as String? ?? 'Anonymous',
        body: json['body'] as String? ?? '',
        createdAt: json['createdAt'] is String
            ? DateTime.tryParse(json['createdAt'] as String)
            : null,
      );
}
