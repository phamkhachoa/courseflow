package edu.courseflow.enrollment.mapper;

import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.model.Enrollment;
import edu.courseflow.enrollment.model.EnrollmentAuditLog;
import edu.courseflow.enrollment.model.WaitlistEntry;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface EnrollmentMapper {

    EnrollmentDto toDto(Enrollment enrollment);

    WaitlistEntryDto toDto(WaitlistEntry entry);

    AuditLogEntryDto toDto(EnrollmentAuditLog entry);
}
