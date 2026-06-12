package edu.courseflow.organization.repository;

import edu.courseflow.organization.dto.OrganizationDtos.AcademicTermDto;
import edu.courseflow.organization.dto.OrganizationDtos.CourseSectionDto;
import edu.courseflow.organization.dto.OrganizationDtos.CreateCourseSectionRequestDto;
import edu.courseflow.organization.dto.OrganizationDtos.DepartmentDto;
import edu.courseflow.organization.mapper.OrganizationMapper;
import edu.courseflow.organization.model.CourseSection;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class OrganizationRepository {

    private final DepartmentJpaRepository departments;
    private final AcademicTermJpaRepository terms;
    private final CourseSectionJpaRepository sections;
    private final OrganizationMapper mapper;

    public OrganizationRepository(DepartmentJpaRepository departments,
            AcademicTermJpaRepository terms,
            CourseSectionJpaRepository sections,
            OrganizationMapper mapper) {
        this.departments = departments;
        this.terms = terms;
        this.sections = sections;
        this.mapper = mapper;
    }

    public List<DepartmentDto> listDepartments() {
        return departments.findAllByOrderByCodeAsc().stream().map(mapper::toDto).toList();
    }

    public List<AcademicTermDto> listTerms() {
        return terms.findAllByOrderByStartDateDesc().stream().map(mapper::toDto).toList();
    }

    public List<CourseSectionDto> listSections(UUID courseId) {
        List<CourseSection> rows = courseId == null
                ? sections.findAllByOrderBySectionCodeAsc()
                : sections.findByCourseIdOrderBySectionCodeAsc(courseId);
        return rows.stream().map(mapper::toDto).toList();
    }

    public CourseSectionDto createSection(CreateCourseSectionRequestDto request) {
        return mapper.toDto(sections.save(mapper.toEntity(request)));
    }
}
