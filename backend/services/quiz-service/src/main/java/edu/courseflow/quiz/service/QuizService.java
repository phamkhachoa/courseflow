package edu.courseflow.quiz.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.MissingNode;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.quiz.dto.QuizDtos.CreateQuizRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.EffectiveScoreDto;
import edu.courseflow.quiz.dto.QuizDtos.LearnerSourceStatusDto;
import edu.courseflow.quiz.dto.QuizDtos.ManualGradeAnswerRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.QuestionOptionDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptAnswerDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDetailDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizQuestionDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizReadinessDto;
import edu.courseflow.quiz.dto.QuizDtos.SaveAnswersRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.StartAttemptResponseDto;
import edu.courseflow.quiz.dto.QuizDtos.StudentQuizDto;
import edu.courseflow.quiz.dto.QuizDtos.StudentQuizQuestionDto;
import edu.courseflow.quiz.dto.QuizDtos.SubmitAttemptRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.UpdateQuizRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.UpsertQuizQuestionRequestDto;
import edu.courseflow.quiz.mapper.QuizMapper;
import edu.courseflow.quiz.model.OutboxEvent;
import edu.courseflow.quiz.model.Question;
import edu.courseflow.quiz.model.QuestionBank;
import edu.courseflow.quiz.model.QuestionOption;
import edu.courseflow.quiz.model.Quiz;
import edu.courseflow.quiz.model.QuizAnswer;
import edu.courseflow.quiz.model.QuizAttempt;
import edu.courseflow.quiz.model.QuizQuestion;
import edu.courseflow.quiz.repository.OutboxEventRepository;
import edu.courseflow.quiz.repository.QuestionBankRepository;
import edu.courseflow.quiz.repository.QuestionOptionRepository;
import edu.courseflow.quiz.repository.QuestionRepository;
import edu.courseflow.quiz.repository.QuizAnswerRepository;
import edu.courseflow.quiz.repository.QuizAttemptRepository;
import edu.courseflow.quiz.repository.QuizQuestionRepository;
import edu.courseflow.quiz.repository.QuizRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.transaction.annotation.Transactional;

@Service
public class QuizService {

    private static final List<String> SUBMITTED_ATTEMPT_STATUSES = List.of("GRADED", "PARTIALLY_GRADED");
    private static final List<String> OPEN_ATTEMPT_STATUSES = List.of("IN_PROGRESS");
    private static final Set<String> ALLOWED_SCORING_METHODS = Set.of("HIGHEST", "AVERAGE", "FIRST", "LATEST");
    private static final Set<String> ALLOWED_STATUSES = Set.of("DRAFT", "PUBLISHED", "ARCHIVED");
    private static final Set<String> OPTION_QUESTION_TYPES = Set.of("MULTIPLE_CHOICE", "TRUE_FALSE",
            "MULTIPLE_RESPONSE");

    private final QuizRepository quizzes;
    private final QuestionBankRepository questionBanks;
    private final QuizQuestionRepository quizQuestions;
    private final QuestionRepository questions;
    private final QuestionOptionRepository questionOptions;
    private final QuizAttemptRepository attempts;
    private final QuizAnswerRepository answers;
    private final OutboxEventRepository outboxEvents;
    private final QuizMapper mapper;
    private final ObjectMapper objectMapper;

    public QuizService(QuizRepository quizzes,
            QuestionBankRepository questionBanks,
            QuizQuestionRepository quizQuestions,
            QuestionRepository questions,
            QuestionOptionRepository questionOptions,
            QuizAttemptRepository attempts,
            QuizAnswerRepository answers,
            OutboxEventRepository outboxEvents,
            QuizMapper mapper,
            ObjectMapper objectMapper) {
        this.quizzes = quizzes;
        this.questionBanks = questionBanks;
        this.quizQuestions = quizQuestions;
        this.questions = questions;
        this.questionOptions = questionOptions;
        this.attempts = attempts;
        this.answers = answers;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
        this.objectMapper = objectMapper;
    }

    // ---------- Reads ----------

    public QuizDto getQuiz(UUID quizId) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        return mapper.toDto(quiz, listQuestions(quizId));
    }

    public QuizReadinessDto readiness(UUID quizId) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        return new QuizReadinessDto(
                quiz.getId().toString(),
                quiz.getCourseId().toString(),
                quiz.getStatus());
    }

    public List<QuizDto> listCourseQuizzes(UUID courseId) {
        return quizzes.findByCourseIdOrderByTitleAsc(courseId).stream()
                .map(quiz -> mapper.toDto(quiz, listQuestions(quiz.getId())))
                .toList();
    }

    public List<QuizAttemptDto> listAttempts(UUID quizId) {
        if (!quizzes.existsById(quizId)) {
            throw new NotFoundException("Quiz not found: " + quizId);
        }
        return attempts.findByQuizIdOrderByStartedAtDesc(quizId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public List<QuizAttemptDto> listMyAttempts(UUID quizId, String studentId) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        if (!"PUBLISHED".equalsIgnoreCase(quiz.getStatus())) {
            throw new BadRequestException("QUIZ_NOT_PUBLISHED");
        }
        return attempts.findByQuizIdAndStudentIdOrderByAttemptNoDesc(quizId, studentId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public List<LearnerSourceStatusDto> learnerStatuses(UUID courseId, String studentId, List<UUID> sourceIds) {
        if (studentId == null || studentId.isBlank()) {
            throw new BadRequestException("studentId is required");
        }
        Set<UUID> requestedSourceIds = sourceIds == null ? Set.of() : new HashSet<>(sourceIds);
        List<Quiz> courseQuizzes = quizzes.findByCourseIdOrderByTitleAsc(courseId).stream()
                .filter(quiz -> requestedSourceIds.isEmpty() || requestedSourceIds.contains(quiz.getId()))
                .toList();
        if (courseQuizzes.isEmpty()) {
            return List.of();
        }
        List<UUID> quizIds = courseQuizzes.stream()
                .map(Quiz::getId)
                .toList();
        Map<UUID, List<QuizAttempt>> attemptsByQuiz = attempts
                .findByQuizIdInAndStudentIdOrderByStartedAtDesc(quizIds, studentId.trim()).stream()
                .collect(java.util.stream.Collectors.groupingBy(QuizAttempt::getQuizId));
        Instant now = Instant.now();
        return courseQuizzes.stream()
                .map(quiz -> learnerStatus(quiz, attemptsByQuiz.getOrDefault(quiz.getId(), List.of()), now))
                .toList();
    }

    public UUID quizCourseId(UUID quizId) {
        return quizzes.findById(quizId)
                .map(Quiz::getCourseId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
    }

    public UUID attemptCourseId(UUID attemptId) {
        QuizAttempt attempt = loadAttemptEntity(attemptId);
        return quizCourseId(attempt.getQuizId());
    }

    @Transactional
    public QuizDto createQuiz(CreateQuizRequestDto request) {
        String scoringMethod = normalizeScoringMethod(request.scoringMethod());
        String status = normalizeStatus(request.status(), "DRAFT");
        validateSchedule(request.openAt(), request.closeAt());
        Quiz quiz = quizzes.save(new Quiz(
                UUID.randomUUID(),
                request.courseId(),
                request.title().trim(),
                request.openAt(),
                request.closeAt(),
                request.durationMinutes() == null ? 20 : request.durationMinutes(),
                request.attemptsAllowed() == null ? 1 : request.attemptsAllowed(),
                Boolean.TRUE.equals(request.randomizeQuestions()),
                Boolean.TRUE.equals(request.randomizeOptions()),
                request.gracePeriodSeconds() == null ? 60 : request.gracePeriodSeconds(),
                scoringMethod,
                request.timeLimitEnforced() == null || Boolean.TRUE.equals(request.timeLimitEnforced()),
                request.showCorrectAnswers() == null || Boolean.TRUE.equals(request.showCorrectAnswers()),
                status));
        validatePublishable(quiz.getId(), quiz.getStatus());
        return getQuiz(quiz.getId());
    }

    @Transactional
    public QuizDto updateQuiz(UUID quizId, UpdateQuizRequestDto request) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        validateSchedule(request.openAt(), request.closeAt());
        quiz.update(
                request.title().trim(),
                request.openAt(),
                request.closeAt(),
                request.durationMinutes() == null ? quiz.getDurationMinutes() : request.durationMinutes(),
                request.attemptsAllowed() == null ? quiz.getAttemptsAllowed() : request.attemptsAllowed(),
                request.randomizeQuestions() == null ? quiz.isRandomizeQuestions()
                        : Boolean.TRUE.equals(request.randomizeQuestions()),
                request.randomizeOptions() == null ? quiz.isRandomizeOptions()
                        : Boolean.TRUE.equals(request.randomizeOptions()),
                request.gracePeriodSeconds() == null ? quiz.getGracePeriodSeconds() : request.gracePeriodSeconds(),
                normalizeScoringMethod(request.scoringMethod() == null ? quiz.getScoringMethod()
                        : request.scoringMethod()),
                request.timeLimitEnforced() == null ? quiz.isTimeLimitEnforced()
                        : Boolean.TRUE.equals(request.timeLimitEnforced()),
                request.showCorrectAnswers() == null ? quiz.isShowCorrectAnswers()
                        : Boolean.TRUE.equals(request.showCorrectAnswers()),
                normalizeStatus(request.status(), quiz.getStatus()));
        validatePublishable(quizId, quiz.getStatus());
        quizzes.save(quiz);
        return getQuiz(quizId);
    }

    @Transactional
    public QuizDto createQuestion(UUID quizId, String actorId, UpsertQuizQuestionRequestDto request) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        QuestionBank bank = defaultQuestionBank(quiz.getCourseId(), actorId);
        UUID questionId = UUID.randomUUID();
        Question question = new Question(
                questionId,
                bank.getId(),
                normalizeQuestionType(request.type()),
                request.stem().trim(),
                normalizeDifficulty(request.difficulty()),
                request.points(),
                normalizeQuestionStatus(request.status()),
                jsonOrNull(request.correctAnswer()),
                request.feedback());
        validateQuestion(question, request);
        questions.save(question);
        replaceOptions(questionId, request);
        int position = request.position() == null ? quizQuestions.countByQuizId(quizId) + 1 : request.position();
        quizQuestions.save(new QuizQuestion(UUID.randomUUID(), quizId, questionId, request.points(), position));
        validatePublishable(quizId, quiz.getStatus());
        return getQuiz(quizId);
    }

    @Transactional
    public QuizDto updateQuestion(UUID quizId, UUID questionId, UpsertQuizQuestionRequestDto request) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        QuizQuestion link = quizQuestions.findByQuizIdAndQuestionId(quizId, questionId)
                .orElseThrow(() -> new NotFoundException("Question not on quiz: " + questionId));
        Question question = questions.findById(questionId)
                .orElseThrow(() -> new NotFoundException("Question not found: " + questionId));
        question.update(
                normalizeQuestionType(request.type()),
                request.stem().trim(),
                normalizeDifficulty(request.difficulty()),
                request.points(),
                normalizeQuestionStatus(request.status()),
                jsonOrNull(request.correctAnswer()),
                request.feedback());
        validateQuestion(question, request);
        questions.save(question);
        replaceOptions(questionId, request);
        link.update(request.points(), request.position() == null ? link.getPosition() : request.position());
        quizQuestions.save(link);
        validatePublishable(quizId, quiz.getStatus());
        return getQuiz(quizId);
    }

    @Transactional
    public QuizDto removeQuestion(UUID quizId, UUID questionId) {
        if (!quizzes.existsById(quizId)) {
            throw new NotFoundException("Quiz not found: " + quizId);
        }
        if (attempts.existsByQuizId(quizId)) {
            throw new BadRequestException("QUIZ_HAS_ATTEMPTS_CANNOT_REMOVE_QUESTION");
        }
        long deleted = quizQuestions.deleteByQuizIdAndQuestionId(quizId, questionId);
        if (deleted == 0) {
            throw new NotFoundException("Question not on quiz: " + questionId);
        }
        reindexQuizQuestions(quizId);
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        validatePublishable(quizId, quiz.getStatus());
        return getQuiz(quizId);
    }

    private List<QuizQuestionDto> listQuestions(UUID quizId) {
        return quizQuestions.findByQuizIdOrderByPositionAsc(quizId).stream()
                .map(link -> {
                    Question question = questions.findById(link.getQuestionId())
                            .orElseThrow(() -> new NotFoundException("Question not found: " + link.getQuestionId()));
                    return mapper.toQuestionDto(
                            question, link, parseJson(question.getCorrectAnswer()), listOptions(question.getId()));
                })
                .toList();
    }

    private void reindexQuizQuestions(UUID quizId) {
        List<QuizQuestion> links = quizQuestions.findByQuizIdOrderByPositionAsc(quizId);
        for (int index = 0; index < links.size(); index++) {
            QuizQuestion link = links.get(index);
            int nextPosition = index + 1;
            if (link.getPosition() != nextPosition) {
                link.update(link.getPoints(), nextPosition);
            }
        }
        quizQuestions.saveAll(links);
    }

    private List<QuestionOptionDto> listOptions(UUID questionId) {
        return questionOptions.findByQuestionIdOrderByLabelAsc(questionId).stream()
                .map(mapper::toDto)
                .toList();
    }

    // ---------- Attempts ----------

    @Transactional
    public StartAttemptResponseDto startAttempt(UUID quizId, String studentId) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        validateQuizCanStart(quiz);
        var existingOpenAttempt = attempts.findFirstByQuizIdAndStudentIdAndStatusInOrderByStartedAtDesc(
                quizId, studentId, OPEN_ATTEMPT_STATUSES);
        if (existingOpenAttempt.isPresent()) {
            return toStartAttemptResponse(existingOpenAttempt.get());
        }

        int nextAttemptNo = attempts.nextAttemptNo(quizId, studentId);
        if (nextAttemptNo > quiz.getAttemptsAllowed()) {
            throw new BadRequestException("QUIZ_ATTEMPT_LIMIT_REACHED");
        }

        Instant startedAt = Instant.now();
        Instant deadlineAt = computeDeadline(quiz, startedAt);
        QuizAttempt attempt = attempts.save(new QuizAttempt(
                UUID.randomUUID(), quizId, studentId, nextAttemptNo, startedAt, deadlineAt));
        attempt.setQuestionsSnapshot(toJson(buildAttemptSnapshot(getQuiz(quizId))));
        attempt = attempts.save(attempt);
        return toStartAttemptResponse(attempt);
    }

    /** Owner (student_id) of an attempt, for controller-level ownership checks. */
    public String attemptStudentId(UUID attemptId) {
        return attempts.findById(attemptId)
                .map(QuizAttempt::getStudentId)
                .orElseThrow(() -> new NotFoundException("Attempt not found: " + attemptId));
    }

    /** True when the student has at least one GRADED attempt on this quiz (gate for revealing answers). */
    public boolean hasGradedAttempt(UUID quizId, String studentId) {
        return attempts.existsByQuizIdAndStudentIdAndStatus(quizId, studentId, "GRADED");
    }

    /**
     * Correct answers can be revealed only when the quiz allows it and the student can no longer use
     * those answers on another live attempt: either the quiz is closed or the attempt limit is spent.
     */
    public boolean canRevealCorrectAnswers(QuizDto quiz, String studentId) {
        if (!quiz.showCorrectAnswers() || !hasGradedAttempt(UUID.fromString(quiz.id()), studentId)) {
            return false;
        }
        Instant now = Instant.now();
        UUID quizId = UUID.fromString(quiz.id());
        boolean closed = quiz.closeAt() != null && now.isAfter(quiz.closeAt());
        boolean hasOpenAttempt = attempts.existsByQuizIdAndStudentIdAndStatusIn(
                quizId, studentId, OPEN_ATTEMPT_STATUSES);
        boolean attemptsExhausted = !hasOpenAttempt
                && attempts.countByQuizIdAndStudentIdAndStatusIn(quizId, studentId, SUBMITTED_ATTEMPT_STATUSES)
                >= quiz.attemptsAllowed();
        return closed || attemptsExhausted;
    }

    private LearnerSourceStatusDto learnerStatus(Quiz quiz, List<QuizAttempt> learnerAttempts, Instant now) {
        QuizAttempt latest = learnerAttempts.isEmpty() ? null : learnerAttempts.getFirst();
        QuizAttempt openAttempt = learnerAttempts.stream()
                .filter(attempt -> "IN_PROGRESS".equalsIgnoreCase(attempt.getStatus()))
                .findFirst()
                .orElse(null);
        boolean hasCompletedAttempt = learnerAttempts.stream()
                .anyMatch(attempt -> "GRADED".equalsIgnoreCase(attempt.getStatus()));
        boolean hasPendingManualGrade = learnerAttempts.stream()
                .anyMatch(attempt -> "PARTIALLY_GRADED".equalsIgnoreCase(attempt.getStatus()));
        Instant dueAt = openAttempt != null && openAttempt.getDeadlineAt() != null
                ? openAttempt.getDeadlineAt()
                : quiz.getCloseAt();
        boolean overdue = !hasCompletedAttempt && dueAt != null && now.isAfter(dueAt);
        String sourceStatus = quizSourceStatus(
                quiz,
                learnerAttempts.size(),
                openAttempt,
                hasCompletedAttempt,
                hasPendingManualGrade,
                overdue,
                now);
        return new LearnerSourceStatusDto(
                "QUIZ",
                quiz.getId().toString(),
                quiz.getCourseId().toString(),
                quiz.getTitle(),
                sourceStatus,
                quiz.getOpenAt(),
                dueAt,
                quiz.getCloseAt(),
                latest == null ? null : latest.getStatus(),
                latest == null ? null : latest.getId().toString(),
                learnerAttempts.size(),
                quiz.getAttemptsAllowed(),
                hasCompletedAttempt,
                overdue);
    }

    private String quizSourceStatus(Quiz quiz,
                                    int attemptsUsed,
                                    QuizAttempt openAttempt,
                                    boolean hasCompletedAttempt,
                                    boolean hasPendingManualGrade,
                                    boolean overdue,
                                    Instant now) {
        if (!"PUBLISHED".equalsIgnoreCase(quiz.getStatus())) {
            return "UNAVAILABLE";
        }
        if (hasCompletedAttempt) {
            return "COMPLETED";
        }
        if (hasPendingManualGrade) {
            return "PENDING_GRADE";
        }
        if (openAttempt != null) {
            return overdue ? "OVERDUE" : "IN_PROGRESS";
        }
        if (quiz.getOpenAt() != null && now.isBefore(quiz.getOpenAt())) {
            return "NOT_AVAILABLE";
        }
        if (quiz.getCloseAt() != null && now.isAfter(quiz.getCloseAt())) {
            return "OVERDUE";
        }
        if (quiz.getAttemptsAllowed() > 0 && attemptsUsed >= quiz.getAttemptsAllowed()) {
            return "ATTEMPTS_EXHAUSTED";
        }
        return "READY";
    }

    private void validateQuizCanStart(Quiz quiz) {
        if (!"PUBLISHED".equalsIgnoreCase(quiz.getStatus())) {
            throw new BadRequestException("QUIZ_NOT_PUBLISHED");
        }
        Instant now = Instant.now();
        if (quiz.getOpenAt() != null && now.isBefore(quiz.getOpenAt())) {
            throw new BadRequestException("QUIZ_NOT_OPEN_YET");
        }
        if (quiz.getCloseAt() != null && now.isAfter(quiz.getCloseAt())) {
            throw new BadRequestException("QUIZ_CLOSED");
        }
    }

    /**
     * Sanitized quiz for students: strips per-question correct answers, feedback, and the per-option
     * {@code correct} flag so the quiz can be taken without leaking the key (closes P0-3).
     */
    public StudentQuizDto toStudentView(QuizDto quiz) {
        return mapper.toStudentView(quiz);
    }

    private StartAttemptResponseDto toStartAttemptResponse(QuizAttempt attempt) {
        List<StudentQuizQuestionDto> questions = snapshotQuestions(attempt).stream()
                .map(mapper::toStudentQuestion)
                .toList();
        return new StartAttemptResponseDto(mapper.toDto(attempt), questions);
    }

    private List<QuizQuestionDto> buildAttemptSnapshot(QuizDto quiz) {
        List<QuizQuestionDto> questions = new ArrayList<>(quiz.questions());
        if (quiz.randomizeQuestions()) {
            Collections.shuffle(questions);
        }
        List<QuizQuestionDto> snapshot = new ArrayList<>(questions.size());
        int position = 1;
        for (QuizQuestionDto question : questions) {
            List<QuestionOptionDto> options = new ArrayList<>(
                    question.options() == null ? List.of() : question.options());
            if (quiz.randomizeOptions()) {
                Collections.shuffle(options);
            }
            snapshot.add(copyQuestion(question, position++, options));
        }
        return snapshot;
    }

    private QuizQuestionDto copyQuestion(QuizQuestionDto question, int position, List<QuestionOptionDto> options) {
        return new QuizQuestionDto(
                question.id(),
                question.type(),
                question.stem(),
                question.difficulty(),
                question.status(),
                question.points(),
                position,
                question.correctAnswer(),
                question.feedback(),
                options);
    }

    private List<QuizQuestionDto> snapshotQuestions(QuizAttempt attempt) {
        String snapshot = attempt.getQuestionsSnapshot();
        if (snapshot == null || snapshot.isBlank()) {
            return getQuiz(attempt.getQuizId()).questions();
        }
        try {
            return objectMapper.readValue(snapshot, new TypeReference<List<QuizQuestionDto>>() {
            });
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to parse quiz attempt snapshot: " + attempt.getId(), ex);
        }
    }

    @Transactional
    public QuizAttemptDto submitAttempt(UUID attemptId, SubmitAttemptRequestDto request) {
        QuizAttempt attempt = loadAttemptEntity(attemptId);
        return submitAttemptInternal(attempt, request.answers(), false);
    }

    private QuizAttemptDto submitAttemptInternal(QuizAttempt attempt, Map<String, JsonNode> requestAnswers,
            boolean forceAutoSubmit) {
        if (!"IN_PROGRESS".equals(attempt.getStatus())) {
            throw new BadRequestException("QUIZ_ATTEMPT_ALREADY_SUBMITTED");
        }
        Quiz quiz = quizzes.findById(attempt.getQuizId())
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + attempt.getQuizId()));
        List<QuizQuestionDto> snapshotQuestions = snapshotQuestions(attempt);

        Instant now = Instant.now();
        boolean autoSubmitted = forceAutoSubmit;
        if (quiz.isTimeLimitEnforced()) {
            Instant deadline = attempt.getDeadlineAt() != null
                    ? attempt.getDeadlineAt()
                    : attempt.getStartedAt().plus(Duration.ofMinutes(quiz.getDurationMinutes()));
            Instant hardDeadline = deadline.plusSeconds(Math.max(0, quiz.getGracePeriodSeconds()));
            if (now.isAfter(hardDeadline)) {
                autoSubmitted = true;
            }
        }

        BigDecimal totalAuto = BigDecimal.ZERO;
        boolean anyEssay = false;
        Map<String, JsonNode> savedAnswers = answers.findByAttemptId(attempt.getId()).stream()
                .collect(java.util.stream.Collectors.toMap(
                        answer -> answer.getQuestionId().toString(),
                        answer -> parseJson(answer.getAnswerPayload()),
                        (left, right) -> right));
        for (QuizQuestionDto q : snapshotQuestions) {
            JsonNode answer = !autoSubmitted && requestAnswers != null && requestAnswers.containsKey(q.id())
                    ? requestAnswers.get(q.id())
                    : savedAnswers.getOrDefault(q.id(), MissingNode.getInstance());
            BigDecimal auto;
            if ("ESSAY".equalsIgnoreCase(q.type())) {
                auto = null;
                anyEssay = true;
            } else {
                auto = gradeAnswer(q, answer).setScale(2, RoundingMode.HALF_UP);
                totalAuto = totalAuto.add(auto);
            }
            saveAnswer(attempt.getId(), UUID.fromString(q.id()), answer, auto);
        }

        String status = anyEssay ? "PARTIALLY_GRADED" : "GRADED";
        attempt.submit(now, status, totalAuto, autoSubmitted);
        attempts.save(attempt);

        if ("GRADED".equals(status)) {
            saveOutbox(attempt.getId(), mapper.toDto(attempt), toQuizDto(quiz, snapshotQuestions), totalAuto);
        }
        return mapper.toDto(attempt);
    }

    private void enforceCanSave(Quiz quiz, QuizAttempt attempt) {
        if (!quiz.isTimeLimitEnforced()) {
            return;
        }
        Instant deadline = attempt.getDeadlineAt() != null
                ? attempt.getDeadlineAt()
                : attempt.getStartedAt().plus(Duration.ofMinutes(quiz.getDurationMinutes()));
        if (Instant.now().isAfter(deadline)) {
            throw new BadRequestException("QUIZ_TIME_LIMIT_EXCEEDED");
        }
    }

    private QuizDto toQuizDto(Quiz quiz, List<QuizQuestionDto> questions) {
        return new QuizDto(
                quiz.getId().toString(),
                quiz.getCourseId().toString(),
                quiz.getTitle(),
                quiz.getOpenAt(),
                quiz.getCloseAt(),
                quiz.getDurationMinutes(),
                quiz.getAttemptsAllowed(),
                quiz.isRandomizeQuestions(),
                quiz.isRandomizeOptions(),
                quiz.getGracePeriodSeconds(),
                quiz.getScoringMethod(),
                quiz.isTimeLimitEnforced(),
                quiz.isShowCorrectAnswers(),
                quiz.getStatus(),
                questions);
    }

    @Transactional
    public QuizAttemptDto saveAnswers(UUID attemptId, SaveAnswersRequestDto request) {
        QuizAttempt attempt = loadAttemptEntity(attemptId);
        if (!"IN_PROGRESS".equals(attempt.getStatus())) {
            throw new BadRequestException("QUIZ_ATTEMPT_ALREADY_SUBMITTED");
        }
        Quiz quiz = quizzes.findById(attempt.getQuizId())
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + attempt.getQuizId()));
        enforceCanSave(quiz, attempt);
        Set<String> validQuestionIds = snapshotQuestions(attempt).stream()
                .map(QuizQuestionDto::id)
                .collect(java.util.stream.Collectors.toSet());
        if (request.answers() == null) {
            return mapper.toDto(attempt);
        }
        for (Map.Entry<String, JsonNode> entry : request.answers().entrySet()) {
            if (!validQuestionIds.contains(entry.getKey())) {
                throw new BadRequestException("QUESTION_NOT_ON_QUIZ: " + entry.getKey());
            }
            saveDraftAnswer(attemptId, UUID.fromString(entry.getKey()), entry.getValue());
        }
        return mapper.toDto(attempt);
    }

    @Transactional
    public QuizAttemptDto manualGradeAnswer(UUID attemptId, UUID questionId, String graderId,
            ManualGradeAnswerRequestDto req) {
        QuizAttempt attempt = loadAttemptEntity(attemptId);
        List<QuizQuestionDto> snapshot = snapshotQuestions(attempt);
        QuizQuestionDto question = snapshot.stream()
                .filter(q -> q.id().equals(questionId.toString()))
                .findFirst()
                .orElseThrow(() -> new NotFoundException("Question not on quiz: " + questionId));
        if (req.score().compareTo(BigDecimal.ZERO) < 0 || req.score().compareTo(question.points()) > 0) {
            throw new BadRequestException("SCORE_OUT_OF_RANGE");
        }

        QuizAnswer answer = answers.findByAttemptIdAndQuestionId(attemptId, questionId)
                .orElseThrow(() -> new NotFoundException("Answer not found for question: " + questionId));
        answer.manualGrade(req.score(), req.feedback(), graderId);
        answers.save(answer);

        Quiz quiz = quizzes.findById(attempt.getQuizId())
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + attempt.getQuizId()));
        recomputeAttemptScore(attempt, toQuizDto(quiz, snapshot));
        return mapper.toDto(attempt);
    }

    private void recomputeAttemptScore(QuizAttempt attempt, QuizDto quiz) {
        List<QuizAnswer> attemptAnswers = answers.findByAttemptId(attempt.getId());
        BigDecimal total = attemptAnswers.stream()
                .map(answer -> answer.getManualScore() != null ? answer.getManualScore() : answer.getAutoScore())
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        Set<String> pendingEssayQuestionIds = quiz.questions().stream()
                .filter(question -> "ESSAY".equalsIgnoreCase(question.type()))
                .map(QuizQuestionDto::id)
                .collect(java.util.stream.Collectors.toSet());
        boolean stillPending = attemptAnswers.stream()
                .anyMatch(answer -> pendingEssayQuestionIds.contains(answer.getQuestionId().toString())
                        && answer.getManualScore() == null);
        String status = stillPending ? "PARTIALLY_GRADED" : "GRADED";
        attempt.updateScore(status, total);
        attempts.save(attempt);
        if (!stillPending) {
            saveOutbox(attempt.getId(), mapper.toDto(attempt), quiz, total);
        }
    }

    public QuizAttemptDetailDto getAttemptDetail(UUID attemptId) {
        QuizAttempt attempt = loadAttemptEntity(attemptId);
        List<QuizAttemptAnswerDto> attemptAnswers = answers.findByAttemptId(attemptId).stream()
                .map(answer -> {
                    BigDecimal auto = answer.getAutoScore();
                    BigDecimal manual = answer.getManualScore();
                    BigDecimal total = manual != null ? manual : auto;
                    return mapper.toAnswerDto(answer, parseJson(answer.getAnswerPayload()), total);
                })
                .toList();
        return new QuizAttemptDetailDto(mapper.toDto(attempt), attemptAnswers);
    }

    public QuizAttemptDetailDto getAttemptDetailForStudent(UUID attemptId, boolean revealQuestionScores) {
        QuizAttemptDetailDto detail = getAttemptDetail(attemptId);
        if (revealQuestionScores) {
            return detail;
        }
        List<QuizAttemptAnswerDto> sanitized = detail.answers().stream()
                .map(answer -> new QuizAttemptAnswerDto(
                        answer.questionId(),
                        answer.answer(),
                        null,
                        null,
                        null,
                        null,
                        null,
                        null))
                .toList();
        return new QuizAttemptDetailDto(detail.attempt(), sanitized);
    }

    public EffectiveScoreDto effectiveScore(UUID quizId, String studentId) {
        Quiz quiz = quizzes.findById(quizId)
                .orElseThrow(() -> new NotFoundException("Quiz not found: " + quizId));
        String scoringMethod = quiz.getScoringMethod();
        List<AttemptScore> rows = attempts
                .findByQuizIdAndStudentIdAndStatusOrderByAttemptNoAsc(quizId, studentId, "GRADED")
                .stream()
                .map(attempt -> new AttemptScore(
                        attempt.getAttemptNo(),
                        attempt.getScore() == null ? BigDecimal.ZERO : attempt.getScore(),
                        attempt.getSubmittedAt()))
                .toList();
        if (rows.isEmpty()) {
            return new EffectiveScoreDto(quizId.toString(), studentId, scoringMethod, BigDecimal.ZERO, 0);
        }
        BigDecimal effective = switch (scoringMethod.toUpperCase(Locale.ROOT)) {
            case "HIGHEST" -> rows.stream().map(AttemptScore::score).max(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
            case "AVERAGE" -> rows.stream().map(AttemptScore::score).reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(rows.size()), 2, RoundingMode.HALF_UP);
            case "FIRST" -> rows.get(0).score();
            case "LATEST" -> rows.get(rows.size() - 1).score();
            default -> rows.get(rows.size() - 1).score();
        };
        return new EffectiveScoreDto(quizId.toString(), studentId, scoringMethod, effective, rows.size());
    }

    @Scheduled(fixedDelayString = "${courseflow.quiz.expiry-sweep-interval-ms:60000}")
    @Transactional
    public void sweepExpiredAttempts() {
        Instant now = Instant.now();
        List<QuizAttempt> expiredCandidates = attempts
                .findByStatusAndDeadlineAtLessThanEqualOrderByDeadlineAtAsc("IN_PROGRESS", now);
        for (QuizAttempt attempt : expiredCandidates) {
            Quiz quiz = quizzes.findById(attempt.getQuizId()).orElse(null);
            if (quiz == null || !quiz.isTimeLimitEnforced() || attempt.getDeadlineAt() == null) {
                continue;
            }
            Instant hardDeadline = attempt.getDeadlineAt().plusSeconds(Math.max(0, quiz.getGracePeriodSeconds()));
            if (!now.isBefore(hardDeadline)) {
                submitAttemptInternal(attempt, Map.of(), true);
            }
        }
    }

    // ---------- Per-question grading ----------

    private BigDecimal gradeAnswer(QuizQuestionDto q, JsonNode answer) {
        if (answer == null || answer.isMissingNode() || answer.isNull()) {
            return BigDecimal.ZERO;
        }
        String type = q.type() == null ? "" : q.type().toUpperCase(Locale.ROOT);
        BigDecimal points = q.points() == null ? BigDecimal.ZERO : q.points();
        return switch (type) {
            case "MULTIPLE_CHOICE", "TRUE_FALSE" -> gradeSingleChoice(q, answer, points);
            case "MULTIPLE_RESPONSE" -> gradeMultipleResponse(q, answer, points);
            case "SHORT_ANSWER" -> gradeShortAnswer(q, answer, points);
            case "FILL_BLANK" -> gradeFillBlank(q, answer, points);
            case "NUMERICAL" -> gradeNumerical(q, answer, points);
            case "MATCHING" -> gradeMatching(q, answer, points);
            default -> BigDecimal.ZERO;
        };
    }

    private BigDecimal gradeSingleChoice(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        String selected = answer.asText("").trim();
        return q.options().stream()
                .filter(o -> Boolean.TRUE.equals(o.correct()))
                .map(QuestionOptionDto::label)
                .anyMatch(selected::equals)
                        ? points
                        : BigDecimal.ZERO;
    }

    private BigDecimal gradeMultipleResponse(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        Set<String> selected = new HashSet<>();
        if (answer.isArray()) {
            answer.forEach(n -> selected.add(n.asText("").trim()));
        } else if (answer.isTextual()) {
            selected.add(answer.asText().trim());
        }
        BigDecimal totalCorrectWeight = BigDecimal.ZERO;
        BigDecimal gained = BigDecimal.ZERO;
        for (QuestionOptionDto o : q.options()) {
            BigDecimal w = o.weight() == null ? BigDecimal.ONE : o.weight();
            boolean isCorrect = Boolean.TRUE.equals(o.correct());
            if (isCorrect) {
                totalCorrectWeight = totalCorrectWeight.add(w);
                if (selected.contains(o.label())) {
                    gained = gained.add(w);
                }
            } else if (selected.contains(o.label())) {
                gained = gained.subtract(w);
            }
        }
        if (totalCorrectWeight.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        BigDecimal ratio = gained.divide(totalCorrectWeight, 4, RoundingMode.HALF_UP);
        if (ratio.compareTo(BigDecimal.ZERO) < 0) {
            ratio = BigDecimal.ZERO;
        }
        return points.multiply(ratio);
    }

    private BigDecimal gradeShortAnswer(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        String candidate = answer.asText("").trim();
        JsonNode spec = q.correctAnswer();
        if (spec == null || !spec.has("answers")) {
            return BigDecimal.ZERO;
        }
        boolean caseSensitive = spec.path("caseSensitive").asBoolean(false);
        for (JsonNode opt : spec.path("answers")) {
            String acceptable = opt.asText();
            boolean match = caseSensitive ? acceptable.equals(candidate) : acceptable.equalsIgnoreCase(candidate);
            if (match) {
                return points;
            }
        }
        return BigDecimal.ZERO;
    }

    private BigDecimal gradeFillBlank(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        JsonNode spec = q.correctAnswer();
        if (spec == null || !spec.has("answers") || !spec.path("answers").isArray()) {
            return BigDecimal.ZERO;
        }
        JsonNode blanks = spec.path("answers");
        int total = blanks.size();
        if (total == 0) {
            return BigDecimal.ZERO;
        }
        boolean caseSensitive = spec.path("caseSensitive").asBoolean(false);
        BigDecimal perBlank = points.divide(BigDecimal.valueOf(total), 4, RoundingMode.HALF_UP);
        BigDecimal score = BigDecimal.ZERO;
        if (!answer.isArray()) {
            return BigDecimal.ZERO;
        }
        for (int i = 0; i < Math.min(total, answer.size()); i++) {
            String candidate = answer.get(i).asText("").trim();
            JsonNode accepted = blanks.get(i);
            if (!accepted.isArray()) {
                continue;
            }
            for (JsonNode a : accepted) {
                String acceptable = a.asText();
                boolean match = caseSensitive ? acceptable.equals(candidate) : acceptable.equalsIgnoreCase(candidate);
                if (match) {
                    score = score.add(perBlank);
                    break;
                }
            }
        }
        return score;
    }

    private BigDecimal gradeNumerical(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        JsonNode spec = q.correctAnswer();
        if (spec == null || !spec.has("value")) {
            return BigDecimal.ZERO;
        }
        double value = spec.path("value").asDouble();
        double tolerance = spec.path("tolerance").asDouble(0);
        double candidate;
        try {
            candidate = answer.isNumber() ? answer.asDouble() : Double.parseDouble(answer.asText());
        } catch (NumberFormatException ex) {
            return BigDecimal.ZERO;
        }
        return Math.abs(candidate - value) <= tolerance ? points : BigDecimal.ZERO;
    }

    private BigDecimal gradeMatching(QuizQuestionDto q, JsonNode answer, BigDecimal points) {
        JsonNode spec = q.correctAnswer();
        if (spec == null || !spec.path("pairs").isObject() || !answer.isObject()) {
            return BigDecimal.ZERO;
        }
        JsonNode correctPairs = spec.path("pairs");
        int total = correctPairs.size();
        if (total == 0) {
            return BigDecimal.ZERO;
        }
        BigDecimal perPair = points.divide(BigDecimal.valueOf(total), 4, RoundingMode.HALF_UP);
        BigDecimal score = BigDecimal.ZERO;
        Iterator<Map.Entry<String, JsonNode>> it = correctPairs.fields();
        while (it.hasNext()) {
            Map.Entry<String, JsonNode> e = it.next();
            String expected = e.getValue().asText();
            String got = answer.path(e.getKey()).asText("");
            if (Objects.equals(expected, got)) {
                score = score.add(perPair);
            }
        }
        return score;
    }

    // ---------- Persistence helpers ----------

    private void saveAnswer(UUID attemptId, UUID questionId, JsonNode answer, BigDecimal autoScore) {
        String payload = toJson(answer == null ? MissingNode.getInstance() : answer);
        QuizAnswer quizAnswer = answers.findByAttemptIdAndQuestionId(attemptId, questionId)
                .orElseGet(() -> new QuizAnswer(attemptId, questionId, payload, autoScore));
        quizAnswer.updateAuto(payload, autoScore);
        answers.save(quizAnswer);
    }

    private void saveDraftAnswer(UUID attemptId, UUID questionId, JsonNode answer) {
        String payload = toJson(answer == null ? MissingNode.getInstance() : answer);
        QuizAnswer quizAnswer = answers.findByAttemptIdAndQuestionId(attemptId, questionId)
                .orElseGet(() -> new QuizAnswer(attemptId, questionId, payload, null));
        quizAnswer.updateDraft(payload);
        answers.save(quizAnswer);
    }

    private QuestionBank defaultQuestionBank(UUID courseId, String actorId) {
        return questionBanks.findFirstByCourseIdOrderByCreatedAtAsc(courseId)
                .orElseGet(() -> questionBanks.save(new QuestionBank(
                        UUID.randomUUID(),
                        courseId,
                        "Course question bank",
                        actorId == null || actorId.isBlank() ? "system" : actorId)));
    }

    private void replaceOptions(UUID questionId, UpsertQuizQuestionRequestDto request) {
        questionOptions.deleteByQuestionId(questionId);
        List<UpsertQuestionOption> normalized = normalizedOptions(request);
        for (UpsertQuestionOption option : normalized) {
            questionOptions.save(new QuestionOption(
                    UUID.randomUUID(),
                    questionId,
                    option.label(),
                    option.content(),
                    option.correct(),
                    option.weight(),
                    option.feedback()));
        }
    }

    private List<UpsertQuestionOption> normalizedOptions(UpsertQuizQuestionRequestDto request) {
        if (request.options() == null) {
            return List.of();
        }
        return request.options().stream()
                .map(option -> new UpsertQuestionOption(
                        option.label().trim(),
                        option.content().trim(),
                        Boolean.TRUE.equals(option.correct()),
                        option.weight() == null ? BigDecimal.ONE : option.weight(),
                        option.feedback()))
                .toList();
    }

    private void validateQuestion(Question question, UpsertQuizQuestionRequestDto request) {
        String type = question.getType();
        List<UpsertQuestionOption> options = normalizedOptions(request);
        if (OPTION_QUESTION_TYPES.contains(type)) {
            if (options.size() < 2) {
                throw new BadRequestException("QUIZ_CHOICE_QUESTION_NEEDS_OPTIONS");
            }
            long correctCount = options.stream().filter(UpsertQuestionOption::correct).count();
            if (correctCount == 0) {
                throw new BadRequestException("QUIZ_CHOICE_QUESTION_NEEDS_CORRECT_OPTION");
            }
            if (!"MULTIPLE_RESPONSE".equals(type) && correctCount > 1) {
                throw new BadRequestException("QUIZ_SINGLE_CHOICE_ONLY_ONE_CORRECT_OPTION");
            }
        } else if (!"ESSAY".equals(type) && (request.correctAnswer() == null || request.correctAnswer().isNull())) {
            throw new BadRequestException("QUIZ_QUESTION_NEEDS_CORRECT_ANSWER");
        }
    }

    private String normalizeQuestionType(String raw) {
        String type = raw == null ? "" : raw.trim().toUpperCase(Locale.ROOT);
        Set<String> allowed = Set.of("MULTIPLE_CHOICE", "TRUE_FALSE", "MULTIPLE_RESPONSE", "SHORT_ANSWER",
                "FILL_BLANK", "NUMERICAL", "MATCHING", "ESSAY");
        if (!allowed.contains(type)) {
            throw new BadRequestException("UNKNOWN_QUESTION_TYPE: " + raw);
        }
        return type;
    }

    private String normalizeQuestionStatus(String raw) {
        String status = raw == null || raw.isBlank() ? "ACTIVE" : raw.trim().toUpperCase(Locale.ROOT);
        if (!Set.of("ACTIVE", "DRAFT", "ARCHIVED").contains(status)) {
            throw new BadRequestException("UNKNOWN_QUESTION_STATUS: " + raw);
        }
        return status;
    }

    private String normalizeDifficulty(String raw) {
        String difficulty = raw == null || raw.isBlank() ? "MEDIUM" : raw.trim().toUpperCase(Locale.ROOT);
        if (!Set.of("EASY", "MEDIUM", "HARD").contains(difficulty)) {
            throw new BadRequestException("UNKNOWN_QUESTION_DIFFICULTY: " + raw);
        }
        return difficulty;
    }

    private String normalizeScoringMethod(String raw) {
        String method = raw == null || raw.isBlank() ? "HIGHEST" : raw.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_SCORING_METHODS.contains(method)) {
            throw new BadRequestException("UNKNOWN_SCORING_METHOD: " + raw);
        }
        return method;
    }

    private String normalizeStatus(String raw, String fallback) {
        String status = raw == null || raw.isBlank() ? fallback : raw.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_STATUSES.contains(status)) {
            throw new BadRequestException("UNKNOWN_QUIZ_STATUS: " + raw);
        }
        return status;
    }

    private void validateSchedule(Instant openAt, Instant closeAt) {
        if (openAt != null && closeAt != null && !closeAt.isAfter(openAt)) {
            throw new BadRequestException("QUIZ_CLOSE_AT_MUST_BE_AFTER_OPEN_AT");
        }
    }

    private void validatePublishable(UUID quizId, String status) {
        if (!"PUBLISHED".equalsIgnoreCase(status)) {
            return;
        }
        List<QuizQuestion> links = quizQuestions.findByQuizIdOrderByPositionAsc(quizId);
        if (links.isEmpty()) {
            throw new BadRequestException("QUIZ_CANNOT_PUBLISH_WITHOUT_QUESTIONS");
        }
        for (QuizQuestion link : links) {
            Question question = questions.findById(link.getQuestionId())
                    .orElseThrow(() -> new NotFoundException("Question not found: " + link.getQuestionId()));
            validatePublishableQuestion(question, link);
        }
    }

    private void validatePublishableQuestion(Question question, QuizQuestion link) {
        if (!"ACTIVE".equalsIgnoreCase(question.getStatus())) {
            throw new BadRequestException("QUIZ_CANNOT_PUBLISH_WITH_INACTIVE_QUESTION: " + question.getId());
        }
        if (question.getStem() == null || question.getStem().isBlank()) {
            throw new BadRequestException("QUIZ_CANNOT_PUBLISH_WITH_BLANK_QUESTION: " + question.getId());
        }
        if (link.getPoints() == null || link.getPoints().compareTo(BigDecimal.ZERO) <= 0) {
            throw new BadRequestException("QUIZ_CANNOT_PUBLISH_WITH_NON_POSITIVE_POINTS: " + question.getId());
        }

        String type = question.getType();
        if (OPTION_QUESTION_TYPES.contains(type)) {
            List<QuestionOption> options = questionOptions.findByQuestionIdOrderByLabelAsc(question.getId());
            if (options.size() < 2) {
                throw new BadRequestException("QUIZ_CHOICE_QUESTION_NEEDS_OPTIONS");
            }
            long correctCount = options.stream().filter(QuestionOption::isCorrect).count();
            if (correctCount == 0) {
                throw new BadRequestException("QUIZ_CHOICE_QUESTION_NEEDS_CORRECT_OPTION");
            }
            if (!"MULTIPLE_RESPONSE".equals(type) && correctCount != 1) {
                throw new BadRequestException("QUIZ_SINGLE_CHOICE_ONLY_ONE_CORRECT_OPTION");
            }
            return;
        }

        if (!"ESSAY".equals(type) && (question.getCorrectAnswer() == null || question.getCorrectAnswer().isBlank())) {
            throw new BadRequestException("QUIZ_QUESTION_NEEDS_CORRECT_ANSWER");
        }
    }

    private String jsonOrNull(JsonNode node) {
        if (node == null || node.isNull() || node.isMissingNode()) {
            return null;
        }
        return toJson(node);
    }

    private QuizAttempt loadAttemptEntity(UUID attemptId) {
        return attempts.findById(attemptId)
                .orElseThrow(() -> new NotFoundException("Attempt not found: " + attemptId));
    }

    private void saveOutbox(UUID attemptId, QuizAttemptDto attempt, QuizDto quiz, BigDecimal score) {
        BigDecimal maxScore = quiz.questions().stream()
                .map(QuizQuestionDto::points)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        Map<String, Object> payload = Map.of(
                "eventId", UUID.randomUUID().toString(),
                "attemptId", attemptId.toString(),
                "quizId", quiz.id(),
                "courseId", quiz.courseId(),
                "studentId", attempt.studentId(),
                "attemptNo", attempt.attemptNo(),
                "score", score,
                "maxScore", maxScore,
                "gradedAt", Instant.now().toString());
        outboxEvents.save(new OutboxEvent(attemptId, "quiz-attempt", "quiz.attempt.graded", toJson(payload)));
    }

    private Instant computeDeadline(Quiz quiz, Instant startedAt) {
        Instant deadline = startedAt.plus(Duration.ofMinutes(quiz.getDurationMinutes()));
        if (quiz.getCloseAt() != null && quiz.getCloseAt().isBefore(deadline)) {
            return quiz.getCloseAt();
        }
        return deadline;
    }

    private JsonNode parseJson(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readTree(raw);
        } catch (Exception ex) {
            return null;
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }

    private record AttemptScore(int attemptNo, BigDecimal score, Instant submittedAt) {
    }

    private record UpsertQuestionOption(
            String label,
            String content,
            boolean correct,
            BigDecimal weight,
            String feedback) {
    }
}
