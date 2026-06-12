/// Catalog summary card. Matches course-service `/v1/courses` rows and the
/// web `FeaturedCourse` shape.
class CourseSummary {
  const CourseSummary({
    required this.id,
    required this.code,
    required this.title,
    required this.slug,
    required this.summary,
    required this.level,
    required this.status,
  });

  final String id;
  final String code;
  final String title;
  final String slug;
  final String summary;
  final String level;
  final String status;

  factory CourseSummary.fromJson(Map<String, dynamic> json) => CourseSummary(
    id: json['id'] as String? ?? '',
    code: json['code'] as String? ?? '',
    title: json['title'] as String? ?? '',
    slug: json['slug'] as String? ?? '',
    summary: json['summary'] as String? ?? '',
    level: json['level'] as String? ?? 'COURSE',
    status: json['status'] as String? ?? 'PUBLISHED',
  );
}

/// Full course page from `/v1/courses/{slug}`. Modules are optional; the
/// detail endpoint may embed them or expose them separately.
class CourseDetail {
  const CourseDetail({
    required this.summary,
    required this.description,
    required this.modules,
  });

  final CourseSummary summary;
  final String description;
  final List<CourseModule> modules;

  factory CourseDetail.fromJson(Map<String, dynamic> json) => CourseDetail(
    summary: CourseSummary.fromJson(json),
    description: json['description'] as String? ?? json['summary'] as String? ?? '',
    modules: (json['modules'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(CourseModule.fromJson)
        .toList(growable: false),
  );
}

class CourseModule {
  const CourseModule({
    required this.id,
    required this.title,
    required this.position,
    required this.completed,
  });

  final String id;
  final String title;
  final int position;
  final bool completed;

  factory CourseModule.fromJson(Map<String, dynamic> json) => CourseModule(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    position: (json['position'] as num?)?.toInt() ?? 0,
    completed: json['completed'] as bool? ?? false,
  );
}
