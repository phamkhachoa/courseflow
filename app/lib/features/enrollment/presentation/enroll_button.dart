import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../application/enrollment_controller.dart';
import '../domain/enrollment_models.dart';

/// Enroll / waitlist call-to-action for a course, driven by
/// [enrollmentControllerProvider]. Embed in the course detail screen.
class EnrollButton extends ConsumerWidget {
  const EnrollButton({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = enrollmentControllerProvider(courseId);
    final enrollment = ref.watch(provider);
    final controller = ref.read(provider.notifier);
    final theme = Theme.of(context);

    return enrollment.when(
      loading: () => const FilledButton(
        onPressed: null,
        child: SizedBox(
          height: 20,
          width: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
      error: (_, __) => OutlinedButton.icon(
        onPressed: () => ref.invalidate(provider),
        icon: const Icon(Icons.refresh),
        label: const Text('Retry'),
      ),
      data: (e) => switch (e.state) {
        EnrollmentState.enrolled => Row(
          children: [
            Icon(Icons.check_circle, color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            const Text('Enrolled'),
          ],
        ),
        EnrollmentState.waitlisted => Row(
          children: [
            Icon(Icons.hourglass_top, color: theme.colorScheme.tertiary),
            const SizedBox(width: 8),
            Text(e.position != null
                ? 'Waitlisted · #${e.position}'
                : 'Waitlisted'),
          ],
        ),
        EnrollmentState.full => FilledButton.tonal(
          onPressed: controller.joinWaitlist,
          child: const Text('Course full · Join waitlist'),
        ),
        EnrollmentState.notEnrolled => FilledButton(
          onPressed: controller.enroll,
          child: const Text('Enroll'),
        ),
      },
    );
  }
}
