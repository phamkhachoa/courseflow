package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewAuditDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewQueueItemDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDiffChangeDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDiffDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateCourseDraftRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateModuleRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.CreateVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModulePrerequisiteOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOrderDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.RollbackVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateCurriculumRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseReviewAuditLog;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.repository.CourseJpaRepository;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseReviewAuditLogJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import edu.courseflow.course.repository.ModulePrerequisiteJpaRepository;
import java.net.URI;
import java.net.URISyntaxException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourseAuthoringService {

    private final CourseJpaRepository courses;
    private final CourseModuleJpaRepository modules;
    private final ModuleItemJpaRepository items;
    private final ModulePrerequisiteJpaRepository prerequisites;
    private final CourseVersionJpaRepository versions;
    private final CourseReviewAuditLogJpaRepository reviewAuditLogs;
    private final ObjectMapper objectMapper;
    private final CourseMapper mapper;
    private final CourseContentReadinessClient readinessClient;

    public CourseAuthoringService(CourseJpaRepository courses,
            CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            ModulePrerequisiteJpaRepository prerequisites,
            CourseVersionJpaRepository versions,
            CourseReviewAuditLogJpaRepository reviewAuditLogs,
            ObjectMapper objectMapper,
            CourseMapper mapper,
            CourseContentReadinessClient readinessClient) {
        this.courses = courses;
        this.modules = modules;
        this.items = items;
        this.prerequisites = prerequisites;
        this.versions = versions;
        this.reviewAuditLogs = reviewAuditLogs;
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
        recordReviewAudit(course, user, "CREATE_DRAFT", null, "DRAFT", "Initial draft", List.of());
        return getDraft(id);
    }

    public CourseDraftDto getDraft(UUID courseId) {
        Course course = findCourse(courseId);
        return mapper.toDraftDto(course, listModules(courseId));
    }

    public CourseDraftDto getDraft(UUID courseId, CurrentUser user) {
        Course course = findCourse(courseId);
        requireReviewVisibility(course, user);
        return mapper.toDraftDto(course, listModules(courseId));
    }

    private List<ModuleOutlineDto> listModules(UUID courseId) {
        return modules.findByCourseIdOrderByPositionAsc(courseId).stream()
                .filter(module -> !"ARCHIVED".equals(module.getStatus()))
                .map(module -> {
                    List<ItemOutlineDto> itemDtos = listItems(module.getId()).stream()
                            .filter(Objects::nonNull)
                            .toList();
                    ModuleOutlineDto outline = mapper.toOutlineDto(module, itemDtos);
                    return withPrerequisites(module, outline == null ? fallbackOutline(module, itemDtos) : outline);
                })
                .toList();
    }

    private ModuleOutlineDto fallbackOutline(CourseModule module, List<ItemOutlineDto> itemDtos) {
        return new ModuleOutlineDto(
                module.getId().toString(),
                module.getTitle(),
                module.getDescription(),
                module.getPosition(),
                module.getStatus(),
                itemDtos);
    }

    private ModuleOutlineDto withPrerequisites(CourseModule module, ModuleOutlineDto outline) {
        List<ModulePrerequisiteOutlineDto> prerequisiteDtos = prerequisites.findByModuleId(module.getId()).stream()
                .map(prerequisite -> new ModulePrerequisiteOutlineDto(
                        prerequisite.getRequiredModuleId().toString(),
                        prerequisite.getRuleType()))
                .toList();
        return new ModuleOutlineDto(
                outline.moduleId(),
                outline.title(),
                outline.description(),
                outline.position(),
                outline.status(),
                outline.items(),
                prerequisiteDtos);
    }

    private List<ItemOutlineDto> listItems(UUID moduleId) {
        return items.findByModuleIdOrderByPositionAsc(moduleId).stream()
                .filter(item -> !"ARCHIVED".equals(item.getStatus()))
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
        ensureMutableDraftVersion(courseId, user);
        validateCurriculumOrder(courseId, request);
        int offset = temporaryPositionOffset(courseId);
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
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    private void validateCurriculumOrder(UUID courseId, UpdateCurriculumRequestDto request) {
        if (request == null || request.modules() == null) {
            throw new BadRequestException("Curriculum order must include modules");
        }
        List<CourseModule> activeModules = activeModules(courseId);
        Set<String> expectedModuleIds = activeModules.stream()
                .map(module -> module.getId().toString())
                .collect(Collectors.toCollection(HashSet::new));
        Set<String> requestedModuleIds = new HashSet<>();
        if (request.modules().size() != expectedModuleIds.size()) {
            throw new BadRequestException("Curriculum order must include every active module exactly once");
        }
        for (ModuleOrderDto module : request.modules()) {
            if (!requestedModuleIds.add(module.moduleId())) {
                throw new BadRequestException("Duplicate module in curriculum order: " + module.moduleId());
            }
            if (!expectedModuleIds.contains(module.moduleId())) {
                throw new BadRequestException("Unknown or archived module in curriculum order: " + module.moduleId());
            }
            UUID moduleId = UUID.fromString(module.moduleId());
            validateItemOrder(moduleId, module.itemIds());
        }
    }

    private void validateItemOrder(UUID moduleId, List<String> itemIds) {
        if (itemIds == null) {
            throw new BadRequestException("Curriculum order must include itemIds for module: " + moduleId);
        }
        Set<String> expectedItemIds = activeItems(moduleId).stream()
                .map(item -> item.getId().toString())
                .collect(Collectors.toCollection(HashSet::new));
        Set<String> requestedItemIds = new HashSet<>();
        if (itemIds.size() != expectedItemIds.size()) {
            throw new BadRequestException("Curriculum order must include every active item exactly once for module: " + moduleId);
        }
        for (String itemId : itemIds) {
            if (!requestedItemIds.add(itemId)) {
                throw new BadRequestException("Duplicate item in curriculum order: " + itemId);
            }
            if (!expectedItemIds.contains(itemId)) {
                throw new BadRequestException("Unknown, archived, or cross-module item in curriculum order: " + itemId);
            }
        }
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
        String previousState = course.getReviewState();
        course.setReviewState("IN_REVIEW");
        course.setLastAuthoredBy(actorId);
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("IN_REVIEW"));
        recordReviewAudit(course, user, "SUBMIT_REVIEW", previousState, "IN_REVIEW", null, List.of());
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
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("APPROVED"));
        recordReviewAudit(course, user, "APPROVE", reviewState, "APPROVED", decisionNote(request), decisionChecklist(request));
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
        String note = requireDecisionNote(request, "Reject note is required");
        course.setReviewState("DRAFT");
        course.setLastAuthoredBy(String.valueOf(user.id()));
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> version.setState("DRAFT"));
        recordReviewAudit(course, user, "REJECT", reviewState, "DRAFT", note, decisionChecklist(request));
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
        recordReviewAudit(course, user, "PUBLISH", reviewState, "PUBLISHED",
                "Published v" + version.getVersionNo() + " learner snapshot", List.of());
        return toVersionDto(version);
    }

    private void publishModules(UUID courseId) {
        modules.findByCourseIdOrderByPositionAsc(courseId).stream()
                .filter(module -> !"ARCHIVED".equals(module.getStatus()))
                .forEach(module -> {
                    module.setStatus("PUBLISHED");
                    modules.save(module);
                });
    }

    /** Create a new module under the course draft. Position is appended after existing modules. */
    @Transactional
    public CourseDraftDto createModule(UUID courseId, CreateModuleRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        int nextPosition = modules.nextPosition(courseId);
        modules.save(new CourseModule(
                UUID.randomUUID(),
                courseId,
                request.title(),
                request.description(),
                nextPosition,
                "DRAFT"));
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto updateModule(UUID courseId, UUID moduleId, UpdateModuleRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        CourseModule module = requireActiveModule(courseId, moduleId);
        module.updateDraft(request.title(), request.description());
        modules.save(module);
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto duplicateModule(UUID courseId, UUID moduleId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        CourseModule source = requireActiveModule(courseId, moduleId);
        UUID copyModuleId = UUID.randomUUID();
        CourseModule copy = new CourseModule(
                copyModuleId,
                courseId,
                duplicateTitle(source.getTitle()),
                source.getDescription(),
                modules.nextPosition(courseId),
                "DRAFT");
        modules.save(copy);
        int itemPosition = 0;
        for (ModuleItem sourceItem : activeItems(moduleId)) {
            UUID copyItemId = UUID.randomUUID();
            items.save(new ModuleItem(
                    copyItemId,
                    copyModuleId,
                    sourceItem.getItemType(),
                    duplicateRefId(sourceItem, copyItemId),
                    duplicateTitle(sourceItem.getTitle()),
                    sourceItem.getDescription(),
                    sourceItem.getVideoMediaId(),
                    sourceItem.getDocumentMediaIds(),
                    sourceItem.getContentUrl(),
                    sourceItem.getEstimatedMinutes(),
                    itemPosition++,
                    sourceItem.isRequired()));
        }
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto archiveModule(UUID courseId, UUID moduleId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        CourseModule module = requireActiveModule(courseId, moduleId);
        for (ModuleItem item : activeItems(moduleId)) {
            item.archive(item.getPosition());
            items.save(item);
        }
        module.archive(module.getPosition());
        modules.save(module);
        compactModulePositions(courseId);
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    /** Create a new item inside a module, verifying the module belongs to the course. */
    @Transactional
    public CourseDraftDto createModuleItem(UUID courseId, UUID moduleId, CreateModuleItemRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        requireActiveModule(courseId, moduleId);
        int nextPosition = items.nextPosition(moduleId);
        UUID itemUuid = UUID.randomUUID();
        SanitizedItemInput sanitized = sanitizeItemInput(
                request.itemType(),
                request.refId(),
                request.videoMediaId(),
                request.documentMediaIds(),
                request.contentUrl());
        String refId = resolveRefId(
                itemUuid,
                sanitized.refId(),
                sanitized.itemType(),
                sanitized.videoMediaId(),
                sanitized.documentMediaIds(),
                sanitized.contentUrl());
        items.save(new ModuleItem(
                itemUuid,
                moduleId,
                sanitized.itemType(),
                refId,
                request.title(),
                request.description(),
                sanitized.videoMediaId(),
                sanitized.documentMediaIds(),
                sanitized.contentUrl(),
                request.estimatedMinutes(),
                nextPosition,
                request.required() == null ? Boolean.TRUE : request.required()));
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto updateModuleItem(UUID courseId, UUID moduleId, UUID itemId,
            UpdateModuleItemRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        requireActiveModule(courseId, moduleId);
        ModuleItem item = requireActiveItem(moduleId, itemId);
        SanitizedItemInput sanitized = sanitizeItemInput(
                request.itemType(),
                request.refId(),
                request.videoMediaId(),
                request.documentMediaIds(),
                request.contentUrl());
        String refId = resolveRefId(
                itemId,
                sanitized.refId(),
                sanitized.itemType(),
                sanitized.videoMediaId(),
                sanitized.documentMediaIds(),
                sanitized.contentUrl());
        item.updateDraft(
                sanitized.itemType(),
                refId,
                request.title(),
                request.description(),
                sanitized.videoMediaId(),
                sanitized.documentMediaIds(),
                sanitized.contentUrl(),
                request.estimatedMinutes(),
                request.required() == null ? item.isRequired() : request.required());
        items.save(item);
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto duplicateModuleItem(UUID courseId, UUID moduleId, UUID itemId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        requireActiveModule(courseId, moduleId);
        ModuleItem source = requireActiveItem(moduleId, itemId);
        UUID copyItemId = UUID.randomUUID();
        items.save(new ModuleItem(
                copyItemId,
                moduleId,
                source.getItemType(),
                duplicateRefId(source, copyItemId),
                duplicateTitle(source.getTitle()),
                source.getDescription(),
                source.getVideoMediaId(),
                source.getDocumentMediaIds(),
                source.getContentUrl(),
                source.getEstimatedMinutes(),
                items.nextPosition(moduleId),
                source.isRequired()));
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    @Transactional
    public CourseDraftDto archiveModuleItem(UUID courseId, UUID moduleId, UUID itemId, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        ensureMutableDraftVersion(courseId, user);
        requireActiveModule(courseId, moduleId);
        ModuleItem item = requireActiveItem(moduleId, itemId);
        item.archive(item.getPosition());
        items.save(item);
        compactItemPositions(moduleId);
        touchAuthoringDraft(courseId);
        return getDraft(courseId);
    }

    private String resolveRefId(UUID itemUuid, String refId, String itemType,
            UUID videoMediaId, List<String> documentMediaIds, String contentUrl) {
        if (refId != null && !refId.isBlank()) {
            return refId.trim();
        }
        if (videoMediaId != null) {
            return videoMediaId.toString();
        }
        if (contentUrl != null && !contentUrl.isBlank()) {
            return contentUrl.trim();
        }
        if (requiresExternalRef(normalizeItemType(itemType, videoMediaId, documentMediaIds, contentUrl))) {
            return "";
        }
        return itemUuid.toString();
    }

    private CourseModule requireActiveModule(UUID courseId, UUID moduleId) {
        CourseModule module = modules.findByIdAndCourseId(moduleId, courseId)
                .orElseThrow(() -> new NotFoundException("Module not found: " + moduleId));
        if ("ARCHIVED".equals(module.getStatus())) {
            throw new BadRequestException("Module is archived: " + moduleId);
        }
        return module;
    }

    private ModuleItem requireActiveItem(UUID moduleId, UUID itemId) {
        ModuleItem item = items.findByIdAndModuleId(itemId, moduleId)
                .orElseThrow(() -> new NotFoundException("Module item not found: " + itemId));
        if ("ARCHIVED".equals(item.getStatus())) {
            throw new BadRequestException("Module item is archived: " + itemId);
        }
        return item;
    }

    private List<CourseModule> activeModules(UUID courseId) {
        return modules.findByCourseIdOrderByPositionAsc(courseId).stream()
                .filter(module -> !"ARCHIVED".equals(module.getStatus()))
                .toList();
    }

    private List<ModuleItem> activeItems(UUID moduleId) {
        return items.findByModuleIdOrderByPositionAsc(moduleId).stream()
                .filter(item -> !"ARCHIVED".equals(item.getStatus()))
                .toList();
    }

    private String duplicateTitle(String value) {
        return "Copy of " + (isBlank(value) ? "Untitled" : value.trim());
    }

    private String duplicateRefId(ModuleItem source, UUID copyItemId) {
        if (isBlank(source.getItemId()) || source.getId().toString().equals(source.getItemId().trim())) {
            return copyItemId.toString();
        }
        return source.getItemId();
    }

    private void compactModulePositions(UUID courseId) {
        int position = 0;
        for (CourseModule module : activeModules(courseId)) {
            module.setPosition(position++);
            modules.saveAndFlush(module);
        }
    }

    private void compactItemPositions(UUID moduleId) {
        int position = 0;
        for (ModuleItem item : activeItems(moduleId)) {
            item.setPosition(position++);
            items.saveAndFlush(item);
        }
    }

    private SanitizedItemInput sanitizeItemInput(String itemType, String refId, UUID videoMediaId,
            List<String> documentMediaIds, String contentUrl) {
        String normalizedType = isBlank(itemType) ? "LESSON" : itemType.trim().toUpperCase();
        return switch (normalizedType) {
            case "VIDEO" -> new SanitizedItemInput("VIDEO", refId, videoMediaId, List.of(), null);
            case "DOCUMENT", "PDF", "MATERIAL" -> new SanitizedItemInput(
                    normalizedType,
                    refId,
                    null,
                    documentMediaIds == null ? List.of() : List.copyOf(documentMediaIds),
                    contentUrl);
            case "LINK" -> new SanitizedItemInput("LINK", refId, null, List.of(), contentUrl);
            case "QUIZ", "ASSIGNMENT" -> new SanitizedItemInput(normalizedType, refId, null, List.of(), null);
            default -> new SanitizedItemInput(normalizedType, refId, null, List.of(), contentUrl);
        };
    }

    private int temporaryPositionOffset(UUID courseId) {
        int max = 0;
        for (CourseModule module : activeModules(courseId)) {
            max = Math.max(max, module.getPosition());
            for (ModuleItem item : activeItems(module.getId())) {
                max = Math.max(max, item.getPosition());
            }
        }
        return max + 10_000;
    }

    private void ensureReviewable(UUID courseId) {
        List<CourseModule> courseModules = modules.findByCourseIdOrderByPositionAsc(courseId).stream()
                .filter(module -> !"ARCHIVED".equals(module.getStatus()))
                .toList();
        if (courseModules.isEmpty()) {
            throw new BadRequestException("Course must have at least one chapter before review");
        }
        List<String> issues = new ArrayList<>();
        int requiredItems = 0;
        for (CourseModule module : courseModules) {
            List<ModuleItem> moduleItems = items.findByModuleIdOrderByPositionAsc(module.getId()).stream()
                    .filter(item -> !"ARCHIVED".equals(item.getStatus()))
                    .toList();
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
        Course course = findCourse(courseId);
        requireReviewVisibility(course, user);
        return listVersions(courseId);
    }

    public List<CourseReviewAuditDto> listReviewHistory(UUID courseId, CurrentUser user) {
        Course course = findCourse(courseId);
        requireReviewVisibility(course, user);
        return reviewAuditLogs.findByCourseIdOrderByCreatedAtDesc(courseId).stream()
                .map(this::toReviewAuditDto)
                .toList();
    }

    public List<CourseReviewQueueItemDto> listReviewQueue(CurrentUser user) {
        requireAuthenticated(user);
        return courses.findByReviewStateOrderByUpdatedAtDescTitleAsc("IN_REVIEW").stream()
                .filter(course -> canViewReviewQueue(course, user))
                .map(this::toReviewQueueItemDto)
                .toList();
    }

    public CourseVersionDiffDto diffDraftWithPublished(UUID courseId, Integer publishedVersionNo, CurrentUser user) {
        Course course = findCourse(courseId);
        requireReviewVisibility(course, user);
        CourseVersion published = resolvePublishedVersion(courseId, publishedVersionNo);
        return buildVersionDiff(course, published, readSnapshot(published), listModules(courseId));
    }

    @Transactional
    public CourseDraftDto rollbackPublishedVersionToDraft(UUID courseId, int versionNo,
            RollbackVersionRequestDto request, CurrentUser user) {
        requireOwnerOrAdmin(courseId, user);
        Course course = findCourse(courseId);
        if (request != null
                && request.expectedCurrentVersionNo() != null
                && request.expectedCurrentVersionNo() != course.getCurrentVersionNo()) {
            throw new BadRequestException("Course draft version changed; reload before rollback");
        }

        CourseVersion source = resolvePublishedVersion(courseId, versionNo);
        List<ModuleOutlineDto> snapshotModules = readSnapshot(source);
        validatePublishSnapshot(snapshotModules);

        int targetVersionNo = versions.nextVersionNo(courseId);
        createVersionRow(
                courseId,
                targetVersionNo,
                "DRAFT",
                String.valueOf(user.id()),
                rollbackVersionNote(source.getVersionNo(), request));

        applySnapshotToWorkingDraft(courseId, snapshotModules);
        course.setCurrentVersionNo(targetVersionNo);
        course.setReviewState("DRAFT");
        course.setLastAuthoredBy(String.valueOf(user.id()));
        recordReviewAudit(course, user, "ROLLBACK_TO_DRAFT", "PUBLISHED", "DRAFT",
                rollbackAuditNote(source.getVersionNo(), targetVersionNo, request),
                List.of("source:v" + source.getVersionNo(), "target:v" + targetVersionNo));
        return getDraft(courseId);
    }

    private CourseVersion resolvePublishedVersion(UUID courseId, Integer publishedVersionNo) {
        CourseVersion version = publishedVersionNo == null
                ? versions.findByCourseIdAndStateOrderByVersionNoDesc(courseId, "PUBLISHED").stream()
                        .findFirst()
                        .orElseThrow(() -> new BadRequestException("Course has no published version snapshot"))
                : versions.findByCourseIdAndVersionNo(courseId, publishedVersionNo)
                        .orElseThrow(() -> new NotFoundException("Course version not found: v" + publishedVersionNo));
        if (!"PUBLISHED".equals(version.getState())) {
            throw new BadRequestException("Only PUBLISHED versions can be compared or rolled back");
        }
        if (isBlank(version.getSnapshot())) {
            throw new BadRequestException("Published version has an empty curriculum snapshot");
        }
        return version;
    }

    private List<ModuleOutlineDto> readSnapshot(CourseVersion version) {
        try {
            List<ModuleOutlineDto> snapshot = objectMapper.readValue(
                    version.getSnapshot(),
                    new TypeReference<List<ModuleOutlineDto>>() {
                    });
            return snapshot == null ? List.of() : snapshot;
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to read course version snapshot", ex);
        }
    }

    private CourseVersionDiffDto buildVersionDiff(Course course, CourseVersion published,
            List<ModuleOutlineDto> publishedModules, List<ModuleOutlineDto> draftModules) {
        DiffCounters counters = new DiffCounters();
        List<CourseVersionDiffChangeDto> changes = new ArrayList<>();

        Map<String, ModuleOutlineDto> baseModules = modulesById(publishedModules);
        Map<String, ModuleOutlineDto> targetModules = modulesById(draftModules);
        for (ModuleOutlineDto module : publishedModules) {
            if (!targetModules.containsKey(module.moduleId())) {
                counters.removedModules++;
                changes.add(diffChange("MODULE", "REMOVED", module.moduleId(), null, module.title(), null, module.title(), null));
            }
        }
        for (ModuleOutlineDto module : draftModules) {
            ModuleOutlineDto base = baseModules.get(module.moduleId());
            if (base == null) {
                counters.addedModules++;
                changes.add(diffChange("MODULE", "ADDED", module.moduleId(), null, module.title(), null, null, module.title()));
                continue;
            }
            boolean changed = false;
            changed |= addChangeIfChanged(changes, "MODULE", module.moduleId(), null, module.title(), "title", base.title(), module.title());
            changed |= addChangeIfChanged(changes, "MODULE", module.moduleId(), null, module.title(), "description", base.description(), module.description());
            if (base.position() != module.position()) {
                counters.movedModules++;
                changes.add(diffChange("MODULE", "MOVED", module.moduleId(), null, module.title(), "position",
                        String.valueOf(base.position()), String.valueOf(module.position())));
            }
            if (changed) {
                counters.changedModules++;
            }
        }

        Map<String, ItemRef> baseItems = itemsById(publishedModules);
        Map<String, ItemRef> targetItems = itemsById(draftModules);
        for (ItemRef item : baseItems.values()) {
            if (!targetItems.containsKey(item.item().itemId())) {
                counters.removedItems++;
                if (item.item().required()) {
                    counters.requiredItemsRemoved++;
                }
                changes.add(diffChange("ITEM", "REMOVED", item.moduleId(), item.item().itemId(), item.item().title(),
                        null, item.item().title(), null));
            }
        }
        for (ItemRef item : targetItems.values()) {
            ItemRef base = baseItems.get(item.item().itemId());
            if (base == null) {
                counters.addedItems++;
                if (item.item().required()) {
                    counters.requiredItemsAdded++;
                }
                changes.add(diffChange("ITEM", "ADDED", item.moduleId(), item.item().itemId(), item.item().title(),
                        null, null, item.item().title()));
                continue;
            }
            boolean changed = false;
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "itemType", base.item().itemType(), item.item().itemType());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "refId", base.item().refId(), item.item().refId());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "title", base.item().title(), item.item().title());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "description", base.item().description(), item.item().description());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "videoMediaId", base.item().videoMediaId(), item.item().videoMediaId());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "documentMediaIds", base.item().documentMediaIds(), item.item().documentMediaIds());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "contentUrl", base.item().contentUrl(), item.item().contentUrl());
            changed |= addChangeIfChanged(changes, "ITEM", item.moduleId(), item.item().itemId(), item.item().title(),
                    "estimatedMinutes", base.item().estimatedMinutes(), item.item().estimatedMinutes());
            if (base.item().required() != item.item().required()) {
                changed = true;
                if (item.item().required()) {
                    counters.requiredItemsAdded++;
                } else {
                    counters.requiredItemsRemoved++;
                }
                changes.add(diffChange("ITEM", "CHANGED", item.moduleId(), item.item().itemId(), item.item().title(),
                        "required", String.valueOf(base.item().required()), String.valueOf(item.item().required())));
            }
            if (!Objects.equals(base.moduleId(), item.moduleId())
                    || base.item().position() != item.item().position()) {
                counters.movedItems++;
                changes.add(diffChange("ITEM", "MOVED", item.moduleId(), item.item().itemId(), item.item().title(),
                        "position", base.moduleId() + "#" + base.item().position(),
                        item.moduleId() + "#" + item.item().position()));
            }
            if (changed) {
                counters.changedItems++;
            }
        }

        return new CourseVersionDiffDto(
                course.getId().toString(),
                course.getCurrentVersionNo(),
                published.getVersionNo(),
                "Published v" + published.getVersionNo(),
                "Draft v" + course.getCurrentVersionNo(),
                counters.addedModules,
                counters.removedModules,
                counters.changedModules,
                counters.movedModules,
                counters.addedItems,
                counters.removedItems,
                counters.changedItems,
                counters.movedItems,
                counters.requiredItemsAdded,
                counters.requiredItemsRemoved,
                changes,
                diffWarnings(counters, changes));
    }

    private Map<String, ModuleOutlineDto> modulesById(List<ModuleOutlineDto> modules) {
        Map<String, ModuleOutlineDto> result = new LinkedHashMap<>();
        for (ModuleOutlineDto module : modules == null ? List.<ModuleOutlineDto>of() : modules) {
            if (!isBlank(module.moduleId())) {
                result.putIfAbsent(module.moduleId(), module);
            }
        }
        return result;
    }

    private Map<String, ItemRef> itemsById(List<ModuleOutlineDto> modules) {
        Map<String, ItemRef> result = new LinkedHashMap<>();
        for (ModuleOutlineDto module : modules == null ? List.<ModuleOutlineDto>of() : modules) {
            for (ItemOutlineDto item : module.items() == null ? List.<ItemOutlineDto>of() : module.items()) {
                if (!isBlank(item.itemId())) {
                    result.putIfAbsent(item.itemId(), new ItemRef(module.moduleId(), item));
                }
            }
        }
        return result;
    }

    private boolean addChangeIfChanged(List<CourseVersionDiffChangeDto> changes, String scope,
            String moduleId, String itemId, String title, String field, Object fromValue, Object toValue) {
        if (Objects.equals(normalizedDiffValue(fromValue), normalizedDiffValue(toValue))) {
            return false;
        }
        changes.add(diffChange(scope, "CHANGED", moduleId, itemId, title, field,
                diffValue(fromValue), diffValue(toValue)));
        return true;
    }

    private CourseVersionDiffChangeDto diffChange(String scope, String changeType, String moduleId,
            String itemId, String title, String field, String fromValue, String toValue) {
        return new CourseVersionDiffChangeDto(scope, changeType, moduleId, itemId, title, field, fromValue, toValue);
    }

    private List<String> diffWarnings(DiffCounters counters, List<CourseVersionDiffChangeDto> changes) {
        List<String> warnings = new ArrayList<>();
        if (counters.requiredItemsRemoved > 0) {
            warnings.add(counters.requiredItemsRemoved + " required item removed or made optional");
        }
        if (counters.requiredItemsAdded > 0) {
            warnings.add(counters.requiredItemsAdded + " required item added or made mandatory");
        }
        boolean sourceChanged = changes.stream()
                .anyMatch(change -> "ITEM".equals(change.scope())
                        && ("refId".equals(change.field()) || "itemType".equals(change.field())));
        if (sourceChanged) {
            warnings.add("Assessment/source links changed; verify quiz, assignment and completion rules before publish");
        }
        return warnings;
    }

    private String normalizedDiffValue(Object value) {
        if (value instanceof List<?> list) {
            return list.stream()
                    .map(item -> item == null ? "" : String.valueOf(item).trim())
                    .collect(Collectors.joining("|"));
        }
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String diffValue(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof List<?> list) {
            return list.stream()
                    .map(String::valueOf)
                    .collect(Collectors.joining(", "));
        }
        return String.valueOf(value);
    }

    private void applySnapshotToWorkingDraft(UUID courseId, List<ModuleOutlineDto> snapshotModules) {
        List<CourseModule> existingModules = modules.findByCourseIdOrderByPositionAsc(courseId);
        List<ModuleItem> existingItems = existingModules.stream()
                .flatMap(module -> items.findByModuleIdOrderByPositionAsc(module.getId()).stream())
                .toList();
        archiveCurrentDraftRows(existingModules, existingItems);

        Map<UUID, CourseModule> existingModulesById = existingModules.stream()
                .collect(Collectors.toMap(CourseModule::getId, Function.identity(), (left, right) -> left));
        Map<UUID, ModuleItem> existingItemsById = existingItems.stream()
                .collect(Collectors.toMap(ModuleItem::getId, Function.identity(), (left, right) -> left));
        for (ModuleOutlineDto snapshotModule : snapshotModules) {
            UUID moduleId = snapshotUuid(snapshotModule.moduleId(), "moduleId");
            CourseModule module = existingModulesById.get(moduleId);
            if (module == null) {
                module = new CourseModule(
                        moduleId,
                        courseId,
                        snapshotModule.title(),
                        snapshotModule.description(),
                        snapshotModule.position(),
                        "DRAFT");
            } else {
                module.restoreDraft(snapshotModule.title(), snapshotModule.description(), snapshotModule.position());
            }
            modules.saveAndFlush(module);
            restoreSnapshotItems(moduleId, snapshotModule.items(), existingItemsById);
        }
    }

    private void archiveCurrentDraftRows(List<CourseModule> existingModules, List<ModuleItem> existingItems) {
        for (CourseModule module : existingModules) {
            module.archive(module.getPosition());
            modules.saveAndFlush(module);
        }
        for (ModuleItem item : existingItems) {
            item.archive(item.getPosition());
            items.saveAndFlush(item);
        }
    }

    private void restoreSnapshotItems(UUID moduleId, List<ItemOutlineDto> snapshotItems,
            Map<UUID, ModuleItem> existingItemsById) {
        for (ItemOutlineDto snapshotItem : snapshotItems == null ? List.<ItemOutlineDto>of() : snapshotItems) {
            UUID itemId = snapshotUuid(snapshotItem.itemId(), "itemId");
            ModuleItem item = existingItemsById.get(itemId);
            String refId = isBlank(snapshotItem.refId()) ? itemId.toString() : snapshotItem.refId().trim();
            String itemType = isBlank(snapshotItem.itemType()) ? "LESSON" : snapshotItem.itemType().trim();
            UUID videoMediaId = nullableUuid(snapshotItem.videoMediaId(), "videoMediaId");
            List<String> documentMediaIds = snapshotItem.documentMediaIds() == null
                    ? List.of()
                    : snapshotItem.documentMediaIds();
            if (item == null) {
                item = new ModuleItem(
                        itemId,
                        moduleId,
                        itemType,
                        refId,
                        snapshotItem.title(),
                        snapshotItem.description(),
                        videoMediaId,
                        documentMediaIds,
                        snapshotItem.contentUrl(),
                        snapshotItem.estimatedMinutes(),
                        snapshotItem.position(),
                        snapshotItem.required());
            } else {
                item.restoreDraft(
                        moduleId,
                        itemType,
                        refId,
                        snapshotItem.title(),
                        snapshotItem.description(),
                        videoMediaId,
                        documentMediaIds,
                        snapshotItem.contentUrl(),
                        snapshotItem.estimatedMinutes(),
                        snapshotItem.position(),
                        snapshotItem.required());
            }
            items.saveAndFlush(item);
        }
    }

    private UUID snapshotUuid(String value, String fieldName) {
        if (isBlank(value)) {
            throw new BadRequestException("Published snapshot has missing " + fieldName);
        }
        try {
            return UUID.fromString(value.trim());
        } catch (RuntimeException ex) {
            throw new BadRequestException("Published snapshot has invalid " + fieldName + ": " + value);
        }
    }

    private UUID nullableUuid(String value, String fieldName) {
        if (isBlank(value)) {
            return null;
        }
        try {
            return UUID.fromString(value.trim());
        } catch (RuntimeException ex) {
            throw new BadRequestException("Published snapshot has invalid " + fieldName + ": " + value);
        }
    }

    private String rollbackVersionNote(int sourceVersionNo, RollbackVersionRequestDto request) {
        String note = request == null ? null : normalizeNote(request.note());
        return note == null ? "Rollback from published v" + sourceVersionNo : "Rollback from published v" + sourceVersionNo + ": " + note;
    }

    private String rollbackAuditNote(int sourceVersionNo, int targetVersionNo, RollbackVersionRequestDto request) {
        String note = request == null ? null : normalizeNote(request.note());
        String prefix = "Rollback published v" + sourceVersionNo + " into draft v" + targetVersionNo;
        return note == null ? prefix : prefix + ": " + note;
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

    private void ensureMutableDraftVersion(UUID courseId, CurrentUser user) {
        Course course = findCourse(courseId);
        CourseVersion current = versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .orElseThrow(() -> new NotFoundException("Course version not found: " + courseId));
        if (!"PUBLISHED".equals(current.getState())) {
            return;
        }
        int nextVersionNo = versions.nextVersionNo(courseId);
        createVersionRow(
                courseId,
                nextVersionNo,
                "DRAFT",
                String.valueOf(user.id()),
                "Draft fork from published v" + current.getVersionNo());
        course.setCurrentVersionNo(nextVersionNo);
        course.setLastAuthoredBy(String.valueOf(user.id()));
        course.setReviewState("DRAFT");
        recordReviewAudit(course, user, "CREATE_DRAFT", "PUBLISHED", "DRAFT",
                "Created editable draft v" + nextVersionNo + " from published v" + current.getVersionNo(), List.of());
    }

    private void touchAuthoringDraft(UUID courseId) {
        Course course = findCourse(courseId);
        course.setReviewState("DRAFT");
        versions.findByCourseIdAndVersionNo(courseId, course.getCurrentVersionNo())
                .ifPresent(version -> {
                    if (!"PUBLISHED".equals(version.getState())) {
                        version.setState("DRAFT");
                    }
                });
        course.touch();
    }

    private CourseVersionDto toVersionDto(CourseVersion version) {
        return mapper.toDto(version);
    }

    private CourseReviewAuditDto toReviewAuditDto(CourseReviewAuditLog log) {
        return new CourseReviewAuditDto(
                log.getId().toString(),
                log.getCourseId().toString(),
                log.getVersionNo(),
                log.getActorId(),
                log.getActorRole(),
                log.getAction(),
                log.getFromState(),
                log.getToState(),
                log.getNote(),
                log.getChecklist(),
                log.getCreatedAt());
    }

    private CourseReviewQueueItemDto toReviewQueueItemDto(Course course) {
        QueueContentStats stats = queueContentStats(course.getId());
        CourseReviewAuditLog submitted = latestAudit(course.getId(), "SUBMIT_REVIEW");
        return new CourseReviewQueueItemDto(
                course.getId().toString(),
                course.getTitle(),
                course.getSlug(),
                course.getSummary(),
                course.getStatus(),
                course.getReviewState(),
                course.getCurrentVersionNo(),
                course.getOwnerId(),
                course.getDepartmentId().toString(),
                course.getLastAuthoredBy(),
                stats.moduleCount(),
                stats.itemCount(),
                submitted == null ? null : submitted.getActorId(),
                submitted == null ? null : submitted.getCreatedAt());
    }

    private QueueContentStats queueContentStats(UUID courseId) {
        int moduleCount = 0;
        int itemCount = 0;
        for (CourseModule module : modules.findByCourseIdOrderByPositionAsc(courseId)) {
            if ("ARCHIVED".equals(module.getStatus())) {
                continue;
            }
            moduleCount++;
            itemCount += (int) items.findByModuleIdOrderByPositionAsc(module.getId()).stream()
                    .filter(item -> !"ARCHIVED".equals(item.getStatus()))
                    .count();
        }
        return new QueueContentStats(moduleCount, itemCount);
    }

    private CourseReviewAuditLog latestAudit(UUID courseId, String action) {
        return reviewAuditLogs.findByCourseIdOrderByCreatedAtDesc(courseId).stream()
                .filter(log -> action.equals(log.getAction()))
                .findFirst()
                .orElse(null);
    }

    private void recordReviewAudit(Course course, CurrentUser user, String action, String fromState, String toState,
            String note, List<String> checklist) {
        reviewAuditLogs.save(new CourseReviewAuditLog(
                UUID.randomUUID(),
                course.getId(),
                course.getCurrentVersionNo(),
                String.valueOf(user.id()),
                user.role(),
                action,
                fromState,
                toState,
                normalizeNote(note),
                normalizeChecklist(checklist)));
    }

    private String decisionNote(ReviewDecisionRequestDto request) {
        return request == null ? null : normalizeNote(request.note());
    }

    private String requireDecisionNote(ReviewDecisionRequestDto request, String message) {
        String note = decisionNote(request);
        if (note == null) {
            throw new BadRequestException(message);
        }
        return note;
    }

    private List<String> decisionChecklist(ReviewDecisionRequestDto request) {
        return request == null ? List.of() : normalizeChecklist(request.checklist());
    }

    private String normalizeNote(String value) {
        return isBlank(value) ? null : value.trim();
    }

    private List<String> normalizeChecklist(List<String> checklist) {
        if (checklist == null) {
            return List.of();
        }
        return checklist.stream()
                .filter(item -> !isBlank(item))
                .map(String::trim)
                .distinct()
                .toList();
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
        requireAuthenticated(user);
        if (isPlatformAdmin(user)) {
            return;
        }
        boolean isOwner = String.valueOf(user.id()).equals(course.getOwnerId());
        if (!isOwner && hasScopedReviewerRole(course, user)) {
            return;
        }
        throw new ForbiddenException("Course review requires an independent reviewer");
    }

    private void requireReviewVisibility(Course course, CurrentUser user) {
        requireAuthenticated(user);
        boolean isOwner = String.valueOf(user.id()).equals(course.getOwnerId());
        if (isOwner || isPlatformAdmin(user) || hasScopedReviewerRole(course, user)) {
            return;
        }
        throw new ForbiddenException("Caller is not allowed to view course review history");
    }

    private boolean canViewReviewQueue(Course course, CurrentUser user) {
        return isPlatformAdmin(user)
                || String.valueOf(user.id()).equals(course.getOwnerId())
                || hasScopedReviewerRole(course, user);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
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

    private record QueueContentStats(int moduleCount, int itemCount) {
    }

    private record ItemRef(String moduleId, ItemOutlineDto item) {
    }

    private record SanitizedItemInput(String itemType, String refId, UUID videoMediaId,
                                      List<String> documentMediaIds, String contentUrl) {
    }

    private static final class DiffCounters {
        private int addedModules;
        private int removedModules;
        private int changedModules;
        private int movedModules;
        private int addedItems;
        private int removedItems;
        private int changedItems;
        private int movedItems;
        private int requiredItemsAdded;
        private int requiredItemsRemoved;
    }
}
