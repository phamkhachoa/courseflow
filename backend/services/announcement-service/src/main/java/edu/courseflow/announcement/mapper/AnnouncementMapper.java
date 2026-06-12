package edu.courseflow.announcement.mapper;

import edu.courseflow.announcement.dto.AnnouncementDtos.AnnouncementDto;
import edu.courseflow.announcement.model.Announcement;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface AnnouncementMapper {

    AnnouncementDto toDto(Announcement announcement);
}
