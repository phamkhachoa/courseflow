package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.AddCourseMaterialRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CreateCourseRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseMetadataDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.service.CourseCatalogService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CourseCatalogController {

    private final CourseCatalogService courses;
    private final String serviceToken;

    public CourseCatalogController(CourseCatalogService courses,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.courses = courses;
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
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
        return courses.list(status, user);
    }

    @PostMapping("/internal/courses")
    public CourseDto createCourse(@Valid @RequestBody CreateCourseRequestDto request, CurrentUser user) {
        return courses.create(request, user);
    }

    @GetMapping("/internal/courses/{courseId}")
    public CourseDto getCourse(@PathVariable UUID courseId, CurrentUser user) {
        return courses.get(courseId, user);
    }

    @GetMapping("/internal/courses/{courseId}/metadata")
    public CourseMetadataDto metadata(@PathVariable UUID courseId,
            @RequestHeader(value = CourseAccessClient.SERVICE_TOKEN_HEADER, required = false) String token) {
        requireServiceToken(token);
        return courses.metadata(courseId);
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

    private void requireServiceToken(String token) {
        if (serviceToken.isBlank() || token == null || !serviceToken.equals(token.trim())) {
            throw new ForbiddenException("Service token required");
        }
    }
}
