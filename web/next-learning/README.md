# CourseFlow Next Learning

Next.js is used for learner-facing and public pages where SEO, shareability or server rendering matters.

## Use Cases

- Public course catalog and course detail pages.
- SEO-friendly course articles/syllabi.
- Certificate verification pages.
- Authenticated learner dashboard when SSR/streaming improves perceived performance.

## Feature Layout

```text
app/                       Next.js app routes
features/
  course-catalog/          public discovery, filters, search facets
  course-detail/           syllabus, outcomes, enrollment CTA
  certificates/            public certificate verification
shared/
  api/                     BFF API client
  ui/                      reusable learner UI
```

Primary backend entrypoint: `api-gateway`.

Use `COURSEFLOW_API_URL=http://localhost:28080/api` and
`NEXT_PUBLIC_API_URL=http://localhost:28080/api` for the default local backend cluster. The learner
source already adds `/v1/...` paths.
