package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CompleteItemProgressRequestDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.LearningDtos.LearnerCoursePlayerDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.dto.RecordItemCompletionRequestDto;
import edu.courseflow.course.service.CourseModuleService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/internal/courses/{courseId}/modules")
public class CourseModuleController {
    private final CourseModuleService modules;

    public CourseModuleController(CourseModuleService modules) {
        this.modules = modules;
    }

    @GetMapping
    public List<CourseModuleDto> list(@PathVariable UUID courseId, CurrentUser user) {
        return modules.listModules(courseId, user);
    }

    @GetMapping("/player")
    public LearnerCoursePlayerDto player(@PathVariable UUID courseId, CurrentUser user) {
        return modules.player(courseId, user);
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
                                                        @Valid @RequestBody RecordItemCompletionRequestDto request) {
        return modules.recordVerifiedItemCompletion(courseId, moduleId, itemId, request);
    }

    @PostMapping("/items/progress/verified")
    public ItemProgressDto recordVerifiedItemCompletionBySource(@PathVariable UUID courseId,
                                                               @Valid @RequestBody RecordItemCompletionRequestDto request) {
        return modules.recordVerifiedItemCompletion(courseId, request);
    }

    /** Course-level completion percentage for the authenticated learner. */
    @GetMapping("/progress")
    public CourseProgressDto progress(@PathVariable UUID courseId, CurrentUser user) {
        return modules.progress(courseId, user);
    }

    @GetMapping("/progress/internal")
    public CourseProgressDto internalProgress(@PathVariable UUID courseId,
                                              @RequestParam String studentId) {
        return modules.progressForStudent(courseId, studentId);
    }
}
