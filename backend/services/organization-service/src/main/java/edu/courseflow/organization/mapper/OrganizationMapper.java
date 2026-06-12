package edu.courseflow.organization.mapper;

import edu.courseflow.organization.dto.OrganizationDtos.AcademicTermDto;
import edu.courseflow.organization.dto.OrganizationDtos.CourseSectionDto;
import edu.courseflow.organization.dto.OrganizationDtos.CreateCourseSectionRequestDto;
import edu.courseflow.organization.dto.OrganizationDtos.DepartmentDto;
import edu.courseflow.organization.model.AcademicTerm;
import edu.courseflow.organization.model.CourseSection;
import edu.courseflow.organization.model.Department;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface OrganizationMapper {

    DepartmentDto toDto(Department department);

    AcademicTermDto toDto(AcademicTerm term);

    CourseSectionDto toDto(CourseSection section);

    @Mapping(target = "id", expression = "java(java.util.UUID.randomUUID())")
    @Mapping(target = "status", constant = "DRAFT")
    CourseSection toEntity(CreateCourseSectionRequestDto request);
}
