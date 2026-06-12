package edu.courseflow.portfolio.mapper;

import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDetailDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDetailDto.EvaluationDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.AddLearningEvidenceRequestDto;
import edu.courseflow.portfolio.model.LearningEvidence;
import edu.courseflow.portfolio.model.LearningEvidence.EvidenceEvaluation;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.AfterMapping;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.MappingTarget;

@Mapper(config = CourseFlowMapperConfig.class)
public interface PortfolioMapper {

    LearningEvidenceDto toDto(LearningEvidence evidence);

    EvaluationDto toDto(EvidenceEvaluation evaluation);

    @Mapping(target = "evaluations", source = "evaluations")
    LearningEvidenceDetailDto toDetailDto(LearningEvidence evidence, List<EvaluationDto> evaluations);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "studentId", source = "studentId")
    @Mapping(target = "courseId", source = "request.courseId")
    @Mapping(target = "title", source = "request.title")
    @Mapping(target = "evidenceType", source = "request.evidenceType")
    @Mapping(target = "sourceType", source = "request.sourceType")
    @Mapping(target = "sourceId", source = "request.sourceId")
    @Mapping(target = "reflection", source = "request.reflection")
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "tags", ignore = true)
    @Mapping(target = "visibility", ignore = true)
    @Mapping(target = "mediaUrls", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "evaluations", ignore = true)
    LearningEvidence toEntity(String studentId, AddLearningEvidenceRequestDto request);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "studentId", source = "studentId")
    @Mapping(target = "courseId", source = "courseId")
    @Mapping(target = "title", expression = "java(\"Assignment submission \" + assignmentId)")
    @Mapping(target = "evidenceType", constant = "ASSIGNMENT")
    @Mapping(target = "sourceType", constant = "ASSIGNMENT_SUBMISSION")
    @Mapping(target = "sourceId", source = "submissionId")
    @Mapping(target = "reflection", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "tags", ignore = true)
    @Mapping(target = "visibility", ignore = true)
    @Mapping(target = "mediaUrls", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "evaluations", ignore = true)
    LearningEvidence toSubmissionEvidence(String studentId, String courseId, String assignmentId, String submissionId);

    @AfterMapping
    default void initializeEvidence(@MappingTarget LearningEvidence evidence) {
        Instant now = Instant.now();
        if (evidence.getCreatedAt() == null) {
            evidence.setCreatedAt(now);
        }
        if (evidence.getUpdatedAt() == null) {
            evidence.setUpdatedAt(now);
        }
        if (evidence.getVisibility() == null) {
            evidence.setVisibility("PRIVATE");
        }
        if (evidence.getEvaluations() == null) {
            evidence.setEvaluations(new ArrayList<>());
        }
        if (evidence.getTags() == null) {
            evidence.setTags(new ArrayList<>());
        }
        if (evidence.getMediaUrls() == null) {
            evidence.setMediaUrls(new ArrayList<>());
        }
    }
}
