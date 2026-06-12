import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/announcements/presentation/announcement_list_screen.dart';
import '../../features/assignments/presentation/assignment_list_screen.dart';
import '../../features/auth/application/auth_controller.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/profile_screen.dart';
import '../../features/certificates/presentation/certificate_list_screen.dart';
import '../../features/courses/presentation/course_detail_screen.dart';
import '../../features/courses/presentation/course_list_screen.dart';
import '../../features/courses/presentation/module_detail_screen.dart';
import '../../features/courses/presentation/my_courses_screen.dart';
import '../../features/deadlines/presentation/deadline_list_screen.dart';
import '../../features/discussions/presentation/discussion_list_screen.dart';
import '../../features/gradebook/presentation/gradebook_screen.dart';
import '../../features/notifications/presentation/notifications_screen.dart';
import '../../features/peer_review/presentation/peer_review_queue_screen.dart';
import '../../features/portfolio/presentation/portfolio_screen.dart';
import '../../features/quizzes/presentation/quiz_attempt_screen.dart';
import '../../features/search/presentation/search_screen.dart';
import 'app_shell.dart';
import 'router_refresh.dart';

final _rootKey = GlobalKey<NavigatorState>();
final _shellKey = GlobalKey<NavigatorState>();

/// App router with an auth guard:
///  - unauthenticated users are sent to `/login`
///  - the splash (`AuthStatus.unknown`) shows a loader until bootstrap resolves
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = RouterRefreshNotifier(ref, authControllerProvider);

  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/explore',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      final loc = state.matchedLocation;

      if (auth.status == AuthStatus.unknown) {
        return loc == '/splash' ? null : '/splash';
      }
      final loggingIn = loc == '/login';
      if (!auth.isAuthenticated) return loggingIn ? null : '/login';
      if (loggingIn || loc == '/splash') return '/explore';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),

      // Primary tabbed shell.
      StatefulShellRoute.indexedStack(
        builder: (_, __, shell) => AppShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _shellKey,
            routes: [
              GoRoute(
                path: '/explore',
                builder: (_, __) => const CourseListScreen(),
                routes: [
                  GoRoute(
                    path: ':slug',
                    parentNavigatorKey: _rootKey,
                    builder: (_, state) => CourseDetailScreen(
                      slug: state.pathParameters['slug']!,
                    ),
                    routes: [
                      GoRoute(
                        path: 'modules/:moduleId',
                        parentNavigatorKey: _rootKey,
                        builder: (_, state) {
                          final args = state.extra as ModuleArgs?;
                          return ModuleDetailScreen(
                            courseId: args?.courseId ?? '',
                            courseSlug:
                                args?.courseSlug ?? state.pathParameters['slug']!,
                            moduleId: state.pathParameters['moduleId']!,
                            title: args?.title ?? 'Module',
                            completed: args?.completed ?? false,
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/my-courses',
                builder: (_, __) => const MyCoursesScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/notifications',
                builder: (_, __) => const NotificationsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (_, __) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),

      // Detail routes pushed over the shell on the root navigator.
      GoRoute(
        path: '/courses/:courseId/assignments',
        parentNavigatorKey: _rootKey,
        builder: (_, state) => AssignmentListScreen(
          courseId: state.pathParameters['courseId']!,
        ),
      ),
      GoRoute(
        path: '/courses/:courseId/grades',
        parentNavigatorKey: _rootKey,
        builder: (_, state) =>
            GradebookScreen(courseId: state.pathParameters['courseId']!),
      ),
      GoRoute(
        path: '/quizzes/:quizId',
        parentNavigatorKey: _rootKey,
        builder: (_, state) =>
            QuizAttemptScreen(quizId: state.pathParameters['quizId']!),
      ),
      GoRoute(
        path: '/discussions',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const DiscussionListScreen(),
      ),
      GoRoute(
        path: '/peer-review',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const PeerReviewQueueScreen(),
      ),
      GoRoute(
        path: '/certificates',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const CertificateListScreen(),
      ),
      GoRoute(
        path: '/portfolio',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const PortfolioScreen(),
      ),
      GoRoute(
        path: '/search',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const SearchScreen(),
      ),
      GoRoute(
        path: '/announcements',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const AnnouncementListScreen(),
      ),
      GoRoute(
        path: '/deadlines',
        parentNavigatorKey: _rootKey,
        builder: (_, __) => const DeadlineListScreen(),
      ),
    ],
  );
});

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
