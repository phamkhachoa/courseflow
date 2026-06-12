package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CompleteItemProgressRequestDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.MissingRequirementDto;
import edu.courseflow.course.dto.CourseProgressDto.ModuleProgressSummaryDto;
import edu.courseflow.course.dto.CourseProgressDto.ProgressBreakdownDto;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.LearnerItemProgress;
import edu.courseflow.course.model.LearnerModuleProgress;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.model.OutboxEvent;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
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
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourseModuleService {

    private final CourseModuleJpaRepository modules;
    private final ModuleItemJpaRepository items;
    private final ModulePrerequisiteJpaRepository prerequisites;
    private final LearnerModuleProgressJpaRepository progressRepository;
    private final LearnerItemProgressJpaRepository itemProgressRepository;
    private final OutboxEventJpaRepository outbox;
    private final ObjectMapper objectMapper;
    private final CourseMapper mapper;
    private final CourseAccessClient courseAccess;

    public CourseModuleService(CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            ModulePrerequisiteJpaRepository prerequisites,
            LearnerModuleProgressJpaRepository progressRepository,
            LearnerItemProgressJpaRepository itemProgressRepository,
            OutboxEventJpaRepository outbox,
            ObjectMapper objectMapper,
            CourseMapper mapper,
            CourseAccessClient courseAccess) {
        this.modules = modules;
        this.items = items;
        this.prerequisites = prerequisites;
        this.progressRepository = progressRepository;
        this.itemProgressRepository = itemProgressRepository;
        this.outbox = outbox;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.courseAccess = courseAccess;
    }

    public List<CourseModuleDto> listModules(UUID courseId) {
        return modules.findByCourseIdAndStatusOrderByPositionAsc(courseId, "PUBLISHED").stream()
                .map(this::toCourseModuleDto)
                .toList();
    }

    @Transactional
    public ModuleProgressDto completeModule(UUID courseId, UUID moduleId, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        // The learner records progress for themselves: studentId comes from the token, not the body.
        String studentId = String.valueOf(user.id());

        CourseModule module = modules.findById(moduleId)
                .orElseThrow(() -> new NotFoundException("Module not found: " + moduleId));
        if (!module.getCourseId().equals(courseId)) {
            throw new BadRequestException("Module " + moduleId + " does not belong to course " + courseId);
        }
        if (!"PUBLISHED".equals(module.getStatus())) {
            throw new ForbiddenException("Cannot complete an unpublished module");
        }

        requireModulePrerequisites(moduleId, studentId);

        List<ModuleItem> moduleItems = items.findByModuleIdOrderByPositionAsc(moduleId);
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        List<String> missingItems = moduleItems.stream()
                .filter(ModuleItem::isRequired)
                .filter(item -> !isItemCompleted(item.getId(), progressByItemId))
                .map(ModuleItem::getTitle)
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

        CourseModule module = modules.findById(moduleId)
                .orElseThrow(() -> new NotFoundException("Module not found: " + moduleId));
        validateModule(courseId, module);
        ModuleItem item = items.findByIdAndModuleId(itemId, moduleId)
                .orElseThrow(() -> new NotFoundException("Module item not found: " + itemId));
        requireModulePrerequisites(moduleId, studentId);

        boolean alreadyComplete = computeProgress(courseId, studentId).completed();
        Instant completedAt = Instant.now();
        LearnerItemProgress progress = itemProgressRepository.findByItemIdAndStudentId(itemId, studentId)
                .orElseGet(() -> new LearnerItemProgress(UUID.randomUUID(), courseId, moduleId, itemId, studentId));
        progress.complete(resolveProgressType(request, item), completedAt);
        progress = itemProgressRepository.save(progress);

        if (isModuleCompleteByItems(moduleId, studentId)) {
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
        List<CourseModule> courseModules = modules.findByCourseIdAndStatusOrderByPositionAsc(courseId, "PUBLISHED");
        List<ModuleItem> courseItems = items.findPublishedCourseItems(courseId);
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
                .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                .count();
        int totalRequiredItems = (int) courseItems.stream().filter(ModuleItem::isRequired).count();
        int completedRequiredItems = (int) courseItems.stream()
                .filter(ModuleItem::isRequired)
                .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                .count();
        int percent = totalRequiredItems == 0
                ? 0
                : (int) Math.round((completedRequiredItems * 100.0) / totalRequiredItems);
        boolean completed = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;

        List<ProgressBreakdownDto> breakdown = breakdown(courseItems, progressByItemId);
        List<ItemProgressDto> itemProgress = courseItems.stream()
                .map(item -> toItemProgressDto(item, progressByItemId.get(item.getId())))
                .toList();
        List<MissingRequirementDto> missingRequirements = courseItems.stream()
                .filter(ModuleItem::isRequired)
                .filter(item -> !isItemCompleted(item.getId(), progressByItemId))
                .map(item -> new MissingRequirementDto(
                        item.getId().toString(),
                        item.getModuleId().toString(),
                        item.getItemType(),
                        item.getTitle()))
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

    private CourseModuleDto toCourseModuleDto(CourseModule module) {
        return mapper.toDto(module, items.findByModuleIdOrderByPositionAsc(module.getId()).stream()
                .map(mapper::toDto)
                .toList());
    }

    private void validateModule(UUID courseId, CourseModule module) {
        if (!module.getCourseId().equals(courseId)) {
            throw new BadRequestException("Module " + module.getId() + " does not belong to course " + courseId);
        }
        if (!"PUBLISHED".equals(module.getStatus())) {
            throw new ForbiddenException("Cannot complete an unpublished module");
        }
    }

    private void requireModulePrerequisites(UUID moduleId, String studentId) {
        List<UUID> unmetPrerequisites = prerequisites.findByModuleId(moduleId).stream()
                .map(p -> p.getRequiredModuleId())
                .filter(requiredModuleId -> !isModuleCompleteByItems(requiredModuleId, studentId))
                .toList();
        if (!unmetPrerequisites.isEmpty()) {
            throw new BadRequestException("Module prerequisites not completed: " + unmetPrerequisites);
        }
    }

    private boolean isModuleCompleteByItems(UUID moduleId, String studentId) {
        List<ModuleItem> moduleItems = items.findByModuleIdOrderByPositionAsc(moduleId);
        List<ModuleItem> requiredItems = moduleItems.stream().filter(ModuleItem::isRequired).toList();
        if (requiredItems.isEmpty()) {
            return progressRepository.existsByModuleIdAndStudentIdAndStatus(moduleId, studentId, "COMPLETED");
        }
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository.findByModuleIdAndStudentId(moduleId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        return requiredItems.stream().allMatch(item -> isItemCompleted(item.getId(), progressByItemId));
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

    private ModuleProgressSummaryDto toModuleSummary(CourseModule module, List<ModuleItem> courseItems,
                                                    Map<UUID, LearnerItemProgress> progressByItemId) {
        List<ModuleItem> moduleItems = courseItems.stream()
                .filter(item -> module.getId().equals(item.getModuleId()))
                .toList();
        int totalItems = moduleItems.size();
        int completedItems = (int) moduleItems.stream()
                .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                .count();
        int totalRequiredItems = (int) moduleItems.stream().filter(ModuleItem::isRequired).count();
        int completedRequiredItems = (int) moduleItems.stream()
                .filter(ModuleItem::isRequired)
                .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                .count();
        int percent = totalRequiredItems == 0
                ? 0
                : (int) Math.round((completedRequiredItems * 100.0) / totalRequiredItems);
        boolean completed = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;
        return new ModuleProgressSummaryDto(
                module.getId().toString(),
                totalItems,
                completedItems,
                totalRequiredItems,
                completedRequiredItems,
                percent,
                completed);
    }

    private List<ProgressBreakdownDto> breakdown(List<ModuleItem> courseItems,
                                                 Map<UUID, LearnerItemProgress> progressByItemId) {
        Map<String, List<ModuleItem>> byType = new HashMap<>();
        for (ModuleItem item : courseItems) {
            byType.computeIfAbsent(normalizeItemType(item), ignored -> new ArrayList<>()).add(item);
        }
        return byType.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> {
                    List<ModuleItem> typedItems = entry.getValue();
                    int total = typedItems.size();
                    int completed = (int) typedItems.stream()
                            .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                            .count();
                    int required = (int) typedItems.stream().filter(ModuleItem::isRequired).count();
                    int completedRequired = (int) typedItems.stream()
                            .filter(ModuleItem::isRequired)
                            .filter(item -> isItemCompleted(item.getId(), progressByItemId))
                            .count();
                    return new ProgressBreakdownDto(entry.getKey(), total, completed, required, completedRequired);
                })
                .toList();
    }

    private ItemProgressDto toItemProgressDto(ModuleItem item, LearnerItemProgress progress) {
        return new ItemProgressDto(
                item.getId().toString(),
                item.getModuleId().toString(),
                normalizeItemType(item),
                item.getTitle(),
                item.isRequired(),
                progress == null ? "NOT_STARTED" : progress.getStatus(),
                progress == null ? null : progress.getProgressType(),
                progress == null ? null : progress.getCompletedAt());
    }

    private boolean isItemCompleted(UUID itemId, Map<UUID, LearnerItemProgress> progressByItemId) {
        LearnerItemProgress progress = progressByItemId.get(itemId);
        return progress != null && "COMPLETED".equals(progress.getStatus());
    }

    private String normalizeItemType(ModuleItem item) {
        if (item.getVideoMediaId() != null) {
            return "VIDEO";
        }
        String itemType = item.getItemType() == null || item.getItemType().isBlank()
                ? "LESSON"
                : item.getItemType().toUpperCase();
        if ((item.getDocumentMediaIds() != null && !item.getDocumentMediaIds().isEmpty())
                && ("LESSON".equals(itemType) || "MATERIAL".equals(itemType))) {
            return "DOCUMENT";
        }
        return itemType;
    }

    private String resolveProgressType(CompleteItemProgressRequestDto request, ModuleItem item) {
        if (request != null && request.progressType() != null && !request.progressType().isBlank()) {
            return request.progressType().trim().toUpperCase();
        }
        return switch (normalizeItemType(item)) {
            case "VIDEO" -> "VIDEO_CONFIRMED";
            case "DOCUMENT", "PDF", "MATERIAL" -> "DOCUMENT_CONFIRMED";
            case "QUIZ" -> "QUIZ_CONFIRMED";
            case "ASSIGNMENT" -> "ASSIGNMENT_CONFIRMED";
            default -> "MANUAL";
        };
    }

    private ModuleItemDto toModuleItemDto(ModuleItem item) {
        return mapper.toDto(item);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
