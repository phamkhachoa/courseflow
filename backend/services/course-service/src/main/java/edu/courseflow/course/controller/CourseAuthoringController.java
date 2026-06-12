package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateCourseDraftRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateCurriculumRequestDto;
import edu.courseflow.course.service.CourseAuthoringService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/authoring/courses")
public class CourseAuthoringController {

    private final CourseAuthoringService authoring;

    public CourseAuthoringController(CourseAuthoringService authoring) {
        this.authoring = authoring;
    }

    @PostMapping
    public CourseDraftDto createDraft(@Valid @RequestBody CreateCourseDraftRequestDto request, CurrentUser user) {
        return authoring.createDraft(request, user);
    }

    @GetMapping("/{courseId}/draft")
    public CourseDraftDto getDraft(@PathVariable UUID courseId, CurrentUser user) {
        return authoring.getDraft(courseId, user);
    }

    @PutMapping("/{courseId}/curriculum")
    public CourseDraftDto updateCurriculum(@PathVariable UUID courseId, @Valid @RequestBody UpdateCurriculumRequestDto request, CurrentUser user) {
        return authoring.updateCurriculum(courseId, request, user);
    }

    @GetMapping("/{courseId}/versions")
    public List<CourseVersionDto> listVersions(@PathVariable UUID courseId, CurrentUser user) {
        return authoring.listVersions(courseId, user);
    }

    @PostMapping("/{courseId}/versions")
    public CourseVersionDto createVersion(@PathVariable UUID courseId, @Valid @RequestBody CreateVersionRequestDto request, CurrentUser user) {
        return authoring.createVersion(courseId, request, user);
    }

    @PostMapping("/{courseId}/submit-review")
    public CourseDraftDto submitForReview(@PathVariable UUID courseId, CurrentUser user) {
        return authoring.submitForReview(courseId, user);
    }

    @PostMapping("/{courseId}/approve")
    public CourseDraftDto approve(@PathVariable UUID courseId, @Valid @RequestBody(required = false) ReviewDecisionRequestDto request,
                                  CurrentUser user) {
        return authoring.approve(courseId, request, user);
    }

    @PostMapping("/{courseId}/reject")
    public CourseDraftDto reject(@PathVariable UUID courseId, @Valid @RequestBody(required = false) ReviewDecisionRequestDto request,
                                 CurrentUser user) {
        return authoring.reject(courseId, request, user);
    }

    @PostMapping("/{courseId}/modules")
    public CourseDraftDto createModule(@PathVariable UUID courseId,
                                       @Valid @RequestBody CreateModuleRequestDto request,
                                       CurrentUser user) {
        return authoring.createModule(courseId, request, user);
    }

    @PostMapping("/{courseId}/modules/{moduleId}/items")
    public CourseDraftDto createModuleItem(@PathVariable UUID courseId,
                                           @PathVariable UUID moduleId,
                                           @Valid @RequestBody CreateModuleItemRequestDto request,
                                           CurrentUser user) {
        return authoring.createModuleItem(courseId, moduleId, request, user);
    }
}
