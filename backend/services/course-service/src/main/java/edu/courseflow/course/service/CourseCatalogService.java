package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.AddCourseMaterialRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CreateCourseRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.repository.CourseCatalogRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourseCatalogService {

    private final CourseCatalogRepository courses;
    private final CourseAuthoringService authoring;
    private final ObjectMapper objectMapper;

    public CourseCatalogService(CourseCatalogRepository courses, CourseAuthoringService authoring, ObjectMapper objectMapper) {
        this.courses = courses;
        this.authoring = authoring;
        this.objectMapper = objectMapper;
    }

    public List<CourseDto> list(Optional<String> status) {
        return courses.list(status);
    }

    public List<CourseDto> listPublished() {
        return courses.listPublished();
    }

    public CourseDto get(UUID courseId) {
        return courses.findById(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
    }

    public CourseDto getPublishedBySlug(String slug) {
        return courses.findPublishedBySlug(slug)
                .orElseThrow(() -> new NotFoundException("Published course not found: " + slug));
    }

    @Transactional
    public CourseDto create(CreateCourseRequestDto request, CurrentUser user) {
        requireInstructorOrAdmin(user);
        // ownerId is taken from the authenticated caller, never from the request body.
        String ownerId = String.valueOf(user.id());
        CourseDto created = courses.create(request, ownerId);
        authoring.ensureInitialVersion(UUID.fromString(created.id()), ownerId);
        return created;
    }

    @Transactional
    public CourseMaterialDto addMaterial(UUID courseId, AddCourseMaterialRequestDto request, CurrentUser user) {
        CourseDto course = get(courseId);
        requireOwnerOrAdmin(course, user);
        return courses.addMaterial(courseId, request);
    }

    @Transactional
    public CourseDto publish(UUID courseId, CurrentUser user) {
        CourseDto current = get(courseId);
        requireOwnerOrAdmin(current, user);
        // Enforce the review workflow (must be APPROVED), freeze the curriculum snapshot into the
        // current course_version and stamp published_at before the course goes live.
        authoring.publishSnapshot(courseId, user);
        courses.updateStatus(courseId, "PUBLISHED");
        courses.outbox(courseId, "course.published", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "courseId", courseId.toString(),
                "code", current.code(),
                "title", current.title(),
                "slug", current.slug(),
                "departmentId", current.departmentId(),
                "ownerId", current.ownerId())));
        return get(courseId);
    }

    @Transactional
    public CourseDto archive(UUID courseId, CurrentUser user) {
        CourseDto current = get(courseId);
        requireOwnerOrAdmin(current, user);
        courses.updateStatus(courseId, "ARCHIVED");
        return get(courseId);
    }

    private void requireInstructorOrAdmin(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        if (!user.hasAnyRole("INSTRUCTOR", "ADMIN")) {
            throw new ForbiddenException("Requires INSTRUCTOR or ADMIN role");
        }
    }

    /**
     * Publish/archive/material changes are limited to the course owner (an instructor) or an ADMIN.
     * Ownership is matched against {@code owner_id}, which stores the gateway user id as a string.
     */
    private void requireOwnerOrAdmin(CourseDto course, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        if (user.hasRole("ADMIN")) {
            return;
        }
        boolean isOwner = user.hasRole("INSTRUCTOR") && String.valueOf(user.id()).equals(course.ownerId());
        if (!isOwner) {
            throw new ForbiddenException("Only the owning instructor or an ADMIN may modify this course");
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
