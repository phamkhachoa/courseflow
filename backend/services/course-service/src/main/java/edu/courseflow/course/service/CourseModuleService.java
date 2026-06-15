package edu.courseflow.course.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModulePrerequisiteOutlineDto;
import edu.courseflow.course.dto.CompleteItemProgressRequestDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseDtos.PresignedDownloadDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.MissingRequirementDto;
import edu.courseflow.course.dto.CourseProgressDto.ModuleProgressSummaryDto;
import edu.courseflow.course.dto.CourseProgressDto.ProgressBreakdownDto;
import edu.courseflow.course.dto.LearningDtos.CertificateEligibilityDto;
import edu.courseflow.course.dto.LearningDtos.CertificateMissingRequirementDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerItemStateDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerModuleStateDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerNextActionDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerPrerequisiteDto;
import edu.courseflow.course.dto.LearningDtos.LearnerCoursePlayerDto;
import edu.courseflow.course.dto.LearningDtos.LearnerLearningPathDto;
import edu.courseflow.course.dto.LearningDtos.LearningSourceStatusDto;
import edu.courseflow.course.dto.LearningDtos.LearningPathItemDto;
import edu.courseflow.course.dto.LearningDtos.LearningPathModuleDto;
import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckDto;
import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckRequestDto;
import edu.courseflow.course.service.LearningSourceStatusClient.SourceKey;
import edu.courseflow.course.service.LearningSourceStatusClient.SourceRef;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.dto.RecordItemCompletionRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.LearnerItemProgress;
import edu.courseflow.course.model.LearnerModuleProgress;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.model.OutboxEvent;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseJpaRepository;
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
import java.util.Set;
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
    private final CourseJpaRepository courses;
    private final CourseVersionJpaRepository versions;
    private final ModulePrerequisiteJpaRepository prerequisites;
    private final LearnerModuleProgressJpaRepository progressRepository;
    private final LearnerItemProgressJpaRepository itemProgressRepository;
    private final OutboxEventJpaRepository outbox;
    private final ObjectMapper objectMapper;
    private final CourseMapper mapper;
    private final CourseAccessClient courseAccess;
    private final CertificateEligibilityClient certificateEligibilityClient;
    private final LearningSourceStatusClient sourceStatusClient;
    private final RestClient mediaClient;
    private final InternalJwtService internalJwt;

    public CourseModuleService(CourseModuleJpaRepository modules,
            ModuleItemJpaRepository items,
            CourseJpaRepository courses,
            CourseVersionJpaRepository versions,
            ModulePrerequisiteJpaRepository prerequisites,
            LearnerModuleProgressJpaRepository progressRepository,
            LearnerItemProgressJpaRepository itemProgressRepository,
            OutboxEventJpaRepository outbox,
            ObjectMapper objectMapper,
            CourseMapper mapper,
            CourseAccessClient courseAccess,
            CertificateEligibilityClient certificateEligibilityClient,
            LearningSourceStatusClient sourceStatusClient,
            RestClient.Builder restClientBuilder,
            @Value("${courseflow.content.media-service-url:http://media-service:8080}") String mediaServiceUrl,
            InternalJwtService internalJwt) {
        this.modules = modules;
        this.items = items;
        this.courses = courses;
        this.versions = versions;
        this.prerequisites = prerequisites;
        this.progressRepository = progressRepository;
        this.itemProgressRepository = itemProgressRepository;
        this.outbox = outbox;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.courseAccess = courseAccess;
        this.certificateEligibilityClient = certificateEligibilityClient;
        this.sourceStatusClient = sourceStatusClient;
        this.mediaClient = restClientBuilder.baseUrl(mediaServiceUrl).build();
        this.internalJwt = internalJwt;
    }

    public List<CourseModuleDto> listModules(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseAccess(user, courseId);
        return publishedModules(courseId);
    }

    List<CourseModuleDto> publishedModules(UUID courseId) {
        return publishedCurriculum(courseId).modules().stream()
                .map(this::toCourseModuleDto)
                .toList();
    }

    public LearnerCoursePlayerDto player(UUID courseId, CurrentUser user) {
        return player(courseId, user, true);
    }

    public LearnerCoursePlayerDto nextActionSnapshot(UUID courseId, CurrentUser user) {
        return player(courseId, user, false);
    }

    public LearnerLearningPathDto learningPath(UUID courseId, CurrentUser user, String cohortId, String sectionId) {
        LearnerCoursePlayerDto player = player(courseId, user, false);
        Map<String, CoursePlayerModuleStateDto> moduleStateById = player.moduleStates().stream()
                .collect(Collectors.toMap(CoursePlayerModuleStateDto::moduleId, Function.identity(), (a, b) -> a));
        Map<String, ModuleProgressSummaryDto> moduleProgressById = player.progress().modules().stream()
                .collect(Collectors.toMap(ModuleProgressSummaryDto::moduleId, Function.identity(), (a, b) -> a));
        Map<String, CoursePlayerItemStateDto> itemStateById = player.itemStates().stream()
                .collect(Collectors.toMap(CoursePlayerItemStateDto::itemId, Function.identity(), (a, b) -> a));
        List<LearningPathModuleDto> pathModules = player.modules().stream()
                .map(module -> learningPathModule(
                        module,
                        moduleStateById.get(module.id()),
                        moduleProgressById.get(module.id()),
                        itemStateById))
                .toList();
        return new LearnerLearningPathDto(
                Instant.now(),
                player.courseId(),
                player.publishedVersionNo(),
                player.progress().studentId(),
                trimToNull(cohortId),
                trimToNull(sectionId),
                player.progress(),
                player.nextAction(),
                pathModules);
    }

    private LearnerCoursePlayerDto player(UUID courseId, CurrentUser user, boolean includeCertificateEligibility) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        String studentId = String.valueOf(user.id());
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        CourseProgressDto progress = toCourseProgressDto(courseId, studentId, curriculum, progressByItemId);
        List<CoursePlayerModuleStateDto> moduleStates = moduleStates(curriculum, studentId, progressByItemId);
        Map<UUID, CoursePlayerModuleStateDto> moduleStateById = moduleStates.stream()
                .collect(Collectors.toMap(state -> UUID.fromString(state.moduleId()), Function.identity(), (a, b) -> a));
        Map<SourceKey, LearningSourceStatusDto> sourceStatuses = loadSourceStatuses(courseId, studentId, curriculum);
        List<CoursePlayerItemStateDto> itemStates = itemStates(curriculum, progressByItemId, moduleStateById,
                sourceStatuses);
        CertificateEligibilityDto certificateEligibility = includeCertificateEligibility || progress.completed()
                ? certificateEligibility(courseId, studentId, user, progress, itemStates)
                : null;

        return new LearnerCoursePlayerDto(
                Instant.now(),
                courseId.toString(),
                curriculum.versionNo(),
                curriculum.modules().stream().map(this::toCourseModuleDto).toList(),
                progress,
                certificateEligibility,
                nextAction(curriculum, progress, itemStates),
                moduleStates,
                itemStates);
    }

    private LearningPathModuleDto learningPathModule(CourseModuleDto module,
                                                     CoursePlayerModuleStateDto state,
                                                     ModuleProgressSummaryDto progress,
                                                     Map<String, CoursePlayerItemStateDto> itemStateById) {
        List<LearningPathItemDto> pathItems = module.items().stream()
                .map(item -> learningPathItem(item, itemStateById.get(item.id())))
                .toList();
        return new LearningPathModuleDto(
                module.id(),
                module.title(),
                module.description(),
                module.position(),
                state != null && state.locked(),
                state == null ? null : state.lockedReasonCode(),
                state == null ? null : state.lockedReasonText(),
                progress == null ? 0 : progress.percentComplete(),
                progress == null ? pathItems.size() : progress.totalItems(),
                progress == null ? 0 : progress.completedItems(),
                progress == null ? (int) pathItems.stream().filter(LearningPathItemDto::required).count()
                        : progress.totalRequiredItems(),
                progress == null ? 0 : progress.completedRequiredItems(),
                progress != null && progress.completed(),
                state == null || state.unmetPrerequisites() == null ? List.of() : state.unmetPrerequisites(),
                pathItems);
    }

    private LearningPathItemDto learningPathItem(ModuleItemDto item, CoursePlayerItemStateDto state) {
        return new LearningPathItemDto(
                item.id(),
                item.itemType(),
                item.itemId(),
                item.title(),
                item.estimatedMinutes(),
                item.position(),
                item.required(),
                state == null ? "NOT_STARTED" : state.progressStatus(),
                state == null ? null : state.progressType(),
                state == null ? null : state.completedAt(),
                state == null ? null : state.completionMode(),
                state != null && state.locked(),
                state == null ? null : state.lockedReasonCode(),
                state == null ? "READY" : state.sourceStatus(),
                state == null ? null : state.sourceDueAt(),
                state == null ? null : state.sourceLockAt());
    }

    public PresignedDownloadDto downloadPublishedMedia(UUID courseId, UUID mediaId, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        courseAccess.requireCourseAccess(user, courseId);
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        PublishedItem item = curriculum.findItemByDocumentMedia(mediaId)
                .orElseThrow(() -> new ForbiddenException("Media asset is not part of the published course curriculum"));
        String studentId = String.valueOf(user.id());
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        List<CoursePlayerPrerequisiteDto> unmetPrerequisites = unmetPrerequisites(
                curriculum,
                item.moduleId(),
                studentId,
                progressByItemId);
        if (!unmetPrerequisites.isEmpty()) {
            throw new ForbiddenException("Media asset is locked until module prerequisites are completed");
        }
        return mediaClient.get()
                .uri("/internal/media/assets/{mediaId}/download-url/trusted", mediaId)
                .headers(internalJwt::applyServiceToken)
                .retrieve()
                .body(PresignedDownloadDto.class);
    }

    public LearningAccessCheckDto checkLearningAccess(UUID courseId, LearningAccessCheckRequestDto request) {
        if (request == null || isBlank(request.studentId())) {
            throw new BadRequestException("studentId is required");
        }
        if (isBlank(request.sourceType())) {
            throw new BadRequestException("sourceType is required");
        }
        if (isBlank(request.sourceId())) {
            throw new BadRequestException("sourceId is required");
        }
        String studentId = request.studentId().trim();
        String sourceType = request.sourceType().trim().toUpperCase();
        String sourceId = request.sourceId().trim();
        try {
            courseAccess.requirePublishedCourse(courseId);
            courseAccess.requireStudentCourseAccess(studentId, courseId);
        } catch (RuntimeException ex) {
            return deniedLearningAccess(
                    courseId,
                    studentId,
                    sourceType,
                    sourceId,
                    "COURSE_ACCESS_DENIED",
                    "Học viên chưa có quyền học khóa này.",
                    null);
        }
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        Optional<PublishedItem> item = findPublishedItemByVerifiedSource(curriculum, sourceType, sourceId);
        if (item.isEmpty()) {
            return deniedLearningAccess(
                    courseId,
                    studentId,
                    sourceType,
                    sourceId,
                    "SOURCE_NOT_IN_PUBLISHED_CURRICULUM",
                    "Hoạt động này không nằm trong phiên bản khóa học đã publish.",
                    null);
        }
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        List<CoursePlayerPrerequisiteDto> unmetPrerequisites = unmetPrerequisites(
                curriculum,
                item.get().moduleId(),
                studentId,
                progressByItemId);
        if (!unmetPrerequisites.isEmpty()) {
            return deniedLearningAccess(
                    courseId,
                    studentId,
                    sourceType,
                    sourceId,
                    "PREREQUISITE_MODULE_INCOMPLETE",
                    lockedReason(unmetPrerequisites),
                    item.get());
        }
        return new LearningAccessCheckDto(
                Instant.now(),
                courseId.toString(),
                studentId,
                sourceType,
                sourceId,
                true,
                null,
                null,
                item.get().moduleId().toString(),
                item.get().id().toString());
    }

    private LearningAccessCheckDto deniedLearningAccess(UUID courseId, String studentId, String sourceType,
                                                        String sourceId, String reasonCode, String reasonText,
                                                        PublishedItem item) {
        return new LearningAccessCheckDto(
                Instant.now(),
                courseId.toString(),
                studentId,
                sourceType,
                sourceId,
                false,
                reasonCode,
                reasonText,
                item == null ? null : item.moduleId().toString(),
                item == null ? null : item.id().toString());
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

        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        requireModulePrerequisites(curriculum, moduleId, studentId, progressByItemId);
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

        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        PublishedItem item = curriculum.findItem(moduleId, itemId)
                .orElseThrow(() -> new NotFoundException("Published module item not found: " + itemId));

        if (!isLearnerSelfCompletable(item)) {
            throw new BadRequestException("Item type " + normalizeItemType(item)
                    + " requires verified completion from its source service");
        }
        return recordItemCompletion(curriculum, courseId, moduleId, item, studentId, learnerProgressType(item), Instant.now());
    }

    @Transactional
    public ItemProgressDto recordVerifiedItemCompletion(UUID courseId, UUID moduleId, UUID itemId,
                                                        RecordItemCompletionRequestDto request) {
        if (request == null || isBlank(request.studentId())) {
            throw new BadRequestException("studentId is required");
        }
        String studentId = request.studentId().trim();
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        PublishedItem item = curriculum.findItem(moduleId, itemId)
                .orElseThrow(() -> new NotFoundException("Published module item not found: " + itemId));
        validateVerifiedSource(item, request);
        Instant completedAt = request.completedAt() == null ? Instant.now() : request.completedAt();
        return recordItemCompletion(curriculum, courseId, moduleId, item, studentId, verifiedProgressType(item), completedAt);
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
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        PublishedItem item = findPublishedItemByVerifiedSource(
                curriculum,
                request.sourceType().trim().toUpperCase(),
                request.sourceId().trim())
                .orElseThrow(() -> new NotFoundException("Published module item not found for source: "
                        + request.sourceType() + "/" + request.sourceId()));
        validateVerifiedSource(item, request);
        Instant completedAt = request.completedAt() == null ? Instant.now() : request.completedAt();
        return recordItemCompletion(curriculum, courseId, item.moduleId(), item, request.studentId().trim(),
                verifiedProgressType(item), completedAt);
    }

    private ItemProgressDto recordItemCompletion(PublishedCurriculum curriculum, UUID courseId, UUID moduleId, PublishedItem item,
                                                 String studentId, String progressType, Instant completedAt) {
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        requireModulePrerequisites(curriculum, moduleId, studentId, progressByItemId);
        boolean alreadyComplete = computeProgress(courseId, studentId).completed();
        LearnerItemProgress progress = itemProgressRepository.findByItemIdAndStudentId(item.id(), studentId)
                .orElseGet(() -> new LearnerItemProgress(UUID.randomUUID(), courseId, moduleId, item.id(), studentId));
        progress.complete(progressType, completedAt);
        progress = itemProgressRepository.save(progress);
        progressByItemId.put(item.id(), progress);

        if (isModuleCompleteByItems(curriculum, moduleId, studentId, progressByItemId)) {
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

    public CourseProgressDto progressForStudent(UUID courseId, String studentId) {
        if (isBlank(studentId)) {
            throw new BadRequestException("studentId is required");
        }
        courseAccess.requirePublishedCourse(courseId);
        return computeProgress(courseId, studentId.trim());
    }

    CourseProgressDto computeProgress(UUID courseId, String studentId) {
        PublishedCurriculum curriculum = publishedCurriculum(courseId);
        Map<UUID, LearnerItemProgress> progressByItemId = itemProgressRepository
                .findByCourseIdAndStudentId(courseId, studentId).stream()
                .collect(Collectors.toMap(LearnerItemProgress::getItemId, Function.identity(), (a, b) -> a));
        return toCourseProgressDto(courseId, studentId, curriculum, progressByItemId);
    }

    private CourseProgressDto toCourseProgressDto(UUID courseId, String studentId, PublishedCurriculum curriculum,
                                                  Map<UUID, LearnerItemProgress> progressByItemId) {
        List<PublishedModule> courseModules = curriculum.modules();
        List<PublishedItem> courseItems = curriculum.items();

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
                curriculum.versionNo(),
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

    private List<CoursePlayerModuleStateDto> moduleStates(PublishedCurriculum curriculum, String studentId,
                                                          Map<UUID, LearnerItemProgress> progressByItemId) {
        Map<UUID, List<UUID>> prerequisiteModuleIds = prerequisiteModuleIds(curriculum);
        return curriculum.modules().stream()
                .map(module -> {
                    List<CoursePlayerPrerequisiteDto> unmet = unmetPrerequisites(
                            curriculum,
                            prerequisiteModuleIds.getOrDefault(module.id(), List.of()),
                            studentId,
                            progressByItemId);
                    boolean locked = !unmet.isEmpty();
                    return new CoursePlayerModuleStateDto(
                            module.id().toString(),
                            locked,
                            locked ? "PREREQUISITE_MODULE_INCOMPLETE" : null,
                            locked ? lockedReason(unmet) : null,
                            unmet);
                })
                .toList();
    }

    private List<CoursePlayerPrerequisiteDto> unmetPrerequisites(PublishedCurriculum curriculum, UUID moduleId,
                                                                 String studentId,
                                                                 Map<UUID, LearnerItemProgress> progressByItemId) {
        return unmetPrerequisites(
                curriculum,
                prerequisiteModuleIds(curriculum).getOrDefault(moduleId, List.of()),
                studentId,
                progressByItemId);
    }

    private List<CoursePlayerPrerequisiteDto> unmetPrerequisites(PublishedCurriculum curriculum,
                                                                 List<UUID> prerequisiteModuleIds,
                                                                 String studentId,
                                                                 Map<UUID, LearnerItemProgress> progressByItemId) {
        return prerequisiteModuleIds.stream()
                .filter(requiredModuleId -> !isModuleCompleteByItems(curriculum, requiredModuleId, studentId, progressByItemId))
                .map(requiredModuleId -> new CoursePlayerPrerequisiteDto(
                        requiredModuleId.toString(),
                        curriculum.findModule(requiredModuleId).map(PublishedModule::title).orElse("Module " + requiredModuleId),
                        false))
                .toList();
    }

    private String lockedReason(List<CoursePlayerPrerequisiteDto> unmet) {
        if (unmet.isEmpty()) {
            return null;
        }
        if (unmet.size() == 1) {
            return "Hoàn thành " + unmet.getFirst().title() + " trước khi mở chương này.";
        }
        return "Hoàn thành " + unmet.size() + " chương điều kiện trước khi mở chương này.";
    }

    private Map<SourceKey, LearningSourceStatusDto> loadSourceStatuses(UUID courseId, String studentId,
                                                                       PublishedCurriculum curriculum) {
        if (sourceStatusClient == null) {
            return Map.of();
        }
        Map<SourceKey, LearningSourceStatusDto> sourceStatuses = sourceStatusClient.loadStatuses(
                courseId,
                studentId,
                sourceRefs(curriculum));
        return sourceStatuses == null ? Map.of() : sourceStatuses;
    }

    private List<SourceRef> sourceRefs(PublishedCurriculum curriculum) {
        return curriculum.items().stream()
                .map(item -> new SourceRef(normalizeItemType(item), trimToNull(item.refId())))
                .filter(ref -> ("QUIZ".equals(ref.sourceType()) || "ASSIGNMENT".equals(ref.sourceType()))
                        && !isBlank(ref.sourceId()))
                .distinct()
                .toList();
    }

    private List<CoursePlayerItemStateDto> itemStates(PublishedCurriculum curriculum,
                                                      Map<UUID, LearnerItemProgress> progressByItemId,
                                                      Map<UUID, CoursePlayerModuleStateDto> moduleStateById,
                                                      Map<SourceKey, LearningSourceStatusDto> sourceStatuses) {
        return curriculum.items().stream()
                .map(item -> {
                    LearnerItemProgress progress = progressByItemId.get(item.id());
                    CoursePlayerModuleStateDto moduleState = moduleStateById.get(item.moduleId());
                    boolean locked = moduleState != null && moduleState.locked();
                    String itemType = normalizeItemType(item);
                    LearningSourceStatusDto sourceStatus = sourceStatuses.get(new SourceKey(itemType, item.refId()));
                    return new CoursePlayerItemStateDto(
                            item.id().toString(),
                            item.moduleId().toString(),
                            itemType,
                            item.required(),
                            progress == null ? "NOT_STARTED" : progress.getStatus(),
                            progress == null ? null : progress.getProgressType(),
                            progress == null ? null : progress.getCompletedAt(),
                            isLearnerSelfCompletable(item) ? "SELF" : "VERIFIED",
                            locked,
                            locked ? moduleState.lockedReasonCode() : null,
                            locked ? moduleState.lockedReasonText() : null,
                            locked ? "LOCKED" : itemSourceStatus(sourceStatus),
                            sourceStatus == null ? null : sourceStatus.dueAt(),
                            sourceStatus == null ? null : sourceStatus.lockAt());
                })
                .toList();
    }

    private CertificateEligibilityDto certificateEligibility(UUID courseId, String studentId, CurrentUser user,
                                                            CourseProgressDto progress,
                                                            List<CoursePlayerItemStateDto> itemStates) {
        CertificateEligibilityDto remote = certificateEligibilityClient == null
                ? unavailableCertificateEligibility(courseId, studentId, "Certificate eligibility client is not configured.")
                : certificateEligibilityClient.loadEligibility(courseId, user);
        return mergeCertificateEligibility(courseId, studentId, remote, progress, itemStates);
    }

    private CertificateEligibilityDto mergeCertificateEligibility(UUID courseId, String studentId,
                                                                  CertificateEligibilityDto remote,
                                                                  CourseProgressDto progress,
                                                                  List<CoursePlayerItemStateDto> itemStates) {
        CertificateEligibilityDto base = remote == null
                ? unavailableCertificateEligibility(courseId, studentId, "Certificate service returned no eligibility status.")
                : remote;
        List<CertificateMissingRequirementDto> requiredItemMissing = missingRequiredItems(progress, itemStates);
        boolean requiredItemsEligible = requiredItemMissing.isEmpty();
        boolean issued = base.issued();
        boolean remoteUnavailable = "ELIGIBILITY_UNAVAILABLE".equalsIgnoreCase(base.status());
        boolean eligible = issued || (base.eligible() && requiredItemsEligible && !remoteUnavailable);
        boolean completionEligible = issued || (base.completionEligible() && requiredItemsEligible);
        List<CertificateMissingRequirementDto> missing = new ArrayList<>();
        for (CertificateMissingRequirementDto requirement : safeCertificateRequirements(base)) {
            if ("COURSE_COMPLETION".equalsIgnoreCase(requirement.code())
                    && (!requiredItemsEligible || "COURSE_NOT_COMPLETED".equalsIgnoreCase(base.status()))) {
                continue;
            }
            missing.add(requirement);
        }
        missing.addAll(requiredItemMissing);
        if (requiredItemsEligible
                && !issued
                && "COURSE_NOT_COMPLETED".equalsIgnoreCase(base.status())
                && missing.stream().noneMatch(requirement -> "COURSE_COMPLETION_SYNC".equalsIgnoreCase(requirement.code()))) {
            missing.add(new CertificateMissingRequirementDto(
                    "COURSE_COMPLETION_SYNC",
                    "Chờ đồng bộ hoàn thành khóa",
                    "Các mục bắt buộc đã hoàn tất, nhưng trạng thái hoàn thành khóa chưa đồng bộ sang certificate service."));
        }

        return new CertificateEligibilityDto(
                base.generatedAt() == null ? Instant.now() : base.generatedAt(),
                courseId.toString(),
                studentId,
                eligible,
                certificateStatus(base, requiredItemsEligible, remoteUnavailable),
                completionEligible,
                issued || base.gradeEligible(),
                issued || requiredItemsEligible,
                issued,
                base.finalGrade(),
                base.gradeThreshold(),
                base.finalGradeStatus(),
                base.certificateId(),
                base.verificationCode(),
                base.issuedAt(),
                missing);
    }

    private List<CertificateMissingRequirementDto> missingRequiredItems(CourseProgressDto progress,
                                                                        List<CoursePlayerItemStateDto> itemStates) {
        if (progress == null || progress.missingRequirements() == null || progress.missingRequirements().isEmpty()) {
            return List.of();
        }
        Map<String, CoursePlayerItemStateDto> stateByItemId = itemStates == null
                ? Map.of()
                : itemStates.stream()
                        .collect(Collectors.toMap(CoursePlayerItemStateDto::itemId, Function.identity(), (a, b) -> a));
        return progress.missingRequirements().stream()
                .filter(requirement -> !sourceCompleted(stateByItemId.get(requirement.itemId())))
                .map(requirement -> new CertificateMissingRequirementDto(
                        "REQUIRED_ITEM_INCOMPLETE",
                        requirement.title(),
                        "Hoàn thành mục bắt buộc trong published course snapshot."))
                .toList();
    }

    private String certificateStatus(CertificateEligibilityDto base, boolean requiredItemsEligible,
                                     boolean remoteUnavailable) {
        if (base.issued()) {
            return "ISSUED";
        }
        if (remoteUnavailable) {
            return "ELIGIBILITY_UNAVAILABLE";
        }
        if (!requiredItemsEligible) {
            return "REQUIRED_ITEMS_INCOMPLETE";
        }
        if ("COURSE_NOT_COMPLETED".equalsIgnoreCase(base.status())) {
            return "PROGRESS_SYNC_PENDING";
        }
        return isBlank(base.status()) ? "NOT_ELIGIBLE" : base.status();
    }

    private List<CertificateMissingRequirementDto> safeCertificateRequirements(CertificateEligibilityDto eligibility) {
        return eligibility == null || eligibility.missingRequirements() == null
                ? List.of()
                : eligibility.missingRequirements();
    }

    private CertificateEligibilityDto unavailableCertificateEligibility(UUID courseId, String studentId, String detail) {
        return new CertificateEligibilityDto(
                Instant.now(),
                courseId.toString(),
                studentId,
                false,
                "ELIGIBILITY_UNAVAILABLE",
                false,
                false,
                false,
                false,
                null,
                null,
                null,
                null,
                null,
                null,
                List.of(new CertificateMissingRequirementDto(
                        "CERTIFICATE_ELIGIBILITY_UNAVAILABLE",
                        "Chưa kiểm tra được điều kiện chứng chỉ",
                        detail)));
    }

    private String itemSourceStatus(LearningSourceStatusDto sourceStatus) {
        if (sourceStatus == null || isBlank(sourceStatus.sourceStatus())) {
            return "READY";
        }
        return sourceStatus.sourceStatus().trim().toUpperCase();
    }

    private CoursePlayerNextActionDto nextAction(PublishedCurriculum curriculum, CourseProgressDto progress,
                                                 List<CoursePlayerItemStateDto> itemStates) {
        Map<String, CoursePlayerItemStateDto> stateByItemId = itemStates.stream()
                .collect(Collectors.toMap(CoursePlayerItemStateDto::itemId, Function.identity(), (a, b) -> a));
        if (progress.completed()) {
            return new CoursePlayerNextActionDto(
                    "COURSE_COMPLETE",
                    null,
                    null,
                    "COURSE",
                    "Khóa học đã hoàn tất",
                    false,
                    "Ôn lại khóa học",
                    "Bạn đã hoàn thành các mục bắt buộc của khóa học.");
        }

        List<PublishedItem> missingItems = progress.missingRequirements().stream()
                .map(missing -> curriculum.findItem(UUID.fromString(missing.moduleId()), UUID.fromString(missing.itemId())))
                .flatMap(Optional::stream)
                .toList();
        List<PublishedItem> pendingItems = missingItems.stream()
                .filter(item -> !sourceCompleted(stateByItemId.get(item.id().toString())))
                .toList();
        if (!missingItems.isEmpty() && pendingItems.isEmpty()) {
            return new CoursePlayerNextActionDto(
                    "SOURCE_SYNC_PENDING",
                    null,
                    null,
                    "COURSE",
                    "Đang đồng bộ tiến độ",
                    false,
                    "Làm mới sau",
                    "Các hoạt động bắt buộc đã hoàn tất ở hệ thống nguồn; CourseFlow đang chờ đồng bộ tiến độ.");
        }

        Optional<PublishedItem> next = firstUnlockedWithSourceStatus(
                        pendingItems,
                        stateByItemId,
                        Set.of("OVERDUE"))
                .or(() -> firstUnlockedWithSourceStatus(
                        pendingItems,
                        stateByItemId,
                        Set.of("IN_PROGRESS")))
                .or(() -> firstUnlockedWithSourceStatus(
                        pendingItems,
                        stateByItemId,
                        Set.of("READY")))
                .or(() -> firstUnlockedItem(pendingItems, stateByItemId));
        boolean onlyLockedItemsRemain = next.isEmpty() && !pendingItems.isEmpty();
        if (next.isEmpty()) {
            next = pendingItems.stream().findFirst();
        }
        if (next.isEmpty()) {
            return new CoursePlayerNextActionDto(
                    "EMPTY",
                    null,
                    null,
                    null,
                    "Chưa có bài bắt buộc tiếp theo",
                    false,
                    "Xem lộ trình",
                    "Khóa học chưa có mục bắt buộc cần hoàn thành.");
        }

        PublishedItem item = next.get();
        CoursePlayerItemStateDto state = stateByItemId.get(item.id().toString());
        boolean locked = state != null && (state.locked() || sourceBlocksAction(state));
        return new CoursePlayerNextActionDto(
                nextActionKind(progress, state, onlyLockedItemsRemain),
                item.moduleId().toString(),
                item.id().toString(),
                normalizeItemType(item),
                item.title(),
                locked,
                ctaForItem(item, state),
                reasonForItem(state));
    }

    private Optional<PublishedItem> firstUnlockedWithSourceStatus(List<PublishedItem> items,
                                                                  Map<String, CoursePlayerItemStateDto> stateByItemId,
                                                                  Set<String> sourceStatuses) {
        return items.stream()
                .filter(item -> {
                    CoursePlayerItemStateDto state = stateByItemId.get(item.id().toString());
                    return !isPrerequisiteLocked(state) && sourceStatuses.contains(sourceStatus(state));
                })
                .findFirst();
    }

    private Optional<PublishedItem> firstUnlockedItem(List<PublishedItem> items,
                                                      Map<String, CoursePlayerItemStateDto> stateByItemId) {
        return items.stream()
                .filter(item -> !isPrerequisiteLocked(stateByItemId.get(item.id().toString())))
                .findFirst();
    }

    private boolean isPrerequisiteLocked(CoursePlayerItemStateDto state) {
        return state != null && state.locked();
    }

    private boolean sourceCompleted(CoursePlayerItemStateDto state) {
        return sourceStatusIn(state, "COMPLETED", "GRADED");
    }

    private boolean sourceBlocksAction(CoursePlayerItemStateDto state) {
        return sourceStatusIn(state, "NOT_AVAILABLE", "LOCKED", "UNAVAILABLE", "SOURCE_STATUS_UNAVAILABLE");
    }

    private boolean sourceStatusIn(CoursePlayerItemStateDto state, String... statuses) {
        String sourceStatus = sourceStatus(state);
        for (String status : statuses) {
            if (status.equals(sourceStatus)) {
                return true;
            }
        }
        return false;
    }

    private String sourceStatus(CoursePlayerItemStateDto state) {
        if (state == null || isBlank(state.sourceStatus())) {
            return "READY";
        }
        return state.sourceStatus().trim().toUpperCase();
    }

    private String nextActionKind(CourseProgressDto progress, CoursePlayerItemStateDto state,
                                  boolean onlyLockedItemsRemain) {
        if (onlyLockedItemsRemain || isPrerequisiteLocked(state)) {
            return "LOCKED_BY_PREREQUISITE";
        }
        return switch (sourceStatus(state)) {
            case "OVERDUE" -> "OVERDUE_ITEM";
            case "IN_PROGRESS" -> "CONTINUE_ITEM";
            case "SUBMITTED", "RESUBMITTED", "PENDING_GRADE", "ATTEMPTS_EXHAUSTED" -> "AWAITING_GRADE";
            case "NOT_AVAILABLE" -> "NOT_AVAILABLE_YET";
            case "LOCKED" -> "SOURCE_LOCKED";
            case "SOURCE_STATUS_UNAVAILABLE" -> "SOURCE_STATUS_UNAVAILABLE";
            case "UNAVAILABLE" -> "SOURCE_UNAVAILABLE";
            default -> progress.percentComplete() == 0 && progress.completedItems() == 0
                    ? "START_COURSE"
                    : "CONTINUE_ITEM";
        };
    }

    private String ctaForItem(PublishedItem item) {
        return switch (normalizeItemType(item)) {
            case "QUIZ" -> "Mở quiz";
            case "ASSIGNMENT" -> "Mở assignment";
            case "VIDEO" -> "Xem video";
            default -> "Tiếp tục học";
        };
    }

    private String ctaForItem(PublishedItem item, CoursePlayerItemStateDto state) {
        if (isPrerequisiteLocked(state)) {
            return "Xem điều kiện";
        }
        return switch (sourceStatus(state)) {
            case "OVERDUE" -> "Xem bài quá hạn";
            case "IN_PROGRESS" -> "Tiếp tục làm";
            case "SUBMITTED", "RESUBMITTED", "PENDING_GRADE", "ATTEMPTS_EXHAUSTED" -> "Xem trạng thái";
            case "NOT_AVAILABLE" -> "Xem lịch mở";
            case "LOCKED" -> "Xem hạn nộp";
            case "SOURCE_STATUS_UNAVAILABLE" -> "Thử lại sau";
            case "UNAVAILABLE" -> "Xem cấu hình";
            default -> ctaForItem(item);
        };
    }

    private String reasonForItem(CoursePlayerItemStateDto state) {
        if (isPrerequisiteLocked(state)) {
            return state.lockedReasonText();
        }
        return switch (sourceStatus(state)) {
            case "OVERDUE" -> "Hoạt động này đã quá hạn và vẫn chưa hoàn tất.";
            case "IN_PROGRESS" -> "Bạn đang làm dở hoạt động này, hãy tiếp tục trước khi chuyển sang việc khác.";
            case "SUBMITTED", "RESUBMITTED", "PENDING_GRADE" ->
                    "Bài đã nộp và đang chờ chấm điểm hoặc đồng bộ kết quả.";
            case "ATTEMPTS_EXHAUSTED" -> "Bạn đã dùng hết lượt làm; hãy chờ điểm hoặc phản hồi từ giảng viên.";
            case "NOT_AVAILABLE" -> "Hoạt động này chưa đến thời gian mở.";
            case "LOCKED" -> "Hoạt động này đã khóa sau hạn nộp.";
            case "SOURCE_STATUS_UNAVAILABLE" ->
                    "Chưa lấy được trạng thái từ hệ thống nguồn, nên CourseFlow tạm thời không gợi ý hoạt động này.";
            case "UNAVAILABLE" -> "Hoạt động nguồn chưa sẵn sàng cho learner.";
            default -> "Bài bắt buộc tiếp theo chưa hoàn thành.";
        };
    }

    private void outbox(UUID aggregateId, String eventType, String payload) {
        outbox.save(new OutboxEvent(aggregateId, "course", eventType, payload));
    }

    private Optional<PublishedItem> findPublishedItemByVerifiedSource(PublishedCurriculum curriculum,
                                                                      String sourceType,
                                                                      String sourceId) {
        return curriculum.items().stream()
                .filter(item -> sourceType.equals(normalizeItemType(item)))
                .filter(item -> sourceMatches(item, sourceId))
                .findFirst();
    }

    private PublishedCurriculum publishedCurriculum(UUID courseId) {
        CourseVersion publishedVersion = resolvePublishedVersion(courseId);
        String snapshot = publishedVersion.getSnapshot();
        if (snapshot == null || snapshot.isBlank()) {
            throw new BadRequestException("Published course has an empty curriculum snapshot");
        }
        PublishedCurriculum curriculum = PublishedCurriculum.fromSnapshot(
                publishedVersion.getVersionNo(),
                readSnapshot(snapshot));
        validatePublishedCurriculum(curriculum);
        return curriculum;
    }

    private CourseVersion resolvePublishedVersion(UUID courseId) {
        Course course = courses.findById(courseId)
                .orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
        Integer publishedVersionNo = course.getPublishedVersionNo();
        if (publishedVersionNo != null) {
            CourseVersion version = versions.findByCourseIdAndVersionNo(courseId, publishedVersionNo)
                    .orElseThrow(() -> new BadRequestException(
                            "Published course pointer references missing version: " + publishedVersionNo));
            if (!"PUBLISHED".equals(version.getState())) {
                throw new BadRequestException(
                        "Published course pointer references non-published version: " + publishedVersionNo);
            }
            return version;
        }
        List<CourseVersion> publishedVersions = versions.findByCourseIdAndStateOrderByVersionNoDesc(courseId, "PUBLISHED");
        if (publishedVersions.isEmpty()) {
            throw new BadRequestException("Published course has no frozen curriculum snapshot");
        }
        return publishedVersions.getFirst();
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

    private void requireModulePrerequisites(PublishedCurriculum curriculum, UUID moduleId, String studentId,
                                            Map<UUID, LearnerItemProgress> progressByItemId) {
        List<UUID> unmetPrerequisites = prerequisiteModuleIds(curriculum).getOrDefault(moduleId, List.of()).stream()
                .filter(requiredModuleId -> !isModuleCompleteByItems(curriculum, requiredModuleId, studentId, progressByItemId))
                .toList();
        if (!unmetPrerequisites.isEmpty()) {
            throw new BadRequestException("Module prerequisites not completed: " + unmetPrerequisites);
        }
    }

    private boolean isModuleCompleteByItems(PublishedCurriculum curriculum, UUID moduleId, String studentId,
                                            Map<UUID, LearnerItemProgress> progressByItemId) {
        List<PublishedItem> moduleItems = curriculum.findModule(moduleId)
                .map(PublishedModule::items)
                .orElseGet(List::of);
        List<PublishedItem> requiredItems = moduleItems.stream().filter(PublishedItem::required).toList();
        if (requiredItems.isEmpty()) {
            return progressRepository.existsByModuleIdAndStudentIdAndStatus(moduleId, studentId, "COMPLETED");
        }
        return requiredItems.stream().allMatch(item -> isItemCompleted(item.id(), progressByItemId));
    }

    private Map<UUID, List<UUID>> prerequisiteModuleIds(PublishedCurriculum curriculum) {
        List<PublishedModule> modulesWithoutSnapshotPrerequisites = curriculum.modules().stream()
                .filter(module -> module.prerequisites() == null)
                .toList();
        Map<UUID, List<UUID>> result = new HashMap<>();
        curriculum.modules().stream()
                .filter(module -> module.prerequisites() != null)
                .forEach(module -> result.put(
                        module.id(),
                        module.prerequisites().stream()
                                .map(PublishedPrerequisite::requiredModuleId)
                                .toList()));
        if (modulesWithoutSnapshotPrerequisites.isEmpty()) {
            return result;
        }
        List<UUID> legacyModuleIds = modulesWithoutSnapshotPrerequisites.stream()
                .map(PublishedModule::id)
                .toList();
        prerequisites.findByModuleIdIn(legacyModuleIds).stream()
                .collect(Collectors.groupingBy(
                        prerequisite -> prerequisite.getModuleId(),
                        Collectors.mapping(prerequisite -> prerequisite.getRequiredModuleId(), Collectors.toList())))
                .forEach(result::put);
        modulesWithoutSnapshotPrerequisites.forEach(module -> result.putIfAbsent(module.id(), List.of()));
        return result;
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

    private record PublishedCurriculum(int versionNo, List<PublishedModule> modules) {
        private PublishedCurriculum {
            modules = modules == null ? List.of() : List.copyOf(modules);
        }

        private static PublishedCurriculum fromSnapshot(int versionNo, List<ModuleOutlineDto> modules) {
            List<PublishedModule> publishedModules = modules == null ? List.of() : modules.stream()
                    .map(PublishedModule::fromSnapshot)
                    .toList();
            return new PublishedCurriculum(versionNo, publishedModules);
        }

        private static PublishedCurriculum fromLive(List<CourseModule> modules, ModuleItemJpaRepository items) {
            List<PublishedModule> publishedModules = modules == null ? List.of() : modules.stream()
                    .map(module -> PublishedModule.fromLive(module, items.findByModuleIdOrderByPositionAsc(module.getId())))
                    .toList();
            return new PublishedCurriculum(0, publishedModules);
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

        private Optional<PublishedItem> findItemByDocumentMedia(UUID mediaId) {
            if (mediaId == null) {
                return Optional.empty();
            }
            String target = mediaId.toString();
            return items().stream()
                    .filter(item -> item.documentMediaIds().stream().anyMatch(target::equalsIgnoreCase))
                    .findFirst();
        }
    }

    private record PublishedModule(
            UUID id,
            String title,
            String description,
            int position,
            String status,
            List<PublishedPrerequisite> prerequisites,
            List<PublishedItem> items) {
        private PublishedModule {
            prerequisites = prerequisites == null ? null : List.copyOf(prerequisites);
            items = items == null ? List.of() : List.copyOf(items);
        }

        private static PublishedModule fromSnapshot(ModuleOutlineDto module) {
            UUID moduleId = snapshotUuid(module.moduleId(), "moduleId");
            List<PublishedItem> publishedItems = module.items() == null ? List.of() : module.items().stream()
                    .map(item -> PublishedItem.fromSnapshot(moduleId, item))
                    .toList();
            List<PublishedPrerequisite> publishedPrerequisites = module.prerequisites() == null ? null : module.prerequisites().stream()
                    .map(PublishedPrerequisite::fromSnapshot)
                    .toList();
            return new PublishedModule(
                    moduleId,
                    module.title(),
                    module.description(),
                    module.position(),
                    module.status(),
                    publishedPrerequisites,
                    publishedItems);
        }

        private static PublishedModule fromLive(CourseModule module, List<ModuleItem> items) {
            return new PublishedModule(
                    module.getId(),
                    module.getTitle(),
                    module.getDescription(),
                    module.getPosition(),
                    module.getStatus(),
                    List.of(),
                    items == null ? List.of() : items.stream().map(PublishedItem::fromLive).toList());
        }
    }

    private record PublishedPrerequisite(
            UUID requiredModuleId,
            String ruleType) {

        private static PublishedPrerequisite fromSnapshot(ModulePrerequisiteOutlineDto prerequisite) {
            return new PublishedPrerequisite(
                    snapshotUuid(prerequisite.requiredModuleId(), "requiredModuleId"),
                    isBlank(prerequisite.ruleType()) ? "MODULE_COMPLETED" : prerequisite.ruleType());
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
