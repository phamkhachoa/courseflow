package edu.courseflow.course.controller;

import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckDto;
import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckRequestDto;
import edu.courseflow.course.service.CourseModuleService;
import java.util.UUID;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/courses/{courseId}/learning-access")
public class LearningAccessController {

    private final CourseModuleService modules;

    public LearningAccessController(CourseModuleService modules) {
        this.modules = modules;
    }

    @PostMapping("/check")
    public LearningAccessCheckDto check(@PathVariable UUID courseId,
                                        @RequestBody LearningAccessCheckRequestDto request) {
        return modules.checkLearningAccess(courseId, request);
    }
}
