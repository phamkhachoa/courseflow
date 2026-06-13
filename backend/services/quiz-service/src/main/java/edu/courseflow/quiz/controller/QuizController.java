package edu.courseflow.quiz.controller;

import edu.courseflow.quiz.dto.QuizDtos.EffectiveScoreDto;
import edu.courseflow.quiz.dto.QuizDtos.CreateQuizRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.ManualGradeAnswerRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDetailDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizReadinessDto;
import edu.courseflow.quiz.dto.QuizDtos.SaveAnswersRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.StartAttemptResponseDto;
import edu.courseflow.quiz.dto.QuizDtos.StartAttemptRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.SubmitAttemptRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.UpdateQuizRequestDto;
import edu.courseflow.quiz.dto.QuizDtos.UpsertQuizQuestionRequestDto;
import edu.courseflow.quiz.service.QuizService;
import edu.courseflow.quiz.web.Authz;
import edu.courseflow.quiz.web.ForbiddenException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/quizzes")
public class QuizController {

    private final QuizService quizzes;
    private final CourseAccessClient courseAccess;
    private final String serviceToken;

    public QuizController(QuizService quizzes,
            CourseAccessClient courseAccess,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.quizzes = quizzes;
        this.courseAccess = courseAccess;
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    @GetMapping
    public List<?> listByCourse(@RequestParam UUID courseId, CurrentUser user) {
        Authz.callerId(user);
        List<QuizDto> rows = quizzes.listCourseQuizzes(courseId);
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
            return rows;
        }
        courseAccess.requireCourseAccess(user, courseId);
        return rows.stream()
                .filter(quiz -> "PUBLISHED".equals(quiz.status()))
                .map(quizzes::toStudentView)
                .toList();
    }

    @PostMapping
    public QuizDto createQuiz(@Valid @RequestBody CreateQuizRequestDto request, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, request.courseId());
        return quizzes.createQuiz(request);
    }

    @PutMapping("/{quizId}")
    public QuizDto updateQuiz(@PathVariable UUID quizId,
            @Valid @RequestBody UpdateQuizRequestDto request,
            CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.updateQuiz(quizId, request);
    }

    @GetMapping("/{quizId}/readiness")
    public QuizReadinessDto readiness(@PathVariable UUID quizId,
            @RequestHeader(value = CourseAccessClient.SERVICE_TOKEN_HEADER, required = false) String token) {
        requireServiceToken(token);
        return quizzes.readiness(quizId);
    }

    @GetMapping("/{quizId}/attempts")
    public List<QuizAttemptDto> listAttempts(@PathVariable UUID quizId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.listAttempts(quizId);
    }

    @GetMapping("/{quizId}/attempts/me")
    public List<QuizAttemptDto> listMyAttempts(@PathVariable UUID quizId, CurrentUser user) {
        return quizzes.listMyAttempts(quizId, Authz.callerId(user));
    }

    @PostMapping("/{quizId}/questions")
    public QuizDto createQuestion(@PathVariable UUID quizId,
            @Valid @RequestBody UpsertQuizQuestionRequestDto request,
            CurrentUser user) {
        Authz.requireStaff(user);
        courseAccess.requireCourseStaffAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.createQuestion(quizId, Authz.callerId(user), request);
    }

    @PutMapping("/{quizId}/questions/{questionId}")
    public QuizDto updateQuestion(@PathVariable UUID quizId,
            @PathVariable UUID questionId,
            @Valid @RequestBody UpsertQuizQuestionRequestDto request,
            CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.updateQuestion(quizId, questionId, request);
    }

    @DeleteMapping("/{quizId}/questions/{questionId}")
    public QuizDto removeQuestion(@PathVariable UUID quizId,
            @PathVariable UUID questionId,
            CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.removeQuestion(quizId, questionId);
    }

    /**
     * Returns the quiz. Staff (INSTRUCTOR/ADMIN) always get the full view including correct answers.
     * Students get a sanitized view with no answer key (closes P0-3); the full view is only revealed
     * to a student once they have a GRADED attempt AND the quiz has {@code show_correct_answers=true}.
     */
    @GetMapping("/{quizId}")
    public Object getQuiz(@PathVariable UUID quizId, CurrentUser user) {
        Authz.callerId(user);
        QuizDto quiz = quizzes.getQuiz(quizId);
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, UUID.fromString(quiz.courseId()));
            return quiz;
        }
        courseAccess.requireCourseAccess(user, UUID.fromString(quiz.courseId()));
        if (!"PUBLISHED".equals(quiz.status())) {
            throw new ForbiddenException("QUIZ_NOT_PUBLISHED");
        }
        boolean reveal = quizzes.canRevealCorrectAnswers(quiz, Authz.callerId(user));
        return reveal ? quiz : quizzes.toStudentView(quiz);
    }

    @PostMapping("/{quizId}/attempts")
    public StartAttemptResponseDto startAttempt(@PathVariable UUID quizId,
            @Valid @RequestBody(required = false) StartAttemptRequestDto request, CurrentUser user) {
        // studentId is the authenticated caller, never trusted from the body.
        courseAccess.requireCourseAccess(user, quizzes.quizCourseId(quizId));
        return quizzes.startAttempt(quizId, Authz.callerId(user));
    }

    @PostMapping("/attempts/{attemptId}/submit")
    public QuizAttemptDto submitAttempt(@PathVariable UUID attemptId,
            @Valid @RequestBody SubmitAttemptRequestDto request, CurrentUser user) {
        // Only the student who owns the attempt may submit it (staff override allowed).
        requireSelfOrScopedStaff(user, quizzes.attemptStudentId(attemptId), quizzes.attemptCourseId(attemptId));
        return quizzes.submitAttempt(attemptId, request);
    }

    @PutMapping("/attempts/{attemptId}/answers")
    public QuizAttemptDto saveAnswers(@PathVariable UUID attemptId,
            @Valid @RequestBody SaveAnswersRequestDto request, CurrentUser user) {
        // Save draft answers only for the owning student, with staff override for support.
        requireSelfOrScopedStaff(user, quizzes.attemptStudentId(attemptId), quizzes.attemptCourseId(attemptId));
        return quizzes.saveAnswers(attemptId, request);
    }

    @GetMapping("/attempts/{attemptId}")
    public QuizAttemptDetailDto getAttempt(@PathVariable UUID attemptId, CurrentUser user) {
        // A student may only read their own attempt; staff may read any.
        String studentId = quizzes.attemptStudentId(attemptId);
        requireSelfOrScopedStaff(user, studentId, quizzes.attemptCourseId(attemptId));
        if (Authz.isStaff(user)) {
            return quizzes.getAttemptDetail(attemptId);
        }
        QuizAttemptDetailDto detail = quizzes.getAttemptDetail(attemptId);
        QuizDto quiz = quizzes.getQuiz(UUID.fromString(detail.attempt().quizId()));
        return quizzes.getAttemptDetailForStudent(attemptId, quizzes.canRevealCorrectAnswers(quiz, studentId));
    }

    /** Manual grading for ESSAY (or override of any other question type). Instructor/admin only. */
    @PostMapping("/attempts/{attemptId}/answers/{questionId}/grade")
    public QuizAttemptDto manualGrade(@PathVariable UUID attemptId,
            @PathVariable UUID questionId,
            @Valid @RequestBody ManualGradeAnswerRequestDto request, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, quizzes.attemptCourseId(attemptId));
        return quizzes.manualGradeAnswer(attemptId, questionId, Authz.callerId(user), request);
    }

    /**
     * Effective score for a student across attempts, per the quiz's scoring_method.
     */
    @GetMapping("/{quizId}/students/{studentId}/score")
    public EffectiveScoreDto effectiveScore(@PathVariable UUID quizId, @PathVariable String studentId,
            CurrentUser user) {
        // A student may only read their own score; staff may read any.
        requireSelfOrScopedStaff(user, studentId, quizzes.quizCourseId(quizId));
        return quizzes.effectiveScore(quizId, studentId);
    }

    private void requireSelfOrScopedStaff(CurrentUser user, String ownerStudentId, UUID courseId) {
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
            return;
        }
        Authz.requireSelfOrStaff(user, ownerStudentId);
        courseAccess.requireCourseAccess(user, courseId);
    }

    private void requireServiceToken(String token) {
        if (serviceToken.isBlank() || token == null || !serviceToken.equals(token.trim())) {
            throw new ForbiddenException("Service token required");
        }
    }
}
