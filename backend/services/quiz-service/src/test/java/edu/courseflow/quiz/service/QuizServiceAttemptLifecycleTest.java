package edu.courseflow.quiz.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
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

        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(publishedQuiz()));
        when(attempts.findFirstByQuizIdAndStudentIdAndStatusInOrderByStartedAtDesc(
                eq(QUIZ_ID), eq(STUDENT_ID), org.mockito.ArgumentMatchers.<Collection<String>>any()))
                .thenReturn(Optional.of(existing));
        when(mapper.toDto(existing)).thenReturn(toDto(existing));

        QuizAttemptDto result = service.startAttempt(QUIZ_ID, STUDENT_ID);

        assertThat(result.id()).isEqualTo(existing.getId().toString());
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

        QuizAttemptDto result = service.startAttempt(QUIZ_ID, STUDENT_ID);

        assertThat(result.quizId()).isEqualTo(QUIZ_ID.toString());
        assertThat(result.studentId()).isEqualTo(STUDENT_ID);
        assertThat(result.attemptNo()).isEqualTo(2);
        assertThat(result.status()).isEqualTo("IN_PROGRESS");
        verify(attempts).save(any(QuizAttempt.class));
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
}
