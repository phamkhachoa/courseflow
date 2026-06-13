package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewAuditDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewQueueItemDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDiffDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateCourseDraftRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.RollbackVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateCurriculumRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleRequestDto;
import edu.courseflow.course.service.CourseAuthoringService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
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

    @GetMapping("/{courseId}/versions/diff")
    public CourseVersionDiffDto diffDraftWithPublished(@PathVariable UUID courseId,
                                                       @RequestParam(required = false) Integer publishedVersionNo,
                                                       CurrentUser user) {
        return authoring.diffDraftWithPublished(courseId, publishedVersionNo, user);
    }

    @GetMapping("/{courseId}/review-history")
    public List<CourseReviewAuditDto> listReviewHistory(@PathVariable UUID courseId, CurrentUser user) {
        return authoring.listReviewHistory(courseId, user);
    }

    @GetMapping("/review-queue")
    public List<CourseReviewQueueItemDto> listReviewQueue(CurrentUser user) {
        return authoring.listReviewQueue(user);
    }

    @PostMapping("/{courseId}/versions")
    public CourseVersionDto createVersion(@PathVariable UUID courseId, @Valid @RequestBody CreateVersionRequestDto request, CurrentUser user) {
        return authoring.createVersion(courseId, request, user);
    }

    @PostMapping("/{courseId}/versions/{versionNo}/rollback-to-draft")
    public CourseDraftDto rollbackVersionToDraft(@PathVariable UUID courseId,
                                                 @PathVariable int versionNo,
                                                 @Valid @RequestBody(required = false) RollbackVersionRequestDto request,
                                                 CurrentUser user) {
        return authoring.rollbackPublishedVersionToDraft(courseId, versionNo, request, user);
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

    @PatchMapping("/{courseId}/modules/{moduleId}")
    public CourseDraftDto updateModule(@PathVariable UUID courseId,
                                       @PathVariable UUID moduleId,
                                       @Valid @RequestBody UpdateModuleRequestDto request,
                                       CurrentUser user) {
        return authoring.updateModule(courseId, moduleId, request, user);
    }

    @PostMapping("/{courseId}/modules/{moduleId}/duplicate")
    public CourseDraftDto duplicateModule(@PathVariable UUID courseId,
                                          @PathVariable UUID moduleId,
                                          CurrentUser user) {
        return authoring.duplicateModule(courseId, moduleId, user);
    }

    @DeleteMapping("/{courseId}/modules/{moduleId}")
    public CourseDraftDto archiveModule(@PathVariable UUID courseId,
                                        @PathVariable UUID moduleId,
                                        CurrentUser user) {
        return authoring.archiveModule(courseId, moduleId, user);
    }

    @PostMapping("/{courseId}/modules/{moduleId}/items")
    public CourseDraftDto createModuleItem(@PathVariable UUID courseId,
                                           @PathVariable UUID moduleId,
                                           @Valid @RequestBody CreateModuleItemRequestDto request,
                                           CurrentUser user) {
        return authoring.createModuleItem(courseId, moduleId, request, user);
    }

    @PatchMapping("/{courseId}/modules/{moduleId}/items/{itemId}")
    public CourseDraftDto updateModuleItem(@PathVariable UUID courseId,
                                           @PathVariable UUID moduleId,
                                           @PathVariable UUID itemId,
                                           @Valid @RequestBody UpdateModuleItemRequestDto request,
                                           CurrentUser user) {
        return authoring.updateModuleItem(courseId, moduleId, itemId, request, user);
    }

    @PostMapping("/{courseId}/modules/{moduleId}/items/{itemId}/duplicate")
    public CourseDraftDto duplicateModuleItem(@PathVariable UUID courseId,
                                             @PathVariable UUID moduleId,
                                             @PathVariable UUID itemId,
                                             CurrentUser user) {
        return authoring.duplicateModuleItem(courseId, moduleId, itemId, user);
    }

    @DeleteMapping("/{courseId}/modules/{moduleId}/items/{itemId}")
    public CourseDraftDto archiveModuleItem(@PathVariable UUID courseId,
                                            @PathVariable UUID moduleId,
                                            @PathVariable UUID itemId,
                                            CurrentUser user) {
        return authoring.archiveModuleItem(courseId, moduleId, itemId, user);
    }
}
