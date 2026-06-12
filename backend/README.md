# CourseFlow Backend v2

The backend is a Spring Boot microservice system. It intentionally has no `core-service`.

## Module Map

```text
common-library                  Cross-cutting API/error/web helpers only
event-contracts                 Shared event schemas
services/
  identity-service              Users, auth, roles, token lifecycle
  organization-service          Departments, terms, programs, course sections
  course-service                Course catalog, syllabus, materials metadata
  enrollment-service            Enrollment, rosters, waitlists, capacity
  assignment-service            Assignments, rubrics, submissions metadata
  deadline-service              Calendars, due windows, reminder policies
  announcement-service          Announcement draft/schedule/publish
  portfolio-service             Evidence, journals, feedback, grades
  discussion-service            Threads, comments, moderation
  notification-service          Inbox, preferences, realtime push
  media-service                 Uploads, file metadata, signed URLs
  search-service                CDC consumers and Elasticsearch read model
  analytics-service             Learning analytics read models
  gradebook-service             Grade items, weights, final grades, rubric audit
  quiz-service                  Question banks, quizzes, attempts, auto-grading
  certificate-service           Certificate issue/revoke/public verification
  peer-review-service           Reviewer assignment, peer reviews, disputes
  api-gateway                   Edge routing, auth delegation, CORS
  outbox-relay                  Optional outbox relay when Debezium is not used (polls outbox_events per service and republishes to Kafka)
infra/
  docker                        Local infra, one database per service
```

## Local Infra

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

Postgres creates one database per service. Service schema and demo data are owned by each service's Liquibase changelog.

## Build

```bash
mvn -DskipTests compile
```

## Service Rule

No service may query another service's database. Cross-service data access must use API calls, events, or dedicated read models.
