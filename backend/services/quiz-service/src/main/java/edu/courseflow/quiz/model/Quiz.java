package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "quizzes")
public class Quiz {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(name = "open_at")
    private Instant openAt;

    @Column(name = "close_at")
    private Instant closeAt;

    @Column(name = "duration_minutes", nullable = false)
    private int durationMinutes;

    @Column(name = "attempts_allowed", nullable = false)
    private int attemptsAllowed = 1;

    @Column(name = "randomize_questions", nullable = false)
    private boolean randomizeQuestions;

    @Column(name = "randomize_options", nullable = false)
    private boolean randomizeOptions;

    @Column(name = "grace_period_seconds", nullable = false)
    private int gracePeriodSeconds = 60;

    @Column(name = "scoring_method", nullable = false, length = 20)
    private String scoringMethod = "HIGHEST";

    @Column(name = "time_limit_enforced", nullable = false)
    private boolean timeLimitEnforced;

    @Column(name = "show_correct_answers", nullable = false)
    private boolean showCorrectAnswers = true;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    protected Quiz() {
    }

    public Quiz(UUID id, UUID courseId, String title, Instant openAt, Instant closeAt, int durationMinutes,
            int attemptsAllowed, boolean randomizeQuestions, boolean randomizeOptions, int gracePeriodSeconds,
            String scoringMethod, boolean timeLimitEnforced, boolean showCorrectAnswers, String status) {
        this.id = id;
        this.courseId = courseId;
        update(title, openAt, closeAt, durationMinutes, attemptsAllowed, randomizeQuestions, randomizeOptions,
                gracePeriodSeconds, scoringMethod, timeLimitEnforced, showCorrectAnswers, status);
    }

    public void update(String title, Instant openAt, Instant closeAt, int durationMinutes, int attemptsAllowed,
            boolean randomizeQuestions, boolean randomizeOptions, int gracePeriodSeconds, String scoringMethod,
            boolean timeLimitEnforced, boolean showCorrectAnswers, String status) {
        this.title = title;
        this.openAt = openAt;
        this.closeAt = closeAt;
        this.durationMinutes = durationMinutes;
        this.attemptsAllowed = attemptsAllowed;
        this.randomizeQuestions = randomizeQuestions;
        this.randomizeOptions = randomizeOptions;
        this.gracePeriodSeconds = gracePeriodSeconds;
        this.scoringMethod = scoringMethod;
        this.timeLimitEnforced = timeLimitEnforced;
        this.showCorrectAnswers = showCorrectAnswers;
        this.status = status;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getTitle() { return title; }
    public Instant getOpenAt() { return openAt; }
    public Instant getCloseAt() { return closeAt; }
    public int getDurationMinutes() { return durationMinutes; }
    public int getAttemptsAllowed() { return attemptsAllowed; }
    public boolean isRandomizeQuestions() { return randomizeQuestions; }
    public boolean isRandomizeOptions() { return randomizeOptions; }
    public int getGracePeriodSeconds() { return gracePeriodSeconds; }
    public String getScoringMethod() { return scoringMethod; }
    public boolean isTimeLimitEnforced() { return timeLimitEnforced; }
    public boolean isShowCorrectAnswers() { return showCorrectAnswers; }
    public String getStatus() { return status; }
}
