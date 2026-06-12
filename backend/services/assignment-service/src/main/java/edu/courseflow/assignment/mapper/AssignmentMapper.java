package edu.courseflow.assignment.mapper;

import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricCriterionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionAttachmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.model.Assignment;
import edu.courseflow.assignment.model.AssignmentRubric;
import edu.courseflow.assignment.model.AssignmentRubricCriterion;
import edu.courseflow.assignment.model.Submission;
import edu.courseflow.assignment.model.SubmissionAttachment;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface AssignmentMapper {

    AssignmentDto toDto(Assignment assignment);

    SubmissionAttachmentDto toDto(SubmissionAttachment attachment);

    @Mapping(target = "isLate", expression = "java(submission.isLate())")
    @Mapping(target = "attachments", source = "attachments")
    SubmissionDto toDto(Submission submission, List<SubmissionAttachmentDto> attachments);

    RubricCriterionDto toDto(AssignmentRubricCriterion criterion);

    @Mapping(target = "criteria", source = "criteria")
    RubricDto toDto(AssignmentRubric rubric, List<RubricCriterionDto> criteria);
}
