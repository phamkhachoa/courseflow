# CourseFlow React Admin

React is used for authenticated, operation-heavy backoffice screens. These pages do not need SEO; they need fast client-side navigation, dense tables, filters, forms and dashboards.

## Use Cases

- User, role and organization management.
- Course publishing and enrollment operations.
- Announcement scheduling.
- Discussion moderation.
- Analytics dashboards and student-at-risk workflows.

## Feature Layout

```text
src/modules/
  identity/
  organization/
  courses/
  enrollments/
  announcements/
  discussions/
  analytics/
src/shared/
  api/
  ui/
  layout/
```

Primary backend entrypoint: `api-gateway`.

Use `VITE_API_GATEWAY_URL=http://localhost:8080/api` for the default local backend cluster, or
`http://localhost:28080/api` when the gateway is started with `API_GATEWAY_PORT=28080`. The admin
source already adds `/admin/v1/...` and `/v1/auth/...` paths.

## Keycloak Login

The admin app can use the enterprise Keycloak flow without changing code:

```bash
VITE_AUTH_MODE=keycloak
VITE_KEYCLOAK_ISSUER_URI=http://localhost:18080/realms/courseflow
VITE_KEYCLOAK_CLIENT_ID=courseflow-admin-web
```

This enables Authorization Code + PKCE and stores the Keycloak access token for gateway calls. Keep
`VITE_AUTH_MODE=legacy` only for explicit local compatibility testing of the retired
identity-service password login.
