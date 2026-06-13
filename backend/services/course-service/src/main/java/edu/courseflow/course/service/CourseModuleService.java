package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.CompleteItemProgressRequestDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseDtos.PresignedDownloadDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.MissingRequirementDto;
import edu.courseflow.course.dto.CourseProgressDto.ModuleProgressSummaryDto;
import edu.courseflow.course.dto.CourseProgressDto.ProgressBreakdownDto;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.dto.RecordItemCompletionRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.LearnerItemProgress;
import edu.courseflow.course.model.LearnerModuleProgress;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.model.OutboxEvent;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.LearnerItemProgressJpaRepository;
import edu.courseflow.course.repository.LearnerModuleProgressJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import edu.courseflow.course.repository.ModulePrerequisiteJpaRepository;
import edu.courseflow.course.repository.OutboxEventJpaRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;

@Service
public class CourseModuleService {

    private final CourseModuleJpaRepository modules;
    private final ModuleItemJpaRepository items;
    private final CourseVersionJpaRepository versions;
    private final ModulePrerequisiteJpaRepository prerequisites;
    private final LearnerModuleProgressJpaRepository progressRepository;
    private final LearnerItemProgressJpaRepository itemProgressRepository;
    private final OutboxEventJpaRepository outbox;
    private final ObjectMapper objectMapper;
    private final CourseMapper mapper;
    private final CourseAccessClient courseAccess;
    private final RestClient mediaClient;
    private final String serviceToken;

    public CourseModuleService(CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            CourseVersionJpaRepository versions,
            ModulePrerequisiteJpaRepository prerequisites,
            LearnerModuleProgressJpaRepository progressRepository,
            LearnerItemProgressJpaRepository itemProgressRepository,
            OutboxEventJpaRepository outbox,
            ObjectMapper objectMapper,
            CourseMapper mapper,
            CourseAccessClient courseAccess,
            RestClient.Builder restClientBuilder,
            @Value("${courseflow.content.media-service-url:http://localhost:8091}") String mediaServiceUrl,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.modules = modules;
        this.items = items;
        this.versions = versions;
        this.prerequisites = prerequisites;
        this.progressRepository = progressRepository;
        this.itemProgressRepository = itemProgressRepository;
        this.outbox = outbox;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.courseAccess = courseAccess;
        this.mediaClient = restClientBuilder.baseUrl(mediaServiceUrl).build();
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    public List<CourseModuleDto> listModules(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseAccess(user, courseId);
        return publishedCurriculum(courseId).modules().stream()
                .map(this::toCourseModuleDto)
                .toList();
    }

    public PresignedDownloadDto downloadPublishedMedia(UUID courseId, UUID mediaId, CurrentUser user) {
        courseAccess.requireCourseAccess(user, courseId);
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        if (!curriculum.containsDocumentMedia(mediaId)) {
            throw new ForbiddenException("Media asset is not part of the published course curriculum");
        }
        if (serviceToken.isBlank()) {
            throw new IllegalStateException("Media download service token is not configured");
        }
        return mediaClient.get()
                .uri("/internal/media/assets/{mediaId}/download-url/trusted", mediaId)
                .header(CourseAccessClient.SERVICE_TOKEN_HEADER, serviceToken)
                .retrieve()
                .body(PresignedDownloadDto.class);
    }

    @Transactional
    public ModuleProgressDto completeModule(UUID courseId, UUID moduleId, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        // The learner records progress for themselves: studentId comes from the token, not the body.
        String studentId = String.valueOf(user.id());

        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        PublishedModule module = curriculum.findModule(moduleId)
                .orElseThrow(() -> new NotFoundException("Published module not found: " + moduleId));

        requireModulePrerequisites(courseId, moduleId, studentId);

        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        List<String> missingItems = module.items().stream()
                .filter(PublishedItem::required)
                .filter(item -> !isItemCompleted(item.id(), progressByItemId))
                .map(PublishedItem::title)
                .toList();
        if (!missingItems.isEmpty()) {
            throw new BadRequestException("Required module items not completed: " + missingItems);
        }

        boolean alreadyComplete = computeProgress(courseId, studentId).completed();

        Instant completedAt = Instant.now();
        LearnerModuleProgress progress = saveModuleCompletion(courseId, moduleId, studentId, completedAt);

        CourseProgressDto courseProgress = computeProgress(courseId, studentId);
        if (courseProgress.completed() && !alreadyComplete) {
            outbox(courseId, "course.completed", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "courseId", courseId.toString(),
                    "studentId", studentId,
                    "completedAt", completedAt.toString())));
        }

        return mapper.toDto(progress);
    }

    @Transactional
    public ItemProgressDto completeItem(UUID courseId, UUID moduleId, UUID itemId,
                                        CompleteItemProgressRequestDto request,
                                        CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        String studentId = String.valueOf(user.id());

        PublishedItem item = publishedCurriculum(courseId).findItem(moduleId, itemId)
                .orElseThrow(() -> new NotFoundException("Published module item not found: " + itemId));

        if (!isLearnerSelfCompletable(item)) {
            throw new BadRequestException("Item type " + normalizeItemType(item)
                    + " requires verified completion from its source service");
        }
        return recordItemCompletion(courseId, moduleId, item, studentId, learnerProgressType(item), Instant.now());
    }

    @Transactional
    public ItemProgressDto recordVerifiedItemCompletion(UUID courseId, UUID moduleId, UUID itemId,
                                                        RecordItemCompletionRequestDto request) {
        if (request == null || isBlank(request.studentId())) {
            throw new BadRequestException("studentId is required");
        }
        String studentId = request.studentId().trim();
        PublishedItem item = publishedCurriculum(courseId).findItem(moduleId, itemId)
                .orElseThrow(() -> new NotFoundException("Published module item not found: " + itemId));
        validateVerifiedSource(item, request);
        Instant completedAt = request.completedAt() == null ? Instant.now() : request.completedAt();
        return recordItemCompletion(courseId, moduleId, item, studentId, verifiedProgressType(item), completedAt);
    }

    @Transactional
    public ItemProgressDto recordVerifiedItemCompletion(UUID courseId, RecordItemCompletionRequestDto request) {
        if (request == null || isBlank(request.studentId())) {
            throw new BadRequestException("studentId is required");
        }
        if (isBlank(request.sourceId())) {
            throw new BadRequestException("sourceId is required");
        }
        if (isBlank(request.sourceType())) {
            throw new BadRequestException("sourceType is required");
        }
        PublishedItem item = findPublishedItemByVerifiedSource(
                courseId,
                request.sourceType().trim().toUpperCase(),
                request.sourceId().trim())
                .orElseThrow(() -> new NotFoundException("Published module item not found for source: "
                        + request.sourceType() + "/" + request.sourceId()));
        validateVerifiedSource(item, request);
        Instant completedAt = request.completedAt() == null ? Instant.now() : request.completedAt();
        return recordItemCompletion(courseId, item.moduleId(), item, request.studentId().trim(),
                verifiedProgressType(item), completedAt);
    }

    private ItemProgressDto recordItemCompletion(UUID courseId, UUID moduleId, PublishedItem item,
                                                 String studentId, String progressType, Instant completedAt) {
        requireModulePrerequisites(courseId, moduleId, studentId);
        boolean alreadyComplete = computeProgress(courseId, studentId).completed();
        LearnerItemProgress progress = itemProgressRepository.findByItemIdAndStudentId(item.id(), studentId)
                .orElseGet(() -> new LearnerItemProgress(UUID.randomUUID(), courseId, moduleId, item.id(), studentId));
        progress.complete(progressType, completedAt);
        progress = itemProgressRepository.save(progress);

        if (isModuleCompleteByItems(courseId, moduleId, studentId)) {
            saveModuleCompletion(courseId, moduleId, studentId, completedAt);
        }

        CourseProgressDto courseProgress = computeProgress(courseId, studentId);
        if (courseProgress.completed() && !alreadyComplete) {
            outbox(courseId, "course.completed", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "courseId", courseId.toString(),
                    "studentId", studentId,
                    "completedAt", completedAt.toString())));
        }

        return toItemProgressDto(item, progress);
    }

    /**
     * Course-level completion for a learner: percentage of required items in published modules
     * that are completed. Module completion is derived from all required items in that module,
     * preventing a learner from completing a course by marking chapters without doing lessons.
     */
    public CourseProgressDto progress(UUID courseId, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        return computeProgress(courseId, String.valueOf(user.id()));
    }

    CourseProgressDto computeProgress(UUID courseId, String studentId) {
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        List<PublishedModule> courseModules = curriculum.modules();
        List<PublishedItem> courseItems = curriculum.items();
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));

        List<ModuleProgressSummaryDto> moduleSummaries = courseModules.stream()
                .map(module -> toModuleSummary(module, courseItems, progressByItemId))
                .toList();
        int totalModules = courseModules.size();
        int completedModules = (int) moduleSummaries.stream().filter(ModuleProgressSummaryDto::completed).count();
        int totalItems = courseItems.size();
        int completedItems = (int) courseItems.stream()
                .filter(item -> isItemCompleted(item.id(), progressByItemId))
                .count();
        int totalRequiredItems = (int) courseItems.stream().filter(PublishedItem::required).count();
        int completedRequiredItems = (int) courseItems.stream()
                .filter(PublishedItem::required)
                .filter(item -> isItemCompleted(item.id(), progressByItemId))
                .count();
        int percent = totalRequiredItems == 0
                ? 0
                : (int) Math.round((completedRequiredItems * 100.0) / totalRequiredItems);
        boolean completed = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;

        List<ProgressBreakdownDto> breakdown = breakdown(courseItems, progressByItemId);
        List<ItemProgressDto> itemProgress = courseItems.stream()
                .map(item -> toItemProgressDto(item, progressByItemId.get(item.id())))
                .toList();
        List<MissingRequirementDto> missingRequirements = courseItems.stream()
                .filter(PublishedItem::required)
                .filter(item -> !isItemCompleted(item.id(), progressByItemId))
                .map(item -> new MissingRequirementDto(
                        item.id().toString(),
                        item.moduleId().toString(),
                        normalizeItemType(item),
                        item.title()))
                .toList();

        return new CourseProgressDto(
                courseId.toString(),
                studentId,
                totalModules,
                completedModules,
                totalItems,
                completedItems,
                totalRequiredItems,
                completedRequiredItems,
                percent,
                completed,
                breakdown,
                moduleSummaries,
                itemProgress,
                missingRequirements);
    }

    private void outbox(UUID aggregateId, String eventType, String payload) {
        outbox.save(new OutboxEvent(aggregateId, "course", eventType, payload));
    }

    private Optional<PublishedItem> findPublishedItemByVerifiedSource(UUID courseId, String sourceType, String sourceId) {
        return publishedCurriculum(courseId).items().stream()
                .filter(item -> sourceType.equals(normalizeItemType(item)))
                .filter(item -> sourceMatches(item, sourceId))
                .findFirst();
    }

    private PublishedCurriculum publishedCurriculum(UUID courseId) {
        List<CourseVersion> publishedVersions = versions.findByCourseIdAndStateOrderByVersionNoDesc(courseId, "PUBLISHED");
        if (publishedVersions.isEmpty()) {
            throw new BadRequestException("Published course has no frozen curriculum snapshot");
        }
        String snapshot = publishedVersions.get(0).getSnapshot();
        if (snapshot == null || snapshot.isBlank()) {
            throw new BadRequestException("Published course has an empty curriculum snapshot");
        }
        PublishedCurriculum curriculum = PublishedCurriculum.fromSnapshot(readSnapshot(snapshot));
        validatePublishedCurriculum(curriculum);
        return curriculum;
    }

    private void validatePublishedCurriculum(PublishedCurriculum curriculum) {
        if (curriculum.modules().isEmpty()) {
            throw new BadRequestException("Published course snapshot has no modules");
        }
        if (curriculum.items().stream().noneMatch(PublishedItem::required)) {
            throw new BadRequestException("Published course snapshot has no required items");
        }
    }

    private List<ModuleOutlineDto> readSnapshot(String snapshot) {
        try {
            return objectMapper.readValue(snapshot, new TypeReference<List<ModuleOutlineDto>>() {
            });
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to read published course snapshot", ex);
        }
    }

    private CourseModuleDto toCourseModuleDto(PublishedModule module) {
        return new CourseModuleDto(
                module.id().toString(),
                module.title(),
                module.description(),
                module.position(),
                module.status(),
                module.items().stream().map(this::toModuleItemDto).toList());
    }

    private ModuleItemDto toModuleItemDto(PublishedItem item) {
        return new ModuleItemDto(
                item.id().toString(),
                item.itemType(),
                item.refId(),
                item.title(),
                item.description(),
                item.videoMediaId(),
                item.documentMediaIds(),
                item.contentUrl(),
                item.estimatedMinutes(),
                item.position(),
                item.required());
    }

    private static UUID snapshotUuid(String value, String fieldName) {
        try {
            return UUID.fromString(value);
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException("Published course snapshot has invalid " + fieldName + ": " + value, ex);
        }
    }

    private void requireModulePrerequisites(UUID courseId, UUID moduleId, String studentId) {
        List<UUID> unmetPrerequisites = prerequisites.findByModuleId(moduleId).stream()
                .map(p -> p.getRequiredModuleId())
                .filter(requiredModuleId -> !isModuleCompleteByItems(courseId, requiredModuleId, studentId))
                .toList();
        if (!unmetPrerequisites.isEmpty()) {
            throw new BadRequestException("Module prerequisites not completed: " + unmetPrerequisites);
        }
    }

    private boolean isModuleCompleteByItems(UUID courseId, UUID moduleId, String studentId) {
        List<PublishedItem> moduleItems = publishedCurriculum(courseId).findModule(moduleId)
                .map(PublishedModule::items)
                .orElseGet(List::of);
        List<PublishedItem> requiredItems = moduleItems.stream().filter(PublishedItem::required).toList();
        if (requiredItems.isEmpty()) {
            return progressRepository.existsByModuleIdAndStudentIdAndStatus(moduleId, studentId, "COMPLETED");
        }
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository.findByModuleIdAndStudentId(moduleId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        return requiredItems.stream().allMatch(item -> isItemCompleted(item.id(), progressByItemId));
    }

    private LearnerModuleProgress saveModuleCompletion(UUID courseId, UUID moduleId, String studentId, Instant completedAt) {
        LearnerModuleProgress progress = progressRepository.findByModuleIdAndStudentId(moduleId, studentId)
                .orElseGet(() -> new LearnerModuleProgress(
                        UUID.randomUUID(),
                        courseId,
                        moduleId,
                        studentId,
                        "COMPLETED",
                        completedAt));
        progress.complete(completedAt);
        return progressRepository.save(progress);
    }

    private ModuleProgressSummaryDto toModuleSummary(PublishedModule module, List<PublishedItem> courseItems,
                                                    Map<UUID, LearnerItemProgress> progressByItemId) {
        List<PublishedItem> moduleItems = courseItems.stream()
                .filter(item -> module.id().equals(item.moduleId()))
                .toList();
        int totalItems = moduleItems.size();
        int completedItems = (int) moduleItems.stream()
                .filter(item -> isItemCompleted(item.id(), progressByItemId))
                .count();
        int totalRequiredItems = (int) moduleItems.stream().filter(PublishedItem::required).count();
        int completedRequiredItems = (int) moduleItems.stream()
                .filter(PublishedItem::required)
                .filter(item -> isItemCompleted(item.id(), progressByItemId))
                .count();
        int percent = totalRequiredItems == 0
                ? 0
                : (int) Math.round((completedRequiredItems * 100.0) / totalRequiredItems);
        boolean completed = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;
        return new ModuleProgressSummaryDto(
                module.id().toString(),
                totalItems,
                completedItems,
                totalRequiredItems,
                completedRequiredItems,
                percent,
                completed);
    }

    private List<ProgressBreakdownDto> breakdown(List<PublishedItem> courseItems,
                                                 Map<UUID, LearnerItemProgress> progressByItemId) {
        Map<String, List<PublishedItem>> byType = new HashMap<>();
        for (PublishedItem item : courseItems) {
            byType.computeIfAbsent(normalizeItemType(item), ignored -> new ArrayList<>()).add(item);
        }
        return byType.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> {
                    List<PublishedItem> typedItems = entry.getValue();
                    int total = typedItems.size();
                    int completed = (int) typedItems.stream()
                            .filter(item -> isItemCompleted(item.id(), progressByItemId))
                            .count();
                    int required = (int) typedItems.stream().filter(PublishedItem::required).count();
                    int completedRequired = (int) typedItems.stream()
                            .filter(PublishedItem::required)
                            .filter(item -> isItemCompleted(item.id(), progressByItemId))
                            .count();
                    return new ProgressBreakdownDto(entry.getKey(), total, completed, required, completedRequired);
                })
                .toList();
    }

    private ItemProgressDto toItemProgressDto(PublishedItem item, LearnerItemProgress progress) {
        return new ItemProgressDto(
                item.id().toString(),
                item.moduleId().toString(),
                normalizeItemType(item),
                item.title(),
                item.required(),
                progress == null ? "NOT_STARTED" : progress.getStatus(),
                progress == null ? null : progress.getProgressType(),
                progress == null ? null : progress.getCompletedAt());
    }

    private boolean isItemCompleted(UUID itemId, Map<UUID, LearnerItemProgress> progressByItemId) {
        LearnerItemProgress progress = progressByItemId.get(itemId);
        return progress != null && "COMPLETED".equals(progress.getStatus());
    }

    private String normalizeItemType(PublishedItem item) {
        if (item.videoMediaId() != null) {
            return "VIDEO";
        }
        String itemType = item.itemType() == null || item.itemType().isBlank()
                ? "LESSON"
                : item.itemType().toUpperCase();
        if ((item.documentMediaIds() != null && !item.documentMediaIds().isEmpty())
                && ("LESSON".equals(itemType) || "MATERIAL".equals(itemType))) {
            return "DOCUMENT";
        }
        if ("LINK".equals(itemType) || ("LESSON".equals(itemType) && !isBlank(item.contentUrl()))) {
            return "LINK";
        }
        return itemType;
    }

    private boolean isLearnerSelfCompletable(PublishedItem item) {
        return switch (normalizeItemType(item)) {
            case "LESSON", "DOCUMENT", "PDF", "MATERIAL", "LINK" -> true;
            default -> false;
        };
    }

    private String learnerProgressType(PublishedItem item) {
        return switch (normalizeItemType(item)) {
            case "DOCUMENT", "PDF", "MATERIAL" -> "DOCUMENT_CONFIRMED";
            case "LINK" -> "LINK_CONFIRMED";
            case "LESSON" -> "LESSON_CONFIRMED";
            default -> "SELF_CONFIRMED";
        };
    }

    private String verifiedProgressType(PublishedItem item) {
        return switch (normalizeItemType(item)) {
            case "VIDEO" -> "VIDEO_VERIFIED";
            case "QUIZ" -> "QUIZ_VERIFIED";
            case "ASSIGNMENT" -> "ASSIGNMENT_VERIFIED";
            case "DOCUMENT", "PDF", "MATERIAL" -> "DOCUMENT_VERIFIED";
            case "LINK" -> "LINK_VERIFIED";
            case "LESSON" -> "LESSON_VERIFIED";
            default -> "SOURCE_VERIFIED";
        };
    }

    private void validateVerifiedSource(PublishedItem item, RecordItemCompletionRequestDto request) {
        String kind = normalizeItemType(item);
        String sourceId = trimToNull(request.sourceId());
        switch (kind) {
            case "VIDEO" -> requireMatchingSource(kind, sourceId, item.videoMediaId(), item.refId());
            case "QUIZ", "ASSIGNMENT" -> requireMatchingSource(kind, sourceId, item.refId());
            default -> {
                // Read-only items can be verified by internal jobs without a backing source id.
            }
        }
    }

    private void requireMatchingSource(String kind, String sourceId, String... allowedSourceIds) {
        if (sourceId == null) {
            throw new BadRequestException(kind + " completion requires sourceId");
        }
        if (sourceMatches(sourceId, allowedSourceIds)) {
            return;
        }
        throw new BadRequestException(kind + " completion source does not match course item");
    }

    private boolean sourceMatches(PublishedItem item, String sourceId) {
        return sourceMatches(sourceId, item.videoMediaId(), item.refId());
    }

    private boolean sourceMatches(String sourceId, String... allowedSourceIds) {
        for (String allowed : allowedSourceIds) {
            if (!isBlank(allowed) && sourceId.equals(allowed.trim())) {
                return true;
            }
        }
        return false;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String trimToNull(String value) {
        return isBlank(value) ? null : value.trim();
    }

    private record PublishedCurriculum(List<PublishedModule> modules) {
        private PublishedCurriculum {
            modules = modules == null ? List.of() : List.copyOf(modules);
        }

        private static PublishedCurriculum fromSnapshot(List<ModuleOutlineDto> modules) {
            List<PublishedModule> publishedModules = modules == null ? List.of() : modules.stream()
                    .map(PublishedModule::fromSnapshot)
                    .toList();
            return new PublishedCurriculum(publishedModules);
        }

        private static PublishedCurriculum fromLive(List<CourseModule> modules, ModuleItemJpaRepository items) {
            List<PublishedModule> publishedModules = modules == null ? List.of() : modules.stream()
                    .map(module -> PublishedModule.fromLive(module, items.findByModuleIdOrderByPositionAsc(module.getId())))
                    .toList();
            return new PublishedCurriculum(publishedModules);
        }

        private List<PublishedItem> items() {
            return modules.stream()
                    .flatMap(module -> module.items().stream())
                    .toList();
        }

        private Optional<PublishedModule> findModule(UUID moduleId) {
            return modules.stream()
                    .filter(module -> module.id().equals(moduleId))
                    .findFirst();
        }

        private Optional<PublishedItem> findItem(UUID moduleId, UUID itemId) {
            return findModule(moduleId)
                    .flatMap(module -> module.items().stream()
                            .filter(item -> item.id().equals(itemId))
                            .findFirst());
        }

        private boolean containsDocumentMedia(UUID mediaId) {
            if (mediaId == null) {
                return false;
            }
            String target = mediaId.toString();
            return items().stream()
                    .flatMap(item -> item.documentMediaIds().stream())
                    .anyMatch(target::equalsIgnoreCase);
        }
    }

    private record PublishedModule(
            UUID id,
            String title,
            String description,
            int position,
            String status,
            List<PublishedItem> items) {
        private PublishedModule {
            items = items == null ? List.of() : List.copyOf(items);
        }

        private static PublishedModule fromSnapshot(ModuleOutlineDto module) {
            UUID moduleId = snapshotUuid(module.moduleId(), "moduleId");
            List<PublishedItem> publishedItems = module.items() == null ? List.of() : module.items().stream()
                    .map(item -> PublishedItem.fromSnapshot(moduleId, item))
                    .toList();
            return new PublishedModule(
                    moduleId,
                    module.title(),
                    module.description(),
                    module.position(),
                    module.status(),
                    publishedItems);
        }

        private static PublishedModule fromLive(CourseModule module, List<ModuleItem> items) {
            return new PublishedModule(
                    module.getId(),
                    module.getTitle(),
                    module.getDescription(),
                    module.getPosition(),
                    module.getStatus(),
                    items == null ? List.of() : items.stream().map(PublishedItem::fromLive).toList());
        }
    }

    private record PublishedItem(
            UUID id,
            UUID moduleId,
            String itemType,
            String refId,
            String title,
            String description,
            String videoMediaId,
            List<String> documentMediaIds,
            String contentUrl,
            Integer estimatedMinutes,
            int position,
            boolean required) {
        private PublishedItem {
            documentMediaIds = documentMediaIds == null ? List.of() : List.copyOf(documentMediaIds);
        }

        private static PublishedItem fromSnapshot(UUID moduleId, ItemOutlineDto item) {
            return new PublishedItem(
                    snapshotUuid(item.itemId(), "itemId"),
                    moduleId,
                    item.itemType(),
                    item.refId(),
                    item.title(),
                    item.description(),
                    item.videoMediaId(),
                    item.documentMediaIds(),
                    item.contentUrl(),
                    item.estimatedMinutes(),
                    item.position(),
                    item.required());
        }

        private static PublishedItem fromLive(ModuleItem item) {
            return new PublishedItem(
                    item.getId(),
                    item.getModuleId(),
                    item.getItemType(),
                    item.getItemId(),
                    item.getTitle(),
                    item.getDescription(),
                    item.getVideoMediaId() == null ? null : item.getVideoMediaId().toString(),
                    item.getDocumentMediaIds(),
                    item.getContentUrl(),
                    item.getEstimatedMinutes(),
                    item.getPosition(),
                    item.isRequired());
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
