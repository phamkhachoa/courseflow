class CourseReview {
  const CourseReview({
    required this.id,
    required this.courseId,
    required this.userId,
    required this.rating,
    required this.status,
    required this.helpfulCount,
    required this.createdAt,
    this.title,
    this.body,
  });

  final String id;
  final String courseId;
  final String userId;
  final int rating;
  final String status;
  final int helpfulCount;
  final String createdAt;
  final String? title;
  final String? body;

  factory CourseReview.fromJson(Map<String, dynamic> json) => CourseReview(
        id: json['id'] as String? ?? '',
        courseId: json['courseId'] as String? ?? '',
        userId: json['userId'] as String? ?? '',
        rating: json['rating'] as int? ?? 0,
        status: json['status'] as String? ?? '',
        helpfulCount: json['helpfulCount'] as int? ?? 0,
        createdAt: json['createdAt'] as String? ?? '',
        title: json['title'] as String?,
        body: json['body'] as String?,
      );
}

class RatingSummary {
  const RatingSummary({
    required this.courseId,
    required this.reviewCount,
    required this.averageRating,
  });

  final String courseId;
  final int reviewCount;
  final double averageRating;

  factory RatingSummary.fromJson(Map<String, dynamic> json) => RatingSummary(
        courseId: json['courseId'] as String? ?? '',
        reviewCount: json['reviewCount'] as int? ?? 0,
        averageRating: (json['averageRating'] as num?)?.toDouble() ?? 0,
      );
}
