# CourseFlow AI Mentor Product Brief

## Vision

CourseFlow AI Mentor biến LMS từ kho khóa học thành một trợ lý học tập thích ứng: hiểu người học đang ở đâu, dự đoán rủi ro, gợi ý bước tiếp theo, trả lời câu hỏi dựa trên nội dung khóa học, hỗ trợ chấm bài và giúp instructor/admin vận hành chất lượng học tập.

Mục tiêu kép:

- Tạo giá trị thật cho CourseFlow LMS.
- Tạo một use case đủ lớn để học và triển khai nhiều họ AI: classical ML, deep learning, NLP embeddings, RAG, LLM, sequence modeling, knowledge tracing, bandit/RL, ASR/CV tùy chọn.

## Personas

| Persona | Need | Outcome |
|---|---|---|
| Learner | Biết nên học gì tiếp theo, hỏi bài nhanh, được hỗ trợ khi yếu | học đúng lộ trình, ít bỏ học |
| Instructor | Giảm tải chấm bài, thấy học viên rủi ro, cải thiện nội dung | feedback nhanh, can thiệp sớm |
| Learning Ops/Admin | Theo dõi completion, quality, AI safety, cost | vận hành AI có kiểm soát |
| AI Engineer | Có platform chuẩn để train, evaluate, activate và monitor model | học được end-to-end MLOps |
| PO/Business Owner | AI tạo giá trị đo được, không chỉ demo kỹ thuật | KPI rõ ràng |

## Product Modules

| Module | Feature | AI family | LMS value |
|---|---|---|---|
| M1 | Recommendation nâng cấp | item-CF, ALS/BPR, two-tower, SASRec | gợi ý khóa học/bài học tiếp theo |
| M2 | Semantic search và cold-start | embeddings, vector search | tìm theo ý nghĩa, khóa mới vẫn discoverable |
| M3 | At-risk prediction | logistic/XGBoost, LSTM/GRU | cảnh báo bỏ học/rớt |
| M4 | Knowledge tracing | DKT, SAKT, transformer | ước lượng skill mastery |
| M5 | Adaptive learning path | optimization, contextual bandit, RL | lộ trình cá nhân hóa |
| M6 | Auto-grading và feedback | LLM, rubric prompting | chấm nháp tự luận, feedback nhanh |
| M7 | AI Tutor course Q&A | RAG, LLM | hỏi đáp dựa trên lesson/chunk nguồn |
| M8 | Quiz/flashcard generator | GenAI | tạo bài luyện tập |
| M9 | Video transcript/summary | ASR, NLP, LLM | phụ đề, tóm tắt video |
| M10 | AI governance | registry, eval, monitoring, audit | vận hành enterprise-ready |

## Epics

### Epic 1: AI Platform Foundation

User stories:

- Là AI Engineer, tôi muốn có contract chuẩn cho feature/model để mọi module dùng chung.
- Là Admin, tôi muốn chỉ model đạt quality gate mới được activate.
- Là PO, tôi muốn biết model nào đang active, metric nào đạt/chưa đạt, chi phí và rủi ro.

Acceptance criteria:

- Có model lifecycle chuẩn.
- Có trạng thái `draft`, `candidate`, `approved`, `active`, `deprecated`, `rejected`.
- Có evaluation report trước khi activate.
- Có audit cho training, approval, serving và rollback.

### Epic 2: Recommendation AI

User stories:

- Là learner, tôi muốn nhận gợi ý khóa học/bài học phù hợp với hành vi học.
- Là Admin, tôi muốn so sánh model hiện tại với ALS/BPR, two-tower hoặc SASRec.
- Là AI Engineer, tôi muốn giữ item-CF hiện tại làm baseline.

Acceptance criteria:

- Metrics tối thiểu: Recall@K, NDCG@K, CTR, enrollment conversion.
- Model mới không được activate nếu thua baseline ở quality gate.
- Recommendation có reason code dễ hiểu.
- Có fallback khi model active không sẵn sàng.

### Epic 3: Semantic Search And Cold-start

User stories:

- Là learner, tôi muốn tìm khóa học bằng ngôn ngữ tự nhiên tiếng Việt.
- Là instructor, tôi muốn hệ thống đề xuất tag/skill cho khóa học.
- Là Admin, tôi muốn khóa mới vẫn có thể được recommend khi chưa có interaction.

Acceptance criteria:

- Course/lesson content được chunk và embed.
- Vector collection có schema, owner, retention và quality checks.
- Search result có score, source reference và explainable reason.
- Có eval set cho search relevance.

### Epic 4: RAG AI Tutor

User stories:

- Là learner, tôi muốn hỏi đáp dựa trên nội dung khóa học.
- Là instructor, tôi muốn AI chỉ trả lời từ tài liệu đã duyệt.
- Là Admin, tôi muốn kiểm soát hallucination, cost và audit.

Acceptance criteria:

- Mỗi câu trả lời có citation về lesson/chunk nguồn.
- Nếu retrieval không đủ tin cậy, AI phải từ chối hoặc hỏi lại.
- Có metrics: groundedness, answer relevance, faithfulness, refusal correctness.
- Có rate limit, conversation audit và cost tracking.

### Epic 5: Auto-grading And Feedback

User stories:

- Là instructor, tôi muốn AI chấm nháp bài tự luận theo rubric.
- Là learner, tôi muốn nhận feedback rõ điểm mạnh/yếu.
- Là Admin, tôi muốn human-in-the-loop cho bài quan trọng.

Acceptance criteria:

- Output có suggested score, rubric mapping, feedback và confidence.
- Không tự động ghi điểm cuối nếu policy yêu cầu instructor duyệt.
- Có agreement metric giữa AI và instructor.
- Có audit trail cho mỗi lần chấm.

### Epic 6: At-risk And Knowledge Tracing

User stories:

- Là instructor, tôi muốn biết learner nào có nguy cơ bỏ học/rớt.
- Là learner, tôi muốn nhận can thiệp sớm trước khi quá muộn.
- Là hệ thống, tôi muốn ước lượng skill mastery theo thời gian.

Acceptance criteria:

- Baseline classical ML có trước deep learning.
- Metrics: AUC, precision@K, recall@K, false positive rate.
- Có reason codes: ít hoạt động, điểm giảm, trễ deadline, quiz yếu.
- Warning phải đi kèm recommended action.

## KPI

Business KPI:

- Course completion rate.
- Recommendation CTR và enrollment conversion.
- Search success rate.
- Dropout/risk reduction.
- Instructor grading time saved.
- Tutor answer resolution rate.

AI KPI:

- Recommendation: Recall@K, NDCG@K, MAP@K.
- Search/RAG: relevance, groundedness, hallucination rate.
- At-risk: AUC, precision@K, recall@K.
- Auto-grading: instructor agreement, rubric consistency.
- Platform: p95 latency, cost/request, activation success rate, drift incident count.

## MVP Definition

MVP không phải xây hết 10 module. MVP là có platform skeleton và 3 module đầu tiên chạy qua cùng lifecycle:

1. Semantic search/course embeddings.
2. Auto-grading human-in-the-loop.
3. At-risk prediction baseline.

Recommendation service hiện tại giữ vai trò benchmark và model-ops reference.

