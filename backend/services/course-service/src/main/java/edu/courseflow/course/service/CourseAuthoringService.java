package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateCourseDraftRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOrderDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateCurriculumRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.repository.CourseJpaRepository;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourseAuthoringService {

    private final CourseJpaRepository courses;
    private final CourseModuleJpaRepository modules;
    private final ModuleItemJpaRepository items;
    private final CourseVersionJpaRepository versions;
    private final ObjectMapper objectMapper;
    private final CourseMapper mapper;

    public CourseAuthoringService(CourseJpaRepository courses,
            CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            CourseVersionJpaRepository versions,
            ObjectMapper objectMapper,
            CourseMapper mapper) {
        this.courses = courses;
        this.modules = modules;
        this.items = items;
        this.versions = versions;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
    }

    @Transactional
    public CourseDraftDto createDraft(CreateCourseDraftRequestDto request, CurrentUser user) {
        requireInstructorOrAdmin(user);
        // ownerId / last_authored_by come from the authenticated caller, never from the body.
        String ownerId = String.valueOf(user.id());
        UUID id = UUID.randomUUID();
        Course course = new Course(
                id,
                request.code(),
                request.title(),
                request.slug(),
                request.summary(),
                request.departmentId(),
                ownerId,
                request.level() == null ? "BEGINNER" : request.level());
        courses.save(course);
        createVersionRow(id, 1, "DRAFT", ownerId, "Initial draft");
        return getDraft(id);
    }

    public CourseDraftDto getDraft(UUID courseId) {
        Course course = findCourse(courseId);
        return mapper.toDraftDto(course, listModules(courseId));
    }

    public CourseDraftDto getDraft(UUID courseId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        return getDraft(courseId);
    }

    private List<ModuleOutlineDto> listModules(UUID courseId) {
        return modules.findByCourseIdOrderByPositionAsc(courseId).stream()
                .map(module -> mapper.toOutlineDto(module, listItems(module.getId())))
                .toList();
    }

    private List<ItemOutlineDto> listItems(UUID moduleId) {
        return items.findByModuleIdOrderByPositionAsc(moduleId).stream()
                .map(mapper::toOutlineDto)
                .toList();
    }

    /**
     * Rewrite module and item positions to match the order supplied by the author.
     * Done in two passes with a large temporary offset to avoid colliding with the
     * UNIQUE (course_id, position) / UNIQUE (module_id, position) constraints mid-update.
     */
    @Transactional
    public CourseDraftDto updateCurriculum(UUID courseId, UpdateCurriculumRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user); // also verifies the course exists
        int offset = 1000;
        int pos = 0;
        for (ModuleOrderDto module : request.modules()) {
            UUID moduleId = UUID.fromString(module.moduleId());
            setModulePosition(moduleId, courseId, pos + offset);
            if (module.itemIds() != null) {
                int itemPos = 0;
                for (String itemId : module.itemIds()) {
                    setItemPosition(UUID.fromString(itemId), moduleId, itemPos + offset);
                    itemPos++;
                }
            }
            pos++;
        }
        // Second pass: collapse back to 0-based contiguous positions.
        pos = 0;
        for (ModuleOrderDto module : request.modules()) {
            UUID moduleId = UUID.fromString(module.moduleId());
            setModulePosition(moduleId, courseId, pos);
            if (module.itemIds() != null) {
                int itemPos = 0;
                for (String itemId : module.itemIds()) {
                    setItemPosition(UUID.fromString(itemId), moduleId, itemPos);
                    itemPos++;
                }
            }
            pos++;
        }
        touch(courseId);
        return getDraft(courseId);
    }

    private void setModulePosition(UUID moduleId, UUID courseId, int position) {
        CourseModule module = modules.findByIdAndCourseId(moduleId, courseId)
                .orElseThrow(() -> new NotFoundException("Module not found: " + moduleId));
        module.setPosition(position);
        modules.saveAndFlush(module);
    }

    private void setItemPosition(UUID itemId, UUID moduleId, int position) {
        ModuleItem item = items.findByIdAndModuleId(itemId, moduleId)
                .orElseThrow(() -> new NotFoundException("Module item not found: " + itemId));
        item.setPosition(position);
        items.saveAndFlush(item);
    }

    @Transactional
    public CourseVersionDto createVersion(UUID courseId, CreateVersionRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        String actorId = String.valueOf(user.id());
        int nextVersion = versions.nextVersionNo(courseId);
        UUID versionId = createVersionRow(courseId, nextVersion, "DRAFT", actorId, request.note());
        Course course = findCourse(courseId);
        course.setCurrentVersionNo(nextVersion);
        course.setLastAuthoredBy(actorId);
        return getVersion(versionId);
    }

    @Transactional
    public CourseDraftDto submitForReview(UUID courseId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        String actorId = String.valueOf(user.id());
        Course course = findCourse(courseId);
        ensureReviewable(courseId);
        course.setReviewState("IN_REVIEW");
        course.setLastAuthoredBy(actorId);
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("IN_REVIEW"));
        return getDraft(courseId);
    }

    /**
     * Reviewer approves a course that is currently IN_REVIEW. Moves the review_state to APPROVED so
     * it becomes eligible for publishing. Staff-only (any INSTRUCTOR or ADMIN may review).
     */
    @Transactional
    public CourseDraftDto approve(UUID courseId, ReviewDecisionRequestDto request, CurrentUser user) {
        requireInstructorOrAdmin(user);
        Course course = findCourse(courseId);
        String reviewState = course.getReviewState();
        if (!"IN_REVIEW".equals(reviewState)) {
            throw new BadRequestException("Only a course IN_REVIEW can be approved (current: " + reviewState + ")");
        }
        course.setReviewState("APPROVED");
        course.setLastAuthoredBy(String.valueOf(user.id()));
        return getDraft(courseId);
    }

    /**
     * Reviewer rejects a course that is currently IN_REVIEW, sending it back to DRAFT for further
     * authoring. Staff-only.
     */
    @Transactional
    public CourseDraftDto reject(UUID courseId, ReviewDecisionRequestDto request, CurrentUser user) {
        requireInstructorOrAdmin(user);
        Course course = findCourse(courseId);
        String reviewState = course.getReviewState();
        if (!"IN_REVIEW".equals(reviewState)) {
            throw new BadRequestException("Only a course IN_REVIEW can be rejected (current: " + reviewState + ")");
        }
        course.setReviewState("DRAFT");
        course.setLastAuthoredBy(String.valueOf(user.id()));
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("DRAFT"));
        return getDraft(courseId);
    }

    /**
     * Freeze the current draft curriculum into the course_versions.snapshot for the live version and
     * stamp published_at. Called by the catalog publish flow once the course reaches PUBLISHED. Rejects
     * publishing a course whose review_state is not APPROVED. Returns the frozen version.
     */
    @Transactional
    public CourseVersionDto publishSnapshot(UUID courseId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        Course course = findCourse(courseId);
        String reviewState = course.getReviewState();
        if (!"APPROVED".equals(reviewState)) {
            throw new BadRequestException("Course must be APPROVED before publishing (current: " + reviewState + ")");
        }
        CourseVersion version = versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .orElseThrow(() -> new NotFoundException("Course version not found: " + courseId));
        version.publish(toJson(getDraft(courseId).modules()), Instant.now());
        course.setReviewState("PUBLISHED");
        publishModules(courseId);
        return toVersionDto(version);
    }

    private void publishModules(UUID courseId) {
        modules.findByCourseIdOrderByPositionAsc(courseId).forEach(module -> {
            module.setStatus("PUBLISHED");
            modules.save(module);
        });
    }

    /** Create a new module under the course draft. Position is appended after existing modules. */
    @Transactional
    public CourseDraftDto createModule(UUID courseId, CreateModuleRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        int nextPosition = modules.nextPosition(courseId);
        modules.save(new CourseModule(
                UUID.randomUUID(),
                courseId,
                request.title(),
                request.description(),
                nextPosition,
                request.status() == null ? "DRAFT" : request.status()));
        touch(courseId);
        return getDraft(courseId);
    }

    /** Create a new item inside a module, verifying the module belongs to the course. */
    @Transactional
    public CourseDraftDto createModuleItem(UUID courseId, UUID moduleId, CreateModuleItemRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        CourseModule module = modules.findById(moduleId)
                .orElseThrow(() -> new NotFoundException("Module not found: " + moduleId));
        if (!module.getCourseId().equals(courseId)) {
            throw new BadRequestException("Module " + moduleId + " does not belong to course " + courseId);
        }
        int nextPosition = items.nextPosition(moduleId);
        UUID itemUuid = UUID.randomUUID();
        String refId = resolveRefId(itemUuid, request);
        items.save(new ModuleItem(
                itemUuid,
                moduleId,
                request.itemType(),
                refId,
                request.title(),
                request.description(),
                request.videoMediaId(),
                request.documentMediaIds(),
                request.contentUrl(),
                request.estimatedMinutes(),
                nextPosition,
                request.required() == null ? Boolean.TRUE : request.required()));
        touch(courseId);
        return getDraft(courseId);
    }

    private String resolveRefId(UUID itemUuid, CreateModuleItemRequestDto request) {
        if (request.refId() != null && !request.refId().isBlank()) {
            return request.refId().trim();
        }
        if (request.videoMediaId() != null) {
            return request.videoMediaId().toString();
        }
        if (request.contentUrl() != null && !request.contentUrl().isBlank()) {
            return request.contentUrl().trim();
        }
        return itemUuid.toString();
    }

    private void ensureReviewable(UUID courseId) {
        List<CourseModule> courseModules = modules.findByCourseIdOrderByPositionAsc(courseId);
        if (courseModules.isEmpty()) {
            throw new BadRequestException("Course must have at least one chapter before review");
        }
        boolean hasLesson = courseModules.stream()
                .anyMatch(module -> !items.findByModuleIdOrderByPositionAsc(module.getId()).isEmpty());
        if (!hasLesson) {
            throw new BadRequestException("Course must have at least one lesson before review");
        }
    }

    public List<CourseVersionDto> listVersions(UUID courseId) {
        return versions.findByCourseIdOrderByVersionNoDesc(courseId).stream()
                .map(this::toVersionDto)
                .toList();
    }

    public List<CourseVersionDto> listVersions(UUID courseId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        return listVersions(courseId);
    }

    private CourseVersionDto getVersion(UUID versionId) {
        return versions.findById(versionId)
                .map(this::toVersionDto)
                .orElseThrow(() -> new NotFoundException("Course version not found: " + versionId));
    }

    private UUID createVersionRow(UUID courseId, int versionNo, String state, String createdBy, String note) {
        return versions.findByCourseIdAndVersionNo(courseId, versionNo)
                .map(CourseVersion::getId)
                .orElseGet(() -> versions.save(new CourseVersion(
                        UUID.randomUUID(),
                        courseId,
                        versionNo,
                        state,
                        createdBy,
                        note)).getId());
    }

    @Transactional
    public void ensureInitialVersion(UUID courseId, String createdBy) {
        findCourse(courseId);
        createVersionRow(courseId, 1, "DRAFT", createdBy, "Initial draft");
    }

    private void touch(UUID courseId) {
        findCourse(courseId).touch();
    }

    private CourseVersionDto toVersionDto(CourseVersion version) {
        return mapper.toDto(version);
    }

    private Course findCourse(UUID courseId) {
        return courses.findById(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
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
     * Authoring mutations are limited to the owning instructor (matched against {@code owner_id})
     * or an ADMIN. Also verifies the course exists, throwing 404 otherwise.
     */
    private void requireOwnerOrAdmin(UUID courseId, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        Course course = findCourse(courseId);
        if (user.hasRole("ADMIN")) {
            return;
        }
        boolean isOwner = user.hasRole("INSTRUCTOR") && String.valueOf(user.id()).equals(course.getOwnerId());
        if (!isOwner) {
            throw new ForbiddenException("Only the owning instructor or an ADMIN may author this course");
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
