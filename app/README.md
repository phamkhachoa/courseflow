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

## Authentication

The app uses Authorization Code + PKCE with Keycloak through `flutter_appauth`, then calls the
gateway with the Keycloak access token. Profile display fields are hydrated from
`user-management-service` through `/api/v1/users/me/profile`.

Run the app against local Keycloak with:

```bash
flutter run \
  --dart-define=COURSEFLOW_KEYCLOAK_ISSUER=http://localhost:18080/realms/courseflow \
  --dart-define=COURSEFLOW_KEYCLOAK_CLIENT_ID=courseflow-mobile \
  --dart-define=COURSEFLOW_KEYCLOAK_REDIRECT_URL=courseflow://auth/callback
```

When Android/iOS platform folders are generated, register the `courseflow` redirect scheme in the
platform configuration (`appAuthRedirectScheme` on Android, URL type on iOS). Keycloak local realm
already includes the `courseflow-mobile` public PKCE client.
