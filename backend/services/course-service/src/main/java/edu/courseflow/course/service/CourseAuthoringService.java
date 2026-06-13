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
import java.net.URI;
import java.net.URISyntaxException;
import java.time.Instant;
import java.util.ArrayList;
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
    private final CourseContentReadinessClient readinessClient;

    public CourseAuthoringService(CourseJpaRepository courses,
            CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            CourseVersionJpaRepository versions,
            ObjectMapper objectMapper,
            CourseMapper mapper,
            CourseContentReadinessClient readinessClient) {
        this.courses = courses;
        this.modules = modules;
        this.items = items;
        this.versions = versions;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.readinessClient = readinessClient;
    }

    @Transactional
    public CourseDraftDto createDraft(CreateCourseDraftRequestDto request, CurrentUser user) {
        requireCourseCreator(user, request.departmentId());
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
        course.setReviewState("DRAFT");
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
     * it becomes eligible for publishing. Owners cannot approve their own course.
     */
    @Transactional
    public CourseDraftDto approve(UUID courseId, ReviewDecisionRequestDto request, CurrentUser user) {
        Course course = findCourse(courseId);
        requireReviewer(course, user);
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
     * authoring. Owners cannot reject their own course.
     */
    @Transactional
    public CourseDraftDto reject(UUID courseId, ReviewDecisionRequestDto request, CurrentUser user) {
        Course course = findCourse(courseId);
        requireReviewer(course, user);
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
        ensureReviewable(courseId);
        CourseVersion version = versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .orElseThrow(() -> new NotFoundException("Course version not found: " + courseId));
        List<ModuleOutlineDto> snapshotModules = getDraft(courseId).modules();
        validatePublishSnapshot(snapshotModules);
        version.publish(toJson(snapshotModules), Instant.now());
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
                "DRAFT"));
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
        if (requiresExternalRef(normalizeItemType(
                request.itemType(), request.videoMediaId(), request.documentMediaIds(), request.contentUrl()))) {
            return "";
        }
        return itemUuid.toString();
    }

    private void ensureReviewable(UUID courseId) {
        List<CourseModule> courseModules = modules.findByCourseIdOrderByPositionAsc(courseId);
        if (courseModules.isEmpty()) {
            throw new BadRequestException("Course must have at least one chapter before review");
        }
        List<String> issues = new ArrayList<>();
        int requiredItems = 0;
        for (CourseModule module : courseModules) {
            List<ModuleItem> moduleItems = items.findByModuleIdOrderByPositionAsc(module.getId());
            if (moduleItems.isEmpty()) {
                issues.add("Module '" + module.getTitle() + "' has no learning items");
                continue;
            }
            boolean moduleHasRequiredItem = false;
            for (ModuleItem item : moduleItems) {
                if (item.isRequired()) {
                    moduleHasRequiredItem = true;
                    requiredItems++;
                }
                validateItemReadiness(module, item, issues);
            }
            if (!moduleHasRequiredItem) {
                issues.add("Module '" + module.getTitle() + "' must contain at least one required item");
            }
        }
        if (requiredItems == 0) {
            issues.add("Course must contain at least one required learning item");
        }
        if (!issues.isEmpty()) {
            throw new BadRequestException("Course is not ready for review: " + String.join("; ", issues));
        }
    }

    private void validateItemReadiness(CourseModule module, ModuleItem item, List<String> issues) {
        String label = "Module '" + module.getTitle() + "', item '" + item.getTitle() + "'";
        String kind = normalizeItemType(item);
        if (item.getEstimatedMinutes() != null && item.getEstimatedMinutes() < 0) {
            issues.add(label + " has negative estimated minutes");
        }
        switch (kind) {
            case "VIDEO" -> {
                if (item.getVideoMediaId() == null) {
                    issues.add(label + " is a video item without video media");
                } else {
                    addReadinessIssue(issues, label, () -> readinessClient.videoIssue(item.getVideoMediaId(), module.getCourseId()));
                }
            }
            case "DOCUMENT", "PDF", "MATERIAL" -> {
                if (!hasDocuments(item) && isBlank(item.getContentUrl())) {
                    issues.add(label + " is a document item without document media or URL");
                }
                if (!isBlank(item.getContentUrl()) && !isHttpUrl(item.getContentUrl())) {
                    issues.add(label + " has an invalid document URL");
                }
            }
            case "LINK" -> {
                if (isBlank(item.getContentUrl())) {
                    issues.add(label + " is a link item without URL");
                } else if (!isHttpUrl(item.getContentUrl())) {
                    issues.add(label + " has an invalid URL");
                }
            }
            case "QUIZ", "ASSIGNMENT" -> {
                if (isBlank(item.getItemId()) || item.getId().toString().equals(item.getItemId().trim())) {
                    issues.add(label + " is a " + kind.toLowerCase() + " item without a linked " + kind.toLowerCase());
                } else if (!isUuid(item.getItemId())) {
                    issues.add(label + " has an invalid " + kind.toLowerCase() + " reference");
                } else if ("QUIZ".equals(kind)) {
                    addReadinessIssue(issues, label,
                            () -> readinessClient.quizIssue(UUID.fromString(item.getItemId().trim()), module.getCourseId()));
                } else {
                    addReadinessIssue(issues, label,
                            () -> readinessClient.assignmentIssue(UUID.fromString(item.getItemId().trim()), module.getCourseId()));
                }
            }
            case "LESSON" -> {
                if (!hasLearningContent(item)) {
                    issues.add(label + " has no learning content");
                }
            }
            default -> issues.add(label + " has unsupported item type '" + kind + "'");
        }
    }

    private void addReadinessIssue(List<String> issues, String label, ReadinessCheck check) {
        try {
            check.issue().ifPresent(issue -> issues.add(label + " " + issue));
        } catch (CourseContentReadinessClient.ContentReadinessException ex) {
            issues.add(label + " " + ex.getMessage());
        }
    }

    private void validatePublishSnapshot(List<ModuleOutlineDto> snapshotModules) {
        if (snapshotModules == null || snapshotModules.isEmpty()) {
            throw new BadRequestException("Published course snapshot must include at least one module");
        }
        boolean hasRequiredItem = snapshotModules.stream()
                .flatMap(module -> module.items() == null ? List.<ItemOutlineDto>of().stream() : module.items().stream())
                .anyMatch(ItemOutlineDto::required);
        if (!hasRequiredItem) {
            throw new BadRequestException("Published course snapshot must include at least one required item");
        }
    }

    @FunctionalInterface
    private interface ReadinessCheck {
        java.util.Optional<String> issue();
    }

    private String normalizeItemType(ModuleItem item) {
        return normalizeItemType(item.getItemType(), item.getVideoMediaId(), item.getDocumentMediaIds(), item.getContentUrl());
    }

    private String normalizeItemType(String itemType, UUID videoMediaId, List<String> documentMediaIds, String contentUrl) {
        if (videoMediaId != null) {
            return "VIDEO";
        }
        String normalized = isBlank(itemType) ? "LESSON" : itemType.trim().toUpperCase();
        if ((documentMediaIds != null && documentMediaIds.stream().anyMatch(id -> !isBlank(id)))
                && ("LESSON".equals(normalized) || "MATERIAL".equals(normalized))) {
            return "DOCUMENT";
        }
        if ("LINK".equals(normalized) || ("LESSON".equals(normalized) && !isBlank(contentUrl))) {
            return "LINK";
        }
        return normalized;
    }

    private boolean requiresExternalRef(String kind) {
        return "QUIZ".equals(kind) || "ASSIGNMENT".equals(kind);
    }

    private boolean hasLearningContent(ModuleItem item) {
        return !isBlank(item.getDescription())
                || !isBlank(item.getContentUrl())
                || item.getVideoMediaId() != null
                || hasDocuments(item)
                || (!isBlank(item.getItemId()) && !item.getId().toString().equals(item.getItemId().trim()));
    }

    private boolean hasDocuments(ModuleItem item) {
        return item.getDocumentMediaIds().stream().anyMatch(id -> !isBlank(id));
    }

    private boolean isHttpUrl(String value) {
        try {
            URI uri = new URI(value.trim());
            return "http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme());
        } catch (URISyntaxException ex) {
            return false;
        }
    }

    private boolean isUuid(String value) {
        try {
            UUID.fromString(value.trim());
            return true;
        } catch (RuntimeException ex) {
            return false;
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
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
        Course course = findCourse(courseId);
        course.setReviewState("DRAFT");
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("DRAFT"));
        course.touch();
    }

    private CourseVersionDto toVersionDto(CourseVersion version) {
        return mapper.toDto(version);
    }

    private Course findCourse(UUID courseId) {
        return courses.findById(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
    }

    private void requireCourseCreator(CurrentUser user, UUID departmentId) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
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

    private void requireReviewer(Course course, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        if (isPlatformAdmin(user)) {
            return;
        }
        boolean isOwner = String.valueOf(user.id()).equals(course.getOwnerId());
        if (!isOwner && hasScopedReviewerRole(course, user)) {
            return;
        }
        throw new ForbiddenException("Course review requires an independent reviewer");
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
        if (isPlatformAdmin(user) || user.hasDepartmentRole("ORG_ADMIN", String.valueOf(course.getDepartmentId()))) {
            return;
        }
        boolean isOwner = user.hasAnyRole("INSTRUCTOR", "PROFESSOR")
                && String.valueOf(user.id()).equals(course.getOwnerId());
        if (!isOwner) {
            throw new ForbiddenException("Only the owning instructor or an ADMIN may author this course");
        }
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }

    private boolean hasScopedReviewerRole(Course course, CurrentUser user) {
        String departmentId = String.valueOf(course.getDepartmentId());
        return user.hasAnyDepartmentRole(departmentId, "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA")
                || user.hasAnyCourseRole(course.getId(), "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA");
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
