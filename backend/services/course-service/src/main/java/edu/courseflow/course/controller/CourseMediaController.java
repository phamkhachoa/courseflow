package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.PresignedDownloadDto;
import edu.courseflow.course.service.CourseModuleService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/courses/{courseId}/media")
public class CourseMediaController {

    private final CourseModuleService modules;

    public CourseMediaController(CourseModuleService modules) {
        this.modules = modules;
    }

    @GetMapping("/assets/{mediaId}/download-url")
    public PresignedDownloadDto downloadUrl(@PathVariable UUID courseId,
                                            @PathVariable UUID mediaId,
                                            CurrentUser user) {
        return modules.downloadPublishedMedia(courseId, mediaId, user);
    }
}
