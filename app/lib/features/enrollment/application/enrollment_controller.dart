import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart';
import '../../courses/application/course_providers.dart';
import '../data/enrollment_repository.dart';
import '../domain/enrollment_models.dart';

/// Loads + mutates the signed-in learner's enrollment for one course.
class EnrollmentController
    extends AutoDisposeFamilyAsyncNotifier<Enrollment, String> {
  @override
  Future<Enrollment> build(String courseId) async {
    final user = ref.watch(authControllerProvider).user;
    if (user == null) return const Enrollment.notEnrolled();
    return ref.watch(enrollmentRepositoryProvider).status(
          courseId: courseId,
          studentId: user.id.toString(),
        );
  }

  Future<void> enroll() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final result =
          await ref.read(enrollmentRepositoryProvider).enroll(arg);
      // New enrollment should appear in the My courses tab.
      ref.invalidate(myCoursesProvider);
      return result;
    });
  }

  Future<void> joinWaitlist() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(enrollmentRepositoryProvider).joinWaitlist(arg),
    );
  }
}

final enrollmentControllerProvider = AsyncNotifierProvider.autoDispose
    .family<EnrollmentController, Enrollment, String>(
      EnrollmentController.new,
    );
