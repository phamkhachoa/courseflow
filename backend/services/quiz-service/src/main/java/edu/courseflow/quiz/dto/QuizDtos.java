package edu.courseflow.quiz.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * All quiz DTOs in one file. Question {@code type} is one of:
 * MULTIPLE_CHOICE, TRUE_FALSE, MULTIPLE_RESPONSE, SHORT_ANSWER, FILL_BLANK,
 * NUMERICAL, MATCHING, ESSAY.
 */
public final class QuizDtos {

    private QuizDtos() {
    }

    public record QuestionOptionDto(
            String id,
            String label,
            String content,
            BigDecimal weight,
            Boolean correct,
            String feedback) {
    }

    public record QuizQuestionDto(
            String id,
            String type,
            String stem,
            String difficulty,
            String status,
            BigDecimal points,
            int position,
            JsonNode correctAnswer,
            String feedback,
            List<QuestionOptionDto> options) {
    }

    public record QuizDto(
            String id,
            String courseId,
            String title,
            Instant openAt,
            Instant closeAt,
            int durationMinutes,
            int attemptsAllowed,
            boolean randomizeQuestions,
            boolean randomizeOptions,
            int gracePeriodSeconds,
            String scoringMethod,
            boolean timeLimitEnforced,
            boolean showCorrectAnswers,
            String status,
            List<QuizQuestionDto> questions) {
    }

    // ---- Admin authoring requests ----

    public record CreateQuizRequestDto(
            @NotNull UUID courseId,
            @NotBlank String title,
            Instant openAt,
            Instant closeAt,
            @Positive Integer durationMinutes,
            @Positive Integer attemptsAllowed,
            Boolean randomizeQuestions,
            Boolean randomizeOptions,
            @PositiveOrZero Integer gracePeriodSeconds,
            String scoringMethod,
            Boolean timeLimitEnforced,
            Boolean showCorrectAnswers,
            String status) {
    }

    public record UpdateQuizRequestDto(
            @NotBlank String title,
            Instant openAt,
            Instant closeAt,
            @Positive Integer durationMinutes,
            @Positive Integer attemptsAllowed,
            Boolean randomizeQuestions,
            Boolean randomizeOptions,
            @PositiveOrZero Integer gracePeriodSeconds,
            String scoringMethod,
            Boolean timeLimitEnforced,
            Boolean showCorrectAnswers,
            String status) {
    }

    public record UpsertQuestionOptionRequestDto(
            @NotBlank String label,
            @NotBlank String content,
            Boolean correct,
            BigDecimal weight,
            String feedback) {
    }

    public record UpsertQuizQuestionRequestDto(
            @NotBlank String type,
            @NotBlank String stem,
            String difficulty,
            @NotNull @Positive BigDecimal points,
            @Positive Integer position,
            JsonNode correctAnswer,
            String feedback,
            String status,
            @Valid List<UpsertQuestionOptionRequestDto> options) {
    }

    // ---- Student-facing (sanitized) views: never expose correct answers/feedback/correct flags. ----

    public record StudentQuestionOptionDto(
            String id,
            String label,
            String content) {
    }

    public record StudentQuizQuestionDto(
            String id,
            String type,
            String stem,
            BigDecimal points,
            int position,
            List<StudentQuestionOptionDto> options) {
    }

    public record StudentQuizDto(
            String id,
            String courseId,
            String title,
            Instant openAt,
            Instant closeAt,
            int durationMinutes,
            int attemptsAllowed,
            boolean randomizeQuestions,
            String scoringMethod,
            boolean timeLimitEnforced,
            boolean showCorrectAnswers,
            String status,
            List<StudentQuizQuestionDto> questions) {
    }

    public record QuizReadinessDto(
            String id,
            String courseId,
            String status) {
    }

    public record LearnerSourceStatusDto(
            String sourceType,
            String sourceId,
            String courseId,
            String title,
            String sourceStatus,
            Instant availableAt,
            Instant dueAt,
            Instant lockAt,
            String latestProgressStatus,
            String latestProgressId,
            int attemptsUsed,
            Integer attemptsAllowed,
            boolean completed,
            boolean overdue) {
    }

    // studentId is taken from the authenticated caller, never from the body.
    public record StartAttemptRequestDto() {
    }

    public record QuizAttemptDto(
            String id,
            String quizId,
            String studentId,
            int attemptNo,
            String status,
            BigDecimal score,
            Instant startedAt,
            Instant submittedAt,
            Instant deadlineAt,
            boolean autoSubmitted) {
    }

    /**
     * Returned when an attempt starts (or resumes): the attempt plus the frozen, possibly-shuffled
     * question set the student must answer. Questions come from the per-attempt snapshot, sanitized
     * to never leak the answer key.
     */
    public record StartAttemptResponseDto(
            QuizAttemptDto attempt,
            List<StudentQuizQuestionDto> questions) {
    }

    // Autosave of in-progress answers (no submission). Lets partial work survive a timeout so the
    // grace-period auto-submit grades what the student actually answered.
    public record SaveAnswersRequestDto(
            @NotNull Map<String, JsonNode> answers) {
    }

    public record QuizAttemptAnswerDto(
            String questionId,
            JsonNode answer,
            BigDecimal autoScore,
            BigDecimal manualScore,
            BigDecimal totalScore,
            String manualFeedback,
            String graderId,
            Instant gradedAt) {
    }

    public record QuizAttemptDetailDto(
            QuizAttemptDto attempt,
            List<QuizAttemptAnswerDto> answers) {
    }

    public record SubmitAttemptRequestDto(
            @NotNull Map<String, JsonNode> answers) {
    }

    // graderId is taken from the authenticated instructor/admin, never from the body.
    public record ManualGradeAnswerRequestDto(
            @NotNull BigDecimal score,
            String feedback) {
    }

    public record EffectiveScoreDto(
            String quizId,
            String studentId,
            String scoringMethod,
            BigDecimal effectiveScore,
            int attemptsCounted) {
    }
}
