package edu.courseflow.organization.service;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.organization.dto.OrganizationDtos.AcademicTermDto;
import edu.courseflow.organization.dto.OrganizationDtos.CourseSectionDto;
import edu.courseflow.organization.dto.OrganizationDtos.CreateCourseSectionRequestDto;
import edu.courseflow.organization.dto.OrganizationDtos.DepartmentDto;
import edu.courseflow.organization.exception.ForbiddenException;
import edu.courseflow.organization.repository.OrganizationRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrganizationService {

    private final OrganizationRepository organizations;

    public OrganizationService(OrganizationRepository organizations) {
        this.organizations = organizations;
    }

    public List<DepartmentDto> listDepartments() {
        return organizations.listDepartments();
    }

    public List<AcademicTermDto> listTerms() {
        return organizations.listTerms();
    }

    public List<CourseSectionDto> listSections(Optional<UUID> courseId) {
        return organizations.listSections(courseId.orElse(null));
    }

    @Transactional
    public CourseSectionDto createSection(CreateCourseSectionRequestDto request, CurrentUser user) {
        // Creating a section is an administrative action: only ADMIN or operator may do it.
        requireAdminOrOperator(user);
        return organizations.createSection(request);
    }

    private void requireAdminOrOperator(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        if (!user.hasAnyRole("ADMIN", "ORG_ADMIN")) {
            throw new ForbiddenException("Requires ADMIN or ORG_ADMIN role");
        }
    }
}
