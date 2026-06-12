# CourseFlow Flutter App

The mobile app is for learner workflows that benefit from native UX:

- My courses, assignments and deadlines.
- Course modules and learning path progress.
- Quiz attempts.
- Gradebook and rubric feedback.
- Realtime notifications.
- Portfolio/journal capture.
- Discussion participation.
- Peer review queue.
- Offline-friendly reading/submission draft support in later phases.

## Architecture

```text
lib/
  core/
    api/        Dio client, interceptors, generated Retrofit clients
    router/     go_router routes
    storage/    secure token storage
    theme/      design tokens
  features/
    auth/
    courses/
    assignments/
    quizzes/
    gradebook/
    notifications/
    portfolio/
    discussions/
    certificates/
    peer_review/
```

Recommended stack: Dio + Retrofit for typed API clients, Riverpod for state, freezed/json_serializable for immutable DTOs, go_router for navigation, flutter_secure_storage for tokens.
