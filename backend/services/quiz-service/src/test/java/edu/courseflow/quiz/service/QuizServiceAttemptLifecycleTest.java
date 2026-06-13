package edu.courseflow.quiz.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizQuestionDto;
import edu.courseflow.quiz.dto.QuizDtos.StartAttemptResponseDto;
import edu.courseflow.quiz.mapper.QuizMapper;
import edu.courseflow.quiz.model.Quiz;
import edu.courseflow.quiz.model.QuizAttempt;
import edu.courseflow.quiz.repository.OutboxEventRepository;
import edu.courseflow.quiz.repository.QuestionBankRepository;
import edu.courseflow.quiz.repository.QuestionOptionRepository;
import edu.courseflow.quiz.repository.QuestionRepository;
import edu.courseflow.quiz.repository.QuizAnswerRepository;
import edu.courseflow.quiz.repository.QuizAttemptRepository;
import edu.courseflow.quiz.repository.QuizQuestionRepository;
import edu.courseflow.quiz.repository.QuizRepository;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class QuizServiceAttemptLifecycleTest {

    private static final UUID QUIZ_ID = UUID.fromString("b3000000-0000-0000-0000-000000000001");
    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final String STUDENT_ID = "4";

    @Mock
    private QuizRepository quizzes;
    @Mock
    private QuestionBankRepository questionBanks;
    @Mock
    private QuizQuestionRepository quizQuestions;
    @Mock
    private QuestionRepository questions;
    @Mock
    private QuestionOptionRepository questionOptions;
    @Mock
    private QuizAttemptRepository attempts;
    @Mock
    private QuizAnswerRepository answers;
    @Mock
    private OutboxEventRepository outboxEvents;
    @Mock
    private QuizMapper mapper;

    private QuizService service;

    @BeforeEach
    void setUp() {
        service = new QuizService(
                quizzes,
                questionBanks,
                quizQuestions,
                questions,
                questionOptions,
                attempts,
                answers,
                outboxEvents,
                mapper,
                new ObjectMapper());
    }

    @Test
    void startAttemptReturnsExistingInProgressAttempt() {
        QuizAttempt existing = attempt(UUID.fromString("c3000000-0000-0000-0000-000000000001"), 1);
        existing.setQuestionsSnapshot("[]");

        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(publishedQuiz()));
        when(attempts.findFirstByQuizIdAndStudentIdAndStatusInOrderByStartedAtDesc(
                eq(QUIZ_ID), eq(STUDENT_ID), org.mockito.ArgumentMatchers.<Collection<String>>any()))
                .thenReturn(Optional.of(existing));
        when(mapper.toDto(existing)).thenReturn(toDto(existing));

        StartAttemptResponseDto result = service.startAttempt(QUIZ_ID, STUDENT_ID);

        assertThat(result.attempt().id()).isEqualTo(existing.getId().toString());
        verify(attempts, never()).nextAttemptNo(QUIZ_ID, STUDENT_ID);
        verify(attempts, never()).save(any(QuizAttempt.class));
    }

    @Test
    void startAttemptCreatesNewAttemptWhenNoAttemptIsOpen() {
        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(publishedQuiz()));
        when(attempts.findFirstByQuizIdAndStudentIdAndStatusInOrderByStartedAtDesc(
                eq(QUIZ_ID), eq(STUDENT_ID), org.mockito.ArgumentMatchers.<Collection<String>>any()))
                .thenReturn(Optional.empty());
        when(attempts.nextAttemptNo(QUIZ_ID, STUDENT_ID)).thenReturn(2);
        when(attempts.save(any(QuizAttempt.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(mapper.toDto(any(QuizAttempt.class))).thenAnswer(invocation -> toDto(invocation.getArgument(0)));
        when(mapper.toDto(any(Quiz.class), org.mockito.ArgumentMatchers.<List<QuizQuestionDto>>any()))
                .thenAnswer(invocation -> toQuizDto(invocation.getArgument(0), invocation.getArgument(1)));

        StartAttemptResponseDto result = service.startAttempt(QUIZ_ID, STUDENT_ID);

        assertThat(result.attempt().quizId()).isEqualTo(QUIZ_ID.toString());
        assertThat(result.attempt().studentId()).isEqualTo(STUDENT_ID);
        assertThat(result.attempt().attemptNo()).isEqualTo(2);
        assertThat(result.attempt().status()).isEqualTo("IN_PROGRESS");
        verify(attempts, times(2)).save(any(QuizAttempt.class));
    }

    @Test
    void learnerStatusesExposeOverdueOpenAttemptDeadline() {
        Instant startedAt = Instant.parse("2000-01-01T00:00:00Z");
        Instant deadlineAt = Instant.parse("2000-01-01T00:20:00Z");
        QuizAttempt openAttempt = new QuizAttempt(
                UUID.fromString("c3000000-0000-0000-0000-000000000002"),
                QUIZ_ID,
                STUDENT_ID,
                1,
                startedAt,
                deadlineAt);
        when(quizzes.findByCourseIdOrderByTitleAsc(COURSE_ID)).thenReturn(List.of(publishedQuiz()));
        when(attempts.findByQuizIdInAndStudentIdOrderByStartedAtDesc(List.of(QUIZ_ID), STUDENT_ID))
                .thenReturn(List.of(openAttempt));

        var result = service.learnerStatuses(COURSE_ID, STUDENT_ID, List.of(QUIZ_ID));

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().sourceStatus()).isEqualTo("OVERDUE");
        assertThat(result.getFirst().latestProgressStatus()).isEqualTo("IN_PROGRESS");
        assertThat(result.getFirst().dueAt()).isEqualTo(deadlineAt);
        assertThat(result.getFirst().attemptsUsed()).isEqualTo(1);
    }

    private static Quiz publishedQuiz() {
        return new Quiz(
                QUIZ_ID,
                COURSE_ID,
                "Midterm quiz",
                null,
                null,
                20,
                2,
                true,
                true,
                60,
                "HIGHEST",
                true,
                true,
                "PUBLISHED");
    }

    private static QuizAttempt attempt(UUID attemptId, int attemptNo) {
        Instant startedAt = Instant.parse("2026-06-12T00:00:00Z");
        return new QuizAttempt(
                attemptId,
                QUIZ_ID,
                STUDENT_ID,
                attemptNo,
                startedAt,
                startedAt.plusSeconds(1200));
    }

    private static QuizAttemptDto toDto(QuizAttempt attempt) {
        return new QuizAttemptDto(
                attempt.getId().toString(),
                attempt.getQuizId().toString(),
                attempt.getStudentId(),
                attempt.getAttemptNo(),
                attempt.getStatus(),
                attempt.getScore(),
                attempt.getStartedAt(),
                attempt.getSubmittedAt(),
                attempt.getDeadlineAt(),
                attempt.isAutoSubmitted());
    }

    private static QuizDto toQuizDto(Quiz quiz, List<QuizQuestionDto> questions) {
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
}
