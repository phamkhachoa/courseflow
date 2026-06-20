# LMS CourseFlow AI Product Onboarding

CourseFlow LMS là product đầu tiên dùng AI Platform. Product này cung cấp dữ liệu học tập, nội dung khóa học, assessment, tracking và vận hành admin để triển khai `CourseFlow AI Mentor`.

## Owned Product Outcomes

| Outcome | AI modules |
|---|---|
| Learner biết nên học gì tiếp theo | recommendation, semantic search, adaptive path |
| Learner được hỗ trợ khi kẹt bài | RAG tutor, quiz/flashcard generation |
| Instructor giảm tải chấm bài | auto-grading, feedback assistant |
| Instructor/Admin phát hiện rủi ro sớm | at-risk prediction, knowledge tracing |
| Learner truy cập nội dung video/tài liệu tốt hơn | speech transcript, lesson summary, document vision ingestion |
| Admin vận hành AI an toàn | model registry, quality gates, audit, cost/drift monitoring |

## Data Dependencies

| Data source | Use |
|---|---|
| `course.published` | content indexing, cold-start, course embeddings |
| `enrollment.completed` | recommendation labels, learner journey |
| `recommendation.tracking` | CTR, feedback loop, offline eval |
| `gradebook.final_grade.updated` | at-risk labels, performance prediction |
| learner activity/clickstream | sequence recommendation, dropout, knowledge tracing |
| assignment submissions/rubrics | auto-grading and feedback |
| lesson/video content | RAG, semantic search, transcript/summary |

## Integration Boundaries

- LMS services keep transactional ownership.
- `dp/` materializes governed analytical features.
- `ai/` trains, evaluates, activates and serves AI decisions.
- Admin/Ops UI should expose model status, approvals, eval reports and audit evidence.
- Learner-facing UX consumes only approved/active AI outputs with fallback.

## First Product Roadmap

1. Keep `recommendation-ml-service` as baseline model ops reference.
2. Add semantic search and content embeddings.
3. Add LLM auto-grading with human review.
4. Add learner-risk baseline.
5. Upgrade recommendation to deep learning only after data/eval gates are ready.
6. Add optional speech/video and document vision only after privacy review and evaluation gates.
