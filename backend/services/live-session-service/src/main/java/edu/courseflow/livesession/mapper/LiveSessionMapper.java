package edu.courseflow.livesession.mapper;

import edu.courseflow.livesession.dto.LiveSessionDtos.LiveSessionDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegistrationDto;
import edu.courseflow.livesession.model.LiveSession;
import edu.courseflow.livesession.model.LiveSessionRegistration;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface LiveSessionMapper {

    LiveSessionDto toDto(LiveSession session);

    RegistrationDto toDto(LiveSessionRegistration registration);
}
