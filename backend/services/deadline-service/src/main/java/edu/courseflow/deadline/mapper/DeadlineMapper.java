package edu.courseflow.deadline.mapper;

import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.model.ReminderPolicy;
import edu.courseflow.deadline.model.ReminderRun;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface DeadlineMapper {

    ReminderPolicyDto toDto(ReminderPolicy policy);

    ReminderRunDto toDto(ReminderRun run);
}
