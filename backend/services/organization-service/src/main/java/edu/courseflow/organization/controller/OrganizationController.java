package edu.courseflow.organization.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.organization.dto.OrganizationDtos.AcademicTermDto;
import edu.courseflow.organization.dto.OrganizationDtos.CourseSectionDto;
import edu.courseflow.organization.dto.OrganizationDtos.CreateCourseSectionRequestDto;
import edu.courseflow.organization.dto.OrganizationDtos.DepartmentDto;
import edu.courseflow.organization.service.OrganizationService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrganizationController {

    private final OrganizationService organizations;

    public OrganizationController(OrganizationService organizations) {
        this.organizations = organizations;
    }

    @GetMapping("/internal/organizations/departments")
    public List<DepartmentDto> departments(CurrentUser user) {
        requireAuthenticated(user);
        return organizations.listDepartments();
    }

    @GetMapping("/internal/terms")
    public List<AcademicTermDto> terms(CurrentUser user) {
        requireAuthenticated(user);
        return organizations.listTerms();
    }

    @GetMapping("/internal/sections")
    public List<CourseSectionDto> sections(@RequestParam Optional<UUID> courseId, CurrentUser user) {
        requireAuthenticated(user);
        return organizations.listSections(courseId);
    }

    @PostMapping("/internal/sections")
    public CourseSectionDto createSection(@Valid @RequestBody CreateCourseSectionRequestDto request,
                                          CurrentUser user) {
        return organizations.createSection(request, user);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new edu.courseflow.organization.exception.ForbiddenException("Authentication required");
        }
    }
}
