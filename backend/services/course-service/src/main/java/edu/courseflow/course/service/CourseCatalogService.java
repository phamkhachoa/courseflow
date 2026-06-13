package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.AddCourseMaterialRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CreateCourseRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseMetadataDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.repository.CourseCatalogRepository;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.course.CourseArchivedEvent;
import edu.courseflow.events.course.CoursePublishedEvent;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
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

    public List<CourseDto> list(Optional<String> status, CurrentUser user) {
        requireAuthenticated(user);
        if (isPlatformAdmin(user)) {
            return courses.list(status);
        }
        List<UUID> orgAdminDepartments = scopedDepartmentIds(user, "ORG_ADMIN");
        if (!orgAdminDepartments.isEmpty()) {
            return courses.listByDepartmentIds(orgAdminDepartments, status);
        }
        if (user.hasAnyRole("INSTRUCTOR", "PROFESSOR", "TA")) {
            return courses.listOwned(String.valueOf(user.id()), status);
        }
        if (status.isPresent() && !"PUBLISHED".equalsIgnoreCase(status.get())) {
            throw new ForbiddenException("Only course staff may list non-published courses");
        }
        return courses.listPublished();
    }

    public List<CourseDto> listPublished() {
        return courses.listPublished();
    }

    public CourseDto get(UUID courseId) {
        return courses.findById(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
    }

    public CourseDto get(UUID courseId, CurrentUser user) {
        requireAuthenticated(user);
        CourseDto course = get(courseId);
        if ("PUBLISHED".equals(course.status())) {
            return course;
        }
        requireOwnerOrAdmin(course, user);
        return course;
    }

    public CourseMetadataDto metadata(UUID courseId) {
        return courses.metadata(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
    }

    public CourseDto getPublishedBySlug(String slug) {
        return courses.findPublishedBySlug(slug)
                .orElseThrow(() -> new NotFoundException("Published course not found: " + slug));
    }

    @Transactional
    public CourseDto create(CreateCourseRequestDto request, CurrentUser user) {
        requireCourseCreator(user, request.departmentId());
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
        courses.outbox(courseId, "course.published", toJson(new CoursePublishedEvent(
                UUID.randomUUID().toString(),
                courseId.toString(),
                current.code(),
                current.title(),
                current.slug(),
                current.summary(),
                current.departmentId(),
                current.ownerId(),
                current.level(),
                "PUBLISHED",
                Instant.now(),
                metadata(user))));
        return get(courseId);
    }

    @Transactional
    public CourseDto archive(UUID courseId, CurrentUser user) {
        CourseDto current = get(courseId);
        requireOwnerOrAdmin(current, user);
        courses.updateStatus(courseId, "ARCHIVED");
        courses.outbox(courseId, "course.archived", toJson(new CourseArchivedEvent(
                UUID.randomUUID().toString(),
                courseId.toString(),
                current.code(),
                current.title(),
                current.slug(),
                current.summary(),
                current.departmentId(),
                current.ownerId(),
                current.level(),
                "ARCHIVED",
                Instant.now(),
                metadata(user))));
        return get(courseId);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }

    private void requireCourseCreator(CurrentUser user, UUID departmentId) {
        requireAuthenticated(user);
        if (isPlatformAdmin(user)
                || user.hasAnyDepartmentRole(String.valueOf(departmentId), "INSTRUCTOR", "PROFESSOR")
                || user.hasPlatformRole("INSTRUCTOR")
                || user.hasPlatformRole("PROFESSOR")) {
            return;
        }
        if (!user.hasAnyRole("INSTRUCTOR", "PROFESSOR", "ADMIN")) {
            throw new ForbiddenException("Requires INSTRUCTOR or ADMIN role");
        }
        throw new ForbiddenException("Caller is not allowed to create courses in this department");
    }

    /**
     * Publish/archive/material changes are limited to the course owner (an instructor) or an ADMIN.
     * Ownership is matched against {@code owner_id}, which stores the gateway user id as a string.
     */
    private void requireOwnerOrAdmin(CourseDto course, CurrentUser user) {
        requireAuthenticated(user);
        if (isPlatformAdmin(user) || user.hasDepartmentRole("ORG_ADMIN", course.departmentId())) {
            return;
        }
        boolean isOwner = user.hasAnyRole("INSTRUCTOR", "PROFESSOR")
                && String.valueOf(user.id()).equals(course.ownerId());
        if (!isOwner) {
            throw new ForbiddenException("Only the owning instructor, scoped ORG_ADMIN or platform ADMIN may modify this course");
        }
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }

    private List<UUID> scopedDepartmentIds(CurrentUser user, String role) {
        Set<UUID> departmentIds = new LinkedHashSet<>();
        for (CurrentUser.RoleAssignment assignment : user.roleAssignments()) {
            if (!role.equalsIgnoreCase(assignment.code())
                    || !"DEPARTMENT".equalsIgnoreCase(assignment.scopeType())
                    || assignment.scopeId() == null) {
                continue;
            }
            try {
                departmentIds.add(UUID.fromString(assignment.scopeId()));
            } catch (IllegalArgumentException ignored) {
                // Invalid scoped ids do not grant department access.
            }
        }
        return List.copyOf(departmentIds);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }

    private EventMetadata metadata(CurrentUser user) {
        return new EventMetadata(null, null, String.valueOf(user.id()), Map.of());
    }
}
