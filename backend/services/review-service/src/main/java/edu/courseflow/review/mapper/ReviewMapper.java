package edu.courseflow.review.mapper;

import edu.courseflow.review.dto.ReviewDtos.RatingSummaryDto;
import edu.courseflow.review.dto.ReviewDtos.ReviewDto;
import edu.courseflow.review.model.CourseRatingSummary;
import edu.courseflow.review.model.CourseReview;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface ReviewMapper {

    ReviewDto toDto(CourseReview review);

    RatingSummaryDto toDto(CourseRatingSummary summary);
}
