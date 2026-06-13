package edu.courseflow.quiz.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
import edu.courseflow.quiz.service.LearningAccessClient;
import edu.courseflow.quiz.service.QuizService;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class QuizControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID QUIZ_ID = UUID.fromString("b3000000-0000-0000-0000-000000000001");
    private static final UUID ATTEMPT_ID = UUID.fromString("c3000000-0000-0000-0000-000000000001");

    @Mock
    private QuizService quizzes;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private LearningAccessClient learningAccess;

    private QuizController controller;

    @BeforeEach
    void setUp() {
        controller = new QuizController(quizzes, courseAccess, learningAccess);
    }

    @Test
    void listMyAttemptsRequiresCourseAccessForQuizCourse() {
        CurrentUser student = student();
        QuizAttemptDto attempt = attempt();
        when(quizzes.quizCourseId(QUIZ_ID)).thenReturn(COURSE_ID);
        when(quizzes.listMyAttempts(QUIZ_ID, "4")).thenReturn(List.of(attempt));

        List<QuizAttemptDto> result = controller.listMyAttempts(QUIZ_ID, student);

        assertThat(result).containsExactly(attempt);
        verify(courseAccess).requireCourseAccess(student, COURSE_ID);
        verify(quizzes).listMyAttempts(QUIZ_ID, "4");
    }

    @Test
    void startAttemptRequiresLearningAccessPolicy() {
        CurrentUser student = student();
        when(quizzes.quizCourseId(QUIZ_ID)).thenReturn(COURSE_ID);
        doThrow(new ForbiddenException("PREREQUISITE_MODULE_INCOMPLETE"))
                .when(learningAccess).requireSourceAccess(COURSE_ID, "4", "QUIZ", QUIZ_ID);

        ForbiddenException ex = assertThrows(ForbiddenException.class,
                () -> controller.startAttempt(QUIZ_ID, null, student));

        assertThat(ex.getMessage()).contains("PREREQUISITE_MODULE_INCOMPLETE");
        verify(courseAccess).requireCourseAccess(student, COURSE_ID);
        verify(quizzes, never()).startAttempt(QUIZ_ID, "4");
    }

    private static CurrentUser student() {
        return new CurrentUser(4L, "student@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }

    private static QuizAttemptDto attempt() {
        Instant startedAt = Instant.parse("2026-06-12T00:00:00Z");
        return new QuizAttemptDto(
                ATTEMPT_ID.toString(),
                QUIZ_ID.toString(),
                "4",
                1,
                "GRADED",
                null,
                startedAt,
                startedAt.plusSeconds(600),
                startedAt.plusSeconds(1200),
                false);
    }
}
