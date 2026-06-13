package edu.courseflow.course.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ModuleProgressSummaryDto;
import edu.courseflow.course.dto.LearningDtos.CertificateEligibilityDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerItemStateDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerNextActionDto;
import edu.courseflow.course.dto.LearningDtos.CourseSummaryDto;
import edu.courseflow.course.dto.LearningDtos.ItemSummaryDto;
import edu.courseflow.course.dto.LearningDtos.LearnerCoursePlayerDto;
import edu.courseflow.course.dto.LearningDtos.LearnerNextActionDto;
import edu.courseflow.course.dto.LearningDtos.ModuleSummaryDto;
import edu.courseflow.course.dto.LearningDtos.TargetDto;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.service.EnrollmentMembershipClient.EnrollmentMembershipUnavailableException;
import edu.courseflow.course.service.EnrollmentMembershipClient.EnrollmentSummary;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Supplier;
import org.springframework.stereotype.Service;

@Service
public class LearnerNextActionService {

    private static final int MAX_ENROLLMENTS = 8;

    private final EnrollmentMembershipClient enrollments;
    private final CourseCatalogService courses;
    private final CourseModuleService modules;

    public LearnerNextActionService(EnrollmentMembershipClient enrollments,
            CourseCatalogService courses,
            CourseModuleService modules) {
        this.enrollments = enrollments;
        this.courses = courses;
        this.modules = modules;
    }

    public LearnerNextActionDto nextAction(CurrentUser user) {
        requireAuthenticated(user);
        List<EnrollmentSummary> learnerEnrollments;
        try {
            learnerEnrollments = enrollments.listLearnerEnrollments(user, MAX_ENROLLMENTS);
        } catch (EnrollmentMembershipUnavailableException | ForbiddenException | IllegalStateException ex) {
            return degradedEnrollmentAction(ex);
        }
        List<ActionCandidate> candidates = new ArrayList<>();
        Instant generatedAt = Instant.now();

        for (EnrollmentSummary enrollment : learnerEnrollments) {
            Optional<CourseActionContext> context = actionContext(enrollment, user);
            if (context.isEmpty()) {
                continue;
            }

            CourseActionContext candidate = context.get();
            if (!candidate.player().progress().completed()
                    && candidate.player().nextAction() != null) {
                if (candidate.player().nextAction().itemId() != null) {
                    candidates.add(itemActionCandidate(candidate, enrollment, generatedAt));
                    continue;
                }
                if ("SOURCE_SYNC_PENDING".equals(candidate.player().nextAction().kind())) {
                    candidates.add(courseLevelActionCandidate(candidate, enrollment, generatedAt));
                    continue;
                }
            }
            if (candidate.player().progress().completed() || "COMPLETED".equalsIgnoreCase(enrollment.status())) {
                candidates.add(courseCompleteActionCandidate(candidate, enrollment, generatedAt));
            }
        }

        if (!candidates.isEmpty()) {
            candidates.sort(this::compareCandidates);
            return candidates.getFirst().action();
        }
        return emptyAction();
    }

    private ActionCandidate itemActionCandidate(CourseActionContext context, EnrollmentSummary enrollment, Instant now) {
        CoursePlayerNextActionDto next = context.player().nextAction();
        CoursePlayerItemStateDto itemState = itemState(context, next.itemId()).orElse(null);
        Instant dueAt = itemState == null ? null : itemState.sourceDueAt();
        String kind = next.kind() == null ? "CONTINUE_ITEM" : next.kind();
        int score = priorityScore(kind, itemState, context.player().progress().percentComplete(), dueAt, now);
        return new ActionCandidate(
                score,
                dueAt,
                reasonCodeFor(kind, itemState),
                enrollmentSortTime(enrollment),
                () -> missingRequiredItemAction(context));
    }

    private ActionCandidate courseLevelActionCandidate(CourseActionContext context, EnrollmentSummary enrollment,
                                                       Instant now) {
        CoursePlayerNextActionDto next = context.player().nextAction();
        String kind = next.kind() == null ? "SOURCE_SYNC_PENDING" : next.kind();
        return new ActionCandidate(
                priorityScore(kind, null, context.player().progress().percentComplete(), null, now),
                null,
                reasonCodeFor(kind, null),
                enrollmentSortTime(enrollment),
                () -> courseLevelAction(context, next));
    }

    private ActionCandidate courseCompleteActionCandidate(CourseActionContext context, EnrollmentSummary enrollment,
                                                         Instant now) {
        String kind = completedActionKind(context);
        return new ActionCandidate(
                priorityScore(kind, null, context.player().progress().percentComplete(), null, now),
                null,
                reasonCodeFor(kind, null),
                enrollmentSortTime(enrollment),
                () -> courseCompleteAction(context));
    }

    private int compareCandidates(ActionCandidate left, ActionCandidate right) {
        int byScore = Integer.compare(right.priorityScore(), left.priorityScore());
        if (byScore != 0) {
            return byScore;
        }
        int byDueAt = compareDueAt(left.dueAt(), right.dueAt());
        if (byDueAt != 0) {
            return byDueAt;
        }
        return Comparator.nullsLast(Comparator.<Instant>naturalOrder())
                .compare(left.enrollmentSortTime(), right.enrollmentSortTime());
    }

    private int compareDueAt(Instant left, Instant right) {
        if (left == null && right == null) {
            return 0;
        }
        if (left == null) {
            return 1;
        }
        if (right == null) {
            return -1;
        }
        return left.compareTo(right);
    }

    private int priorityScore(String kind, CoursePlayerItemStateDto itemState, int progressPercent, Instant dueAt,
                              Instant now) {
        int score = switch (kind == null ? "" : kind) {
            case "OVERDUE_ITEM" -> 1000;
            case "CONTINUE_ITEM" -> "IN_PROGRESS".equals(sourceStatus(itemState)) ? 900 : 700;
            case "START_COURSE" -> 680;
            case "AWAITING_GRADE" -> 620;
            case "LOCKED_BY_PREREQUISITE" -> 520;
            case "NOT_AVAILABLE_YET", "SOURCE_LOCKED" -> 500;
            case "SOURCE_SYNC_PENDING" -> 470;
            case "SOURCE_STATUS_UNAVAILABLE", "SOURCE_UNAVAILABLE" -> 430;
            case "CERTIFICATE_ISSUED" -> 390;
            case "CERTIFICATE_ELIGIBLE" -> 370;
            case "COURSE_COMPLETE" -> 200;
            default -> 100;
        };
        score += Math.min(Math.max(progressPercent, 0), 100) / 10;
        if (dueAt == null || now == null) {
            return score;
        }
        Duration untilDue = Duration.between(now, dueAt);
        if (untilDue.isNegative()) {
            return score + 220;
        }
        if (untilDue.compareTo(Duration.ofHours(24)) <= 0) {
            return score + 180;
        }
        if (untilDue.compareTo(Duration.ofDays(3)) <= 0) {
            return score + 120;
        }
        if (untilDue.compareTo(Duration.ofDays(7)) <= 0) {
            return score + 60;
        }
        return score;
    }

    private String completedActionKind(CourseActionContext context) {
        CertificateEligibilityDto certificate = context.player().certificateEligibility();
        if (certificate == null) {
            return "COURSE_COMPLETE";
        }
        if (certificate.issued() && certificate.verificationCode() != null && !certificate.verificationCode().isBlank()) {
            return "CERTIFICATE_ISSUED";
        }
        if (certificate.eligible() || "ELIGIBLE".equalsIgnoreCase(certificate.status())) {
            return "CERTIFICATE_ELIGIBLE";
        }
        if ("FINAL_GRADE_NOT_FINALIZED".equalsIgnoreCase(certificate.status())) {
            return "AWAITING_GRADE";
        }
        return "COURSE_COMPLETE";
    }

    private String reasonCodeFor(String kind, CoursePlayerItemStateDto itemState) {
        if (itemState != null && itemState.lockedReasonCode() != null && !itemState.lockedReasonCode().isBlank()) {
            return itemState.lockedReasonCode();
        }
        return switch (kind == null ? "" : kind) {
            case "OVERDUE_ITEM" -> "OVERDUE_REQUIRED_ACTIVITY";
            case "CONTINUE_ITEM" -> "NEXT_REQUIRED_ACTIVITY";
            case "START_COURSE" -> "FIRST_REQUIRED_ACTIVITY";
            case "AWAITING_GRADE" -> "AWAITING_FINAL_OR_SOURCE_GRADE";
            case "LOCKED_BY_PREREQUISITE" -> "PREREQUISITE_LOCKED";
            case "NOT_AVAILABLE_YET" -> "SOURCE_NOT_AVAILABLE_YET";
            case "SOURCE_LOCKED" -> "SOURCE_LOCKED";
            case "SOURCE_SYNC_PENDING" -> "SOURCE_PROGRESS_SYNC_PENDING";
            case "SOURCE_STATUS_UNAVAILABLE", "SOURCE_UNAVAILABLE" -> "SOURCE_UNAVAILABLE";
            case "CERTIFICATE_ISSUED" -> "CERTIFICATE_READY";
            case "CERTIFICATE_ELIGIBLE" -> "CERTIFICATE_ELIGIBLE";
            case "COURSE_COMPLETE" -> "COURSE_REQUIRED_ITEMS_COMPLETE";
            default -> "NEXT_ACTION_SELECTED";
        };
    }

    private Optional<CoursePlayerItemStateDto> itemState(CourseActionContext context, String itemId) {
        if (itemId == null || context.player().itemStates() == null) {
            return Optional.empty();
        }
        return context.player().itemStates().stream()
                .filter(state -> itemId.equals(state.itemId()))
                .findFirst();
    }

    private String sourceStatus(CoursePlayerItemStateDto itemState) {
        return itemState == null || itemState.sourceStatus() == null || itemState.sourceStatus().isBlank()
                ? "READY"
                : itemState.sourceStatus().trim().toUpperCase();
    }

    private Instant enrollmentSortTime(EnrollmentSummary enrollment) {
        if (enrollment == null) {
            return null;
        }
        if (enrollment.completedAt() != null) {
            return enrollment.completedAt();
        }
        return enrollment.enrolledAt();
    }

    private LearnerNextActionDto courseLevelAction(CourseActionContext context, CoursePlayerNextActionDto next) {
        CourseSummaryDto course = courseSummary(context);
        return new LearnerNextActionDto(
                Instant.now(),
                next.kind(),
                course,
                null,
                null,
                new TargetDto("COURSE", course.id(), course.slug()),
                "/courses/" + course.slug() + "/modules",
                next.ctaLabel() == null ? "Xem khóa học" : next.ctaLabel(),
                next.reason() == null ? next.title() : next.reason());
    }

    private Optional<CourseActionContext> actionContext(EnrollmentSummary enrollment, CurrentUser user) {
        Optional<UUID> courseId = parseUuid(enrollment.courseId());
        if (courseId.isEmpty()) {
            return Optional.empty();
        }
        try {
            LearnerCoursePlayerDto player = modules.nextActionSnapshot(courseId.get(), user);
            return Optional.of(new CourseActionContext(courseId.get(), player));
        } catch (BadRequestException | NotFoundException | ForbiddenException | IllegalStateException ex) {
            return Optional.empty();
        }
    }

    private LearnerNextActionDto missingRequiredItemAction(CourseActionContext context) {
        CoursePlayerNextActionDto next = context.player().nextAction();
        ItemProgressDto progressItem = findProgressItem(context.player().progress(), next.itemId())
                .orElse(new ItemProgressDto(
                        next.itemId(),
                        next.moduleId(),
                        next.itemType(),
                        next.title(),
                        true,
                        "NOT_STARTED",
                        null,
                        null));

        CourseModuleDto module = null;
        ModuleItemDto moduleItem = null;
        try {
            module = context.player().modules().stream()
                    .filter(candidate -> candidate.id().equals(next.moduleId()))
                    .findFirst()
                    .orElse(null);
            if (module != null && module.items() != null) {
                moduleItem = module.items().stream()
                        .filter(item -> item.id().equals(next.itemId()))
                        .findFirst()
                        .orElse(null);
            }
        } catch (RuntimeException ignored) {
            // Progress already identified the next item; module metadata only enriches the response.
        }

        ModuleProgressSummaryDto moduleProgress = findModuleProgress(context.player().progress(), next.moduleId()).orElse(null);
        String itemType = normalize(next.itemType() == null ? progressItem.itemType() : next.itemType());
        String refId = itemRef(itemType, moduleItem);
        CourseDto course = course(context);
        String href = next.locked() ? hrefFor(course, null) : hrefFor(course, next.itemId());
        boolean startCourse = "START_COURSE".equals(next.kind());

        CourseSummaryDto courseSummary = courseSummary(context);
        ModuleSummaryDto moduleSummary = moduleSummary(module, moduleProgress, next.moduleId());
        ItemSummaryDto itemSummary = new ItemSummaryDto(
                next.itemId(),
                itemType,
                moduleItem == null ? progressItem.title() : moduleItem.title(),
                progressItem.required(),
                progressItem.status(),
                refId);
        TargetDto target = new TargetDto(itemType, itemSummary.id(), refId);

        String kind = next.kind() == null ? startCourse ? "START_COURSE" : "CONTINUE_ITEM" : next.kind();
        return new LearnerNextActionDto(
                Instant.now(),
                kind,
                courseSummary,
                moduleSummary,
                itemSummary,
                target,
                href,
                next.ctaLabel() == null ? ctaFor(kind, itemType) : next.ctaLabel(),
                next.reason() == null
                        ? startCourse ? "Bài bắt buộc đầu tiên trong khóa học." : "Bài bắt buộc tiếp theo chưa hoàn thành."
                        : next.reason());
    }

    private LearnerNextActionDto courseCompleteAction(CourseActionContext context) {
        CourseSummaryDto course = courseSummary(context);
        CertificateEligibilityDto certificate = context.player().certificateEligibility();
        if (certificate != null) {
            if (certificate.issued() && certificate.verificationCode() != null && !certificate.verificationCode().isBlank()) {
                return new LearnerNextActionDto(
                        Instant.now(),
                        "CERTIFICATE_ISSUED",
                        course,
                        null,
                        null,
                        new TargetDto("CERTIFICATE", certificate.certificateId(), certificate.verificationCode()),
                        "/certificates/verify/" + URLEncoder.encode(certificate.verificationCode(), StandardCharsets.UTF_8),
                        "Xác minh chứng chỉ",
                        "Chứng chỉ của bạn đã được cấp và có thể xác minh công khai.");
            }
            if (certificate.eligible() || "ELIGIBLE".equalsIgnoreCase(certificate.status())) {
                return new LearnerNextActionDto(
                        Instant.now(),
                        "CERTIFICATE_ELIGIBLE",
                        course,
                        null,
                        null,
                        new TargetDto("CERTIFICATE", certificate.certificateId(), certificate.verificationCode()),
                        "/certificates",
                        "Mở ví chứng chỉ",
                        "Bạn đã đủ điều kiện nhận chứng chỉ cho khóa học này.");
            }
            if ("FINAL_GRADE_NOT_FINALIZED".equalsIgnoreCase(certificate.status())) {
                return new LearnerNextActionDto(
                        Instant.now(),
                        "AWAITING_GRADE",
                        course,
                        null,
                        null,
                        new TargetDto("GRADEBOOK", course.id(), course.slug()),
                        "/gradebook",
                        "Xem bảng điểm",
                        "Khóa học đã hoàn thành; bạn đang chờ instructor chốt điểm cuối khóa.");
            }
        }
        return new LearnerNextActionDto(
                Instant.now(),
                "COURSE_COMPLETE",
                course,
                null,
                null,
                new TargetDto("COURSE", course.id(), course.slug()),
                "/courses/" + course.slug() + "/modules",
                "Xem lại khóa học",
                "Bạn đã hoàn thành các yêu cầu bắt buộc của khóa học.");
    }

    private LearnerNextActionDto emptyAction() {
        return new LearnerNextActionDto(
                Instant.now(),
                "EMPTY",
                null,
                null,
                null,
                null,
                "/search",
                "Tìm khóa học",
                "Bạn chưa có khóa học đang học.");
    }

    private LearnerNextActionDto degradedEnrollmentAction(RuntimeException ex) {
        return new LearnerNextActionDto(
                Instant.now(),
                "LEARNER_CONTEXT_UNAVAILABLE",
                null,
                null,
                null,
                null,
                "/",
                "Thử lại sau",
                "Chưa tải được danh sách khóa học của bạn. CourseFlow sẽ tự cập nhật lại khi dịch vụ ghi danh sẵn sàng.",
                "ENROLLMENT_MEMBERSHIP_UNAVAILABLE",
                0,
                null);
    }

    private CourseSummaryDto courseSummary(CourseActionContext context) {
        CourseDto course = course(context);
        return new CourseSummaryDto(
                course.id(),
                course.title(),
                course.slug(),
                context.player().progress().percentComplete());
    }

    private ModuleSummaryDto moduleSummary(CourseModuleDto module,
            ModuleProgressSummaryDto progress,
            String moduleId) {
        if (progress == null) {
            return new ModuleSummaryDto(
                    moduleId,
                    module == null ? null : module.title(),
                    0,
                    0,
                    0,
                    0,
                    0,
                    false);
        }
        return new ModuleSummaryDto(
                progress.moduleId(),
                module == null ? null : module.title(),
                progress.percentComplete(),
                progress.totalItems(),
                progress.completedItems(),
                progress.totalRequiredItems(),
                progress.completedRequiredItems(),
                progress.completed());
    }

    private Optional<ItemProgressDto> findProgressItem(CourseProgressDto progress, String itemId) {
        return progress.items().stream()
                .filter(item -> item.itemId().equals(itemId))
                .findFirst();
    }

    private Optional<ModuleProgressSummaryDto> findModuleProgress(CourseProgressDto progress, String moduleId) {
        return progress.modules().stream()
                .filter(module -> module.moduleId().equals(moduleId))
                .findFirst();
    }

    private String itemRef(String itemType, ModuleItemDto item) {
        if (item == null) {
            return null;
        }
        if ("VIDEO".equals(itemType) && item.videoMediaId() != null && !item.videoMediaId().isBlank()) {
            return item.videoMediaId();
        }
        if (item.itemId() != null && !item.itemId().isBlank()) {
            return item.itemId();
        }
        if (item.videoMediaId() != null && !item.videoMediaId().isBlank()) {
            return item.videoMediaId();
        }
        return null;
    }

    private String hrefFor(CourseDto course, String itemId) {
        String query = itemId == null || itemId.isBlank()
                ? ""
                : "?itemId=" + URLEncoder.encode(itemId, StandardCharsets.UTF_8);
        return "/courses/" + course.slug() + "/modules" + query;
    }

    private CourseDto course(CourseActionContext context) {
        if (context.course() != null) {
            return context.course();
        }
        CourseDto course = courses.get(context.courseId());
        context.setCourse(course);
        return course;
    }

    private String ctaFor(String kind, String itemType) {
        if ("START_COURSE".equals(kind)) {
            return "Bắt đầu học";
        }
        return switch (itemType) {
            case "QUIZ" -> "Mở quiz";
            case "ASSIGNMENT" -> "Mở assignment";
            case "VIDEO" -> "Xem video";
            default -> "Tiếp tục học";
        };
    }

    private Optional<UUID> parseUuid(String raw) {
        try {
            return raw == null || raw.isBlank() ? Optional.empty() : Optional.of(UUID.fromString(raw));
        } catch (IllegalArgumentException ex) {
            return Optional.empty();
        }
    }

    private String normalize(String value) {
        return value == null || value.isBlank() ? "LESSON" : value.trim().toUpperCase();
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }

    private static final class CourseActionContext {
        private final UUID courseId;
        private final LearnerCoursePlayerDto player;
        private CourseDto course;

        private CourseActionContext(UUID courseId, LearnerCoursePlayerDto player) {
            this.courseId = courseId;
            this.player = player;
        }

        UUID courseId() {
            return courseId;
        }

        LearnerCoursePlayerDto player() {
            return player;
        }

        CourseDto course() {
            return course;
        }

        void setCourse(CourseDto course) {
            this.course = course;
        }
    }

    private record ActionCandidate(
            int priorityScore,
            Instant dueAt,
            String reasonCode,
            Instant enrollmentSortTime,
            Supplier<LearnerNextActionDto> actionSupplier
    ) {
        LearnerNextActionDto action() {
            LearnerNextActionDto action = actionSupplier.get();
            return new LearnerNextActionDto(
                    action.generatedAt(),
                    action.kind(),
                    action.course(),
                    action.module(),
                    action.item(),
                    action.target(),
                    action.href(),
                    action.ctaLabel(),
                    action.reason(),
                    reasonCode,
                    priorityScore,
                    dueAt);
        }
    }
}
