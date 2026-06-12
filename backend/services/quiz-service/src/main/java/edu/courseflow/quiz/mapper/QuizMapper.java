package edu.courseflow.quiz.mapper;

import com.fasterxml.jackson.databind.JsonNode;
import edu.courseflow.quiz.dto.QuizDtos.QuestionOptionDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptAnswerDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizAttemptDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizDto;
import edu.courseflow.quiz.dto.QuizDtos.QuizQuestionDto;
import edu.courseflow.quiz.dto.QuizDtos.StudentQuestionOptionDto;
import edu.courseflow.quiz.dto.QuizDtos.StudentQuizDto;
import edu.courseflow.quiz.dto.QuizDtos.StudentQuizQuestionDto;
import edu.courseflow.quiz.model.Question;
import edu.courseflow.quiz.model.QuestionOption;
import edu.courseflow.quiz.model.Quiz;
import edu.courseflow.quiz.model.QuizAnswer;
import edu.courseflow.quiz.model.QuizAttempt;
import edu.courseflow.quiz.model.QuizQuestion;
import java.math.BigDecimal;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface QuizMapper {

    @Mapping(target = "questions", source = "questions")
    QuizDto toDto(Quiz quiz, List<QuizQuestionDto> questions);

    QuizAttemptDto toDto(QuizAttempt attempt);

    QuestionOptionDto toDto(QuestionOption option);

    @Mapping(target = "id", source = "question.id")
    @Mapping(target = "type", source = "question.type")
    @Mapping(target = "stem", source = "question.stem")
    @Mapping(target = "difficulty", source = "question.difficulty")
    @Mapping(target = "status", source = "question.status")
    @Mapping(target = "points", source = "link.points")
    @Mapping(target = "position", source = "link.position")
    @Mapping(target = "correctAnswer", source = "correctAnswer")
    @Mapping(target = "feedback", source = "question.feedback")
    @Mapping(target = "options", source = "options")
    QuizQuestionDto toQuestionDto(
            Question question, QuizQuestion link, JsonNode correctAnswer, List<QuestionOptionDto> options);

    @Mapping(target = "answer", source = "answer")
    @Mapping(target = "totalScore", source = "totalScore")
    QuizAttemptAnswerDto toAnswerDto(QuizAnswer quizAnswer, JsonNode answer, BigDecimal totalScore);

    @Mapping(target = "questions", source = "questions")
    StudentQuizDto toStudentView(QuizDto quiz);

    @Mapping(target = "options", source = "options")
    StudentQuizQuestionDto toStudentQuestion(QuizQuestionDto question);

    StudentQuestionOptionDto toStudentOption(QuestionOptionDto option);
}
