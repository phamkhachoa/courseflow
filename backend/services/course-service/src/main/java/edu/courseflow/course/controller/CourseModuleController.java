package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CompleteItemProgressRequestDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.dto.RecordItemCompletionRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.service.CourseModuleService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/internal/courses/{courseId}/modules")
public class CourseModuleController {
    private final CourseModuleService modules;
    private final String serviceToken;

    public CourseModuleController(CourseModuleService modules,
                                  @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.modules = modules;
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    @GetMapping
    public List<CourseModuleDto> list(@PathVariable UUID courseId, CurrentUser user) {
        return modules.listModules(courseId, user);
    }

    @PostMapping("/{moduleId}/progress")
    public ModuleProgressDto complete(@PathVariable UUID courseId,
                                     @PathVariable UUID moduleId,
                                     CurrentUser user) {
        return modules.completeModule(courseId, moduleId, user);
    }

    @PostMapping("/{moduleId}/items/{itemId}/progress")
    public ItemProgressDto completeItem(@PathVariable UUID courseId,
                                        @PathVariable UUID moduleId,
                                        @PathVariable UUID itemId,
                                        @RequestBody(required = false) CompleteItemProgressRequestDto request,
                                        CurrentUser user) {
        return modules.completeItem(courseId, moduleId, itemId, request, user);
    }

    @PostMapping("/{moduleId}/items/{itemId}/progress/verified")
    public ItemProgressDto recordVerifiedItemCompletion(@PathVariable UUID courseId,
                                                        @PathVariable UUID moduleId,
                                                        @PathVariable UUID itemId,
                                                        @Valid @RequestBody RecordItemCompletionRequestDto request,
                                                        @RequestHeader(value = CourseAccessClient.SERVICE_TOKEN_HEADER, required = false)
                                                        String token) {
        requireServiceToken(token);
        return modules.recordVerifiedItemCompletion(courseId, moduleId, itemId, request);
    }

    @PostMapping("/items/progress/verified")
    public ItemProgressDto recordVerifiedItemCompletionBySource(@PathVariable UUID courseId,
                                                               @Valid @RequestBody RecordItemCompletionRequestDto request,
                                                               @RequestHeader(value = CourseAccessClient.SERVICE_TOKEN_HEADER, required = false)
                                                               String token) {
        requireServiceToken(token);
        return modules.recordVerifiedItemCompletion(courseId, request);
    }

    /** Course-level completion percentage for the authenticated learner. */
    @GetMapping("/progress")
    public CourseProgressDto progress(@PathVariable UUID courseId, CurrentUser user) {
        return modules.progress(courseId, user);
    }

    private void requireServiceToken(String token) {
        if (serviceToken.isBlank() || token == null || !serviceToken.equals(token.trim())) {
            throw new ForbiddenException("Service token required");
        }
    }
}
