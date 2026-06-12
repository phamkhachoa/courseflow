package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.AddCourseMaterialRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CreateCourseRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.service.CourseCatalogService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CourseCatalogController {

    private final CourseCatalogService courses;

    public CourseCatalogController(CourseCatalogService courses) {
        this.courses = courses;
    }

    @GetMapping("/public/courses")
    public List<CourseDto> listPublicCourses() {
        return courses.listPublished();
    }

    @GetMapping("/public/courses/{slug}")
    public CourseDto getPublicCourse(@PathVariable String slug) {
        return courses.getPublishedBySlug(slug);
    }

    @GetMapping("/internal/courses")
    public List<CourseDto> listCourses(@RequestParam Optional<String> status, CurrentUser user) {
        requireAuthenticated(user);
        if (!user.hasAnyRole("ADMIN", "INSTRUCTOR")) {
            if (status.isPresent() && !"PUBLISHED".equalsIgnoreCase(status.get())) {
                throw new ForbiddenException("Only ADMIN or INSTRUCTOR may list non-published courses");
            }
            return courses.listPublished();
        }
        return courses.list(status);
    }

    @PostMapping("/internal/courses")
    public CourseDto createCourse(@Valid @RequestBody CreateCourseRequestDto request, CurrentUser user) {
        return courses.create(request, user);
    }

    @GetMapping("/internal/courses/{courseId}")
    public CourseDto getCourse(@PathVariable UUID courseId, CurrentUser user) {
        requireAuthenticated(user);
        return courses.get(courseId);
    }

    @PostMapping("/internal/courses/{courseId}/materials")
    public CourseMaterialDto addMaterial(@PathVariable UUID courseId,
                                         @Valid @RequestBody AddCourseMaterialRequestDto request,
                                         CurrentUser user) {
        return courses.addMaterial(courseId, request, user);
    }

    @PostMapping("/internal/courses/{courseId}/publish")
    public CourseDto publish(@PathVariable UUID courseId, CurrentUser user) {
        return courses.publish(courseId, user);
    }

    @PostMapping("/internal/courses/{courseId}/archive")
    public CourseDto archive(@PathVariable UUID courseId, CurrentUser user) {
        return courses.archive(courseId, user);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }
}
