package edu.courseflow.notification.mapper;

import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationPreferenceDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.model.NotificationPreference;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface NotificationMapper {

    NotificationDto toDto(Notification notification);

    NotificationPreferenceDto toDto(NotificationPreference preference);
}
