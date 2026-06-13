import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart';
import '../data/course_repository.dart';
import '../domain/course_models.dart';

/// Public catalog shown on the discovery tab (no auth).
final publicCoursesProvider = FutureProvider.autoDispose<List<CourseSummary>>((
  ref,
) {
  return ref.watch(courseRepositoryProvider).publicCourses();
});

/// Courses the signed-in learner is enrolled in.
final myCoursesProvider =
    FutureProvider.autoDispose<List<CourseSummary>>((ref) {
  final user = ref.watch(authControllerProvider).user;
  if (user == null) return const [];
  return ref.watch(courseRepositoryProvider).myCourses(user.id.toString());
});

/// Course detail by slug.
final courseDetailProvider =
    FutureProvider.autoDispose.family<CourseDetail, String>((ref, slug) {
  return ref.watch(courseRepositoryProvider).courseBySlug(slug);
});
