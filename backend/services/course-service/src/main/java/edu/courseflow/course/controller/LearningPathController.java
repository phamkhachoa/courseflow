package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.LearningDtos.LearnerLearningPathDto;
import edu.courseflow.course.service.CourseModuleService;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/courses/{courseId}/learning-path")
public class LearningPathController {

    private final CourseModuleService modules;

    public LearningPathController(CourseModuleService modules) {
        this.modules = modules;
    }

    @GetMapping
    public LearnerLearningPathDto learningPath(@PathVariable UUID courseId,
                                               @RequestParam Optional<String> cohortId,
                                               @RequestParam Optional<String> sectionId,
                                               CurrentUser user) {
        return modules.learningPath(courseId, user, cohortId.orElse(null), sectionId.orElse(null));
    }
}
