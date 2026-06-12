package edu.courseflow.peerreview.mapper;

import edu.courseflow.peerreview.dto.PeerReviewResultDto;
import edu.courseflow.peerreview.dto.PeerReviewSettingDto;
import edu.courseflow.peerreview.dto.ReviewAssignmentDto;
import edu.courseflow.peerreview.dto.ReviewSubmissionDto;
import edu.courseflow.peerreview.model.PeerReviewResult;
import edu.courseflow.peerreview.model.PeerReviewSetting;
import edu.courseflow.peerreview.model.ReviewAssignment;
import edu.courseflow.peerreview.model.ReviewSubmission;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface PeerReviewMapper {

    PeerReviewSettingDto toDto(PeerReviewSetting setting);

    ReviewAssignmentDto toDto(ReviewAssignment assignment);

    ReviewSubmissionDto toDto(ReviewSubmission submission);

    PeerReviewResultDto toDto(PeerReviewResult result);
}
