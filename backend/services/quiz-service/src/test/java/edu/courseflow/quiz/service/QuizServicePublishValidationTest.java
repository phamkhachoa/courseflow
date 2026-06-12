package edu.courseflow.quiz.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.quiz.dto.QuizDtos.QuestionOptionDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizQuestionDto;
import edu.courseflow.quiz.dto.QuizDtos.UpdateQuizRequestDto;
import edu.courseflow.quiz.mapper.QuizMapper;
import edu.courseflow.quiz.model.Question;
import edu.courseflow.quiz.model.QuestionOption;
import edu.courseflow.quiz.model.Quiz;
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
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class QuizServicePublishValidationTest {

    private static final UUID QUIZ_ID = UUID.fromString("b3000000-0000-0000-0000-000000000001");
    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID QUESTION_ID = UUID.fromString("b2000000-0000-0000-0000-000000000001");

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
    void updateQuizRejectsPublishWithoutQuestions() {
        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(draftQuiz()));
        when(quizQuestions.findByQuizIdOrderByPositionAsc(QUIZ_ID)).thenReturn(List.of());

        assertThrows(BadRequestException.class, () -> service.updateQuiz(QUIZ_ID, publishRequest()));

        verify(quizzes, never()).save(any(Quiz.class));
    }

    @Test
    void updateQuizRejectsSingleChoicePublishWithoutCorrectOption() {
        QuizQuestion link = quizQuestion(BigDecimal.TEN);
        Question question = activeQuestion("MULTIPLE_CHOICE", null);

        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(draftQuiz()));
        when(quizQuestions.findByQuizIdOrderByPositionAsc(QUIZ_ID)).thenReturn(List.of(link));
        when(questions.findById(QUESTION_ID)).thenReturn(Optional.of(question));
        when(questionOptions.findByQuestionIdOrderByLabelAsc(QUESTION_ID)).thenReturn(List.of(
                option("A", false),
                option("B", false)));

        assertThrows(BadRequestException.class, () -> service.updateQuiz(QUIZ_ID, publishRequest()));

        verify(quizzes, never()).save(any(Quiz.class));
    }

    @Test
    void updateQuizRejectsAutoGradedQuestionWithoutCorrectAnswer() {
        QuizQuestion link = quizQuestion(BigDecimal.TEN);
        Question question = activeQuestion("SHORT_ANSWER", null);

        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(draftQuiz()));
        when(quizQuestions.findByQuizIdOrderByPositionAsc(QUIZ_ID)).thenReturn(List.of(link));
        when(questions.findById(QUESTION_ID)).thenReturn(Optional.of(question));

        assertThrows(BadRequestException.class, () -> service.updateQuiz(QUIZ_ID, publishRequest()));

        verify(quizzes, never()).save(any(Quiz.class));
    }

    @Test
    void updateQuizPublishesWhenQuestionsAreValid() {
        Quiz quiz = draftQuiz();
        QuizQuestion link = quizQuestion(BigDecimal.TEN);
        Question question = activeQuestion("MULTIPLE_CHOICE", null);
        List<QuestionOption> options = List.of(option("A", true), option("B", false));

        when(quizzes.findById(QUIZ_ID)).thenReturn(Optional.of(quiz));
        when(quizQuestions.findByQuizIdOrderByPositionAsc(QUIZ_ID)).thenReturn(List.of(link));
        when(questions.findById(QUESTION_ID)).thenReturn(Optional.of(question));
        when(questionOptions.findByQuestionIdOrderByLabelAsc(QUESTION_ID)).thenReturn(options);
        when(quizzes.save(any(Quiz.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(mapper.toDto(any(QuestionOption.class))).thenAnswer(invocation -> {
            QuestionOption option = invocation.getArgument(0);
            return new QuestionOptionDto(
                    option.getId().toString(),
                    option.getLabel(),
                    option.getContent(),
                    option.getWeight(),
                    option.isCorrect(),
                    option.getFeedback());
        });
        when(mapper.toQuestionDto(any(Question.class), any(QuizQuestion.class), any(), anyList()))
                .thenReturn(new QuizQuestionDto(
                        QUESTION_ID.toString(),
                        "MULTIPLE_CHOICE",
                        "Valid question?",
                        "EASY",
                        "ACTIVE",
                        BigDecimal.TEN,
                        1,
                        null,
                        null,
                        List.of(new QuestionOptionDto(UUID.randomUUID().toString(), "A", "Yes", BigDecimal.ONE, true, null))));
        when(mapper.toDto(any(Quiz.class), anyList())).thenAnswer(invocation -> {
            Quiz saved = invocation.getArgument(0);
            return new QuizDto(
                    saved.getId().toString(),
                    saved.getCourseId().toString(),
                    saved.getTitle(),
                    saved.getOpenAt(),
                    saved.getCloseAt(),
                    saved.getDurationMinutes(),
                    saved.getAttemptsAllowed(),
                    saved.isRandomizeQuestions(),
                    saved.isRandomizeOptions(),
                    saved.getGracePeriodSeconds(),
                    saved.getScoringMethod(),
                    saved.isTimeLimitEnforced(),
                    saved.isShowCorrectAnswers(),
                    saved.getStatus(),
                    invocation.getArgument(1));
        });

        QuizDto result = service.updateQuiz(QUIZ_ID, publishRequest());

        assertThat(result.status()).isEqualTo("PUBLISHED");
        verify(quizzes).save(any(Quiz.class));
    }

    private static UpdateQuizRequestDto publishRequest() {
        return new UpdateQuizRequestDto(
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

    private static Quiz draftQuiz() {
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
                "DRAFT");
    }

    private static QuizQuestion quizQuestion(BigDecimal points) {
        return new QuizQuestion(UUID.randomUUID(), QUIZ_ID, QUESTION_ID, points, 1);
    }

    private static Question activeQuestion(String type, String correctAnswer) {
        return new Question(
                QUESTION_ID,
                UUID.randomUUID(),
                type,
                "Valid question?",
                "EASY",
                BigDecimal.TEN,
                "ACTIVE",
                correctAnswer,
                null);
    }

    private static QuestionOption option(String label, boolean correct) {
        return new QuestionOption(
                UUID.randomUUID(),
                QUESTION_ID,
                label,
                label.equals("A") ? "Yes" : "No",
                correct,
                correct ? BigDecimal.ONE : BigDecimal.ZERO,
                null);
    }
}
