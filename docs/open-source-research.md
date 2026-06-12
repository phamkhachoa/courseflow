# Open-source Research Notes

## Architecture Reference

- YAS: https://github.com/nashtech-garage/yas
  - Useful patterns: independent business services, BFFs, storefront/backoffice split, search module, Docker/K8s, Kafka, Keycloak, Elasticsearch, OpenTelemetry/Grafana stack.
  - CourseFlow adaptation: `learning-bff` and `backoffice-bff`, no `core-service`, domain services own one business capability.

## LMS References

- Open edX: https://github.com/openedx/openedx-platform
  - Useful patterns: LMS plus Studio/content authoring, independently deployable applications, React micro-frontends, discussion and learner experience separation.
  - CourseFlow feature candidates: course authoring workflow, certificate generation, cohort/team learning, content blocks.

- Moodle: https://github.com/moodle/moodle
  - Useful patterns: assignments, quizzes, forums, gradebook, calendar, notifications, plugin ecosystem.
  - CourseFlow feature candidates: quiz/question bank, gradebook weighting, workshop peer review, calendar integration.

- Canvas LMS: https://github.com/instructure/canvas-lms
  - Useful patterns: modules, assignments, gradebook, discussions, outcomes, admin operations.
  - CourseFlow feature candidates: rubric/outcome mapping, speed-grading queue, course modules, admin audit and moderation workflows.

## Recommended Feature Backlog

1. Announcement + deadline reminder: validates Kafka, Redis/WebSocket, scheduler and notification preferences.
2. Course chat: MongoDB-backed room/message history, STOMP/WebSocket realtime, enrollment-gated access; add Redis pub/sub when scaling beyond one chat-service replica.
3. Discussion forum: validates append-heavy data, moderation, accepted answers and analytics engagement events.
4. Transactional outbox + dedup: validates production-grade event reliability before adding more consumers.
5. Search CDC + Elasticsearch: validates Debezium, Kafka Connect, read models and SEO/public discovery.
6. Analytics: validates event-driven reporting and admin/professor dashboards.
7. Quiz/question bank: validates assessment model and gradebook complexity.
8. Certificate verification page: gives Next.js a real SEO/public use case and a credential feature like large LMS platforms.
9. Rubric/outcomes mapping: makes grading more realistic and supports learning analytics.

## Implemented in v2 Foundation

- Gradebook + Rubric: `gradebook-service` owns weighted scores, grade items, rubric audit and final score APIs.
- Quiz + Question Bank: `quiz-service` owns question banks, quizzes, attempts and auto-grading APIs.
- Course Modules / Learning Path: `course-service` owns course modules, module items, prerequisites and learner progress APIs.
- Certificate Verification: `certificate-service` owns issue, revoke and public verification APIs.
- Peer Review / Workshop: `peer-review-service` owns reviewer assignment, submitted reviews and finalized peer scores.
- Course Chat: `chat-service` owns MongoDB chat rooms/messages, REST history/send APIs and STOMP broadcast for learner rooms.
