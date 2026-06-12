package edu.courseflow.discussion.mapper;

import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionCommentDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionThreadDto;
import edu.courseflow.discussion.model.DiscussionComment;
import edu.courseflow.discussion.model.DiscussionThread;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface DiscussionMapper {

    @Mapping(target = "comments", source = "comments")
    DiscussionThreadDto toDto(DiscussionThread thread, List<DiscussionCommentDto> comments);

    DiscussionCommentDto toDto(DiscussionComment comment);
}
