package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.ItemProgressDto;
import edu.courseflow.course.dto.CourseProgressDto.MissingRequirementDto;
import edu.courseflow.course.dto.CourseProgressDto.ModuleProgressSummaryDto;
import edu.courseflow.course.dto.CourseProgressDto.ProgressBreakdownDto;
import edu.courseflow.course.dto.LearningDtos.CertificateEligibilityDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerItemStateDto;
import edu.courseflow.course.dto.LearningDtos.CoursePlayerNextActionDto;
import edu.courseflow.course.dto.LearningDtos.LearnerCoursePlayerDto;
import edu.courseflow.course.dto.LearningDtos.LearnerNextActionDto;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.service.EnrollmentMembershipClient.EnrollmentSummary;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LearnerNextActionServiceTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000099");
    private static final String COURSE_SLUG = "production-lms";
    private static final String OTHER_COURSE_SLUG = "deadline-operations";
    private static final String MODULE_ID = "30000000-0000-0000-0000-000000001001";
    private static final String ITEM_ID = "30000000-0000-0000-0000-000000002001";
    private static final CurrentUser LEARNER = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));

    @Mock
    private EnrollmentMembershipClient enrollments;
    @Mock
    private CourseCatalogService courses;
    @Mock
    private CourseModuleService modules;

    private LearnerNextActionService service;

    @BeforeEach
    void setUp() {
        service = new LearnerNextActionService(enrollments, courses, modules);
    }

    @Test
    void selectsFirstMissingRequiredItemAsContinueAction() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("ACTIVE")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(player("CONTINUE_ITEM", 50, false, 1, "LESSON", false));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("CONTINUE_ITEM");
        assertThat(action.course().id()).isEqualTo(COURSE_ID.toString());
        assertThat(action.course().progressPercent()).isEqualTo(50);
        assertThat(action.module().title()).isEqualTo("Module 1");
        assertThat(action.item().id()).isEqualTo(ITEM_ID);
        assertThat(action.item().type()).isEqualTo("LESSON");
        assertThat(action.item().refId()).isEqualTo("lesson-ref");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules?itemId=" + ITEM_ID);
        assertThat(action.ctaLabel()).isEqualTo("Tiếp tục học");
        verify(modules, never()).player(COURSE_ID, LEARNER);
    }

    @Test
    void usesStartCourseKindWhenNoProgressExistsYet() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("ACTIVE")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(player("START_COURSE", 0, false, 0, "QUIZ", false));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("START_COURSE");
        assertThat(action.target().type()).isEqualTo("QUIZ");
        assertThat(action.target().refId()).isEqualTo("quiz-1");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules?itemId=" + ITEM_ID);
        assertThat(action.ctaLabel()).isEqualTo("Bắt đầu học");
    }

    @Test
    void usesVideoMediaIdForVideoTargetWhenGenericRefDiffers() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("ACTIVE")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(player(
                "CONTINUE_ITEM",
                progress(25, false, 1, "VIDEO"),
                module("VIDEO", "curriculum-ref", "83000000-0000-0000-0000-000000000001"),
                false));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("CONTINUE_ITEM");
        assertThat(action.target().type()).isEqualTo("VIDEO");
        assertThat(action.target().refId()).isEqualTo("83000000-0000-0000-0000-000000000001");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules?itemId=" + ITEM_ID);
        assertThat(action.ctaLabel()).isEqualTo("Xem video");
    }

    @Test
    void doesNotDeepLinkDashboardActionIntoLockedItem() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("ACTIVE")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(player("LOCKED_BY_PREREQUISITE", 25, false, 1, "LESSON", true));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("LOCKED_BY_PREREQUISITE");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules");
        assertThat(action.ctaLabel()).isEqualTo("Xem điều kiện");
        assertThat(action.reason()).contains("điều kiện");
    }

    @Test
    void fallsBackToCourseCompleteWhenAllTopEnrollmentsAreComplete() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("COMPLETED")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(completedPlayer());

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("COURSE_COMPLETE");
        assertThat(action.item()).isNull();
        assertThat(action.target().type()).isEqualTo("COURSE");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules");
    }

    @Test
    void prioritizesIssuedCertificateForCompletedCourse() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("COMPLETED")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(completedPlayer(certificateIssued()));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("CERTIFICATE_ISSUED");
        assertThat(action.target().type()).isEqualTo("CERTIFICATE");
        assertThat(action.target().refId()).isEqualTo("CF-VERIFY");
        assertThat(action.href()).isEqualTo("/certificates/verify/CF-VERIFY");
        assertThat(action.ctaLabel()).isEqualTo("Xác minh chứng chỉ");
    }

    @Test
    void prioritizesEligibleCertificateForCompletedCourse() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("COMPLETED")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(completedPlayer(certificateEligible()));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("CERTIFICATE_ELIGIBLE");
        assertThat(action.href()).isEqualTo("/certificates");
        assertThat(action.ctaLabel()).isEqualTo("Mở ví chứng chỉ");
    }

    @Test
    void surfacesAwaitingGradeForCompletedCourseWithoutFinalGrade() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("COMPLETED")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(completedPlayer(certificatePendingGrade()));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("AWAITING_GRADE");
        assertThat(action.href()).isEqualTo("/gradebook");
        assertThat(action.ctaLabel()).isEqualTo("Xem bảng điểm");
    }

    @Test
    void ranksOverdueRequiredActivityAcrossEnrollmentsBeforeFirstEnrollmentContinue() {
        Instant overdueAt = Instant.parse("2026-06-12T08:00:00Z");
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment(COURSE_ID, "ACTIVE"), enrollment(OTHER_COURSE_ID, "ACTIVE")));
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER))
                .thenReturn(player("CONTINUE_ITEM", 30, false, 1, "LESSON", false));
        when(modules.nextActionSnapshot(OTHER_COURSE_ID, LEARNER))
                .thenReturn(playerWithSourceState("OVERDUE_ITEM", 45, "ASSIGNMENT", "OVERDUE", overdueAt));
        when(courses.get(OTHER_COURSE_ID)).thenReturn(course(OTHER_COURSE_ID, OTHER_COURSE_SLUG));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("OVERDUE_ITEM");
        assertThat(action.course().id()).isEqualTo(OTHER_COURSE_ID.toString());
        assertThat(action.href()).isEqualTo("/courses/deadline-operations/modules?itemId=" + ITEM_ID);
        assertThat(action.dueAt()).isEqualTo(overdueAt);
        assertThat(action.priorityScore()).isGreaterThan(1000);
        assertThat(action.reasonCode()).isEqualTo("OVERDUE_REQUIRED_ACTIVITY");
        verify(courses, never()).get(COURSE_ID);
    }

    @Test
    void returnsDegradedActionWhenEnrollmentMembershipLookupIsUnavailable() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenThrow(new EnrollmentMembershipClient.EnrollmentMembershipUnavailableException(
                        "membership lookup failed",
                        new RuntimeException("boom")));

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("LEARNER_CONTEXT_UNAVAILABLE");
        assertThat(action.reasonCode()).isEqualTo("ENROLLMENT_MEMBERSHIP_UNAVAILABLE");
        assertThat(action.href()).isEqualTo("/");
        verify(modules, never()).nextActionSnapshot(COURSE_ID, LEARNER);
    }

    @Test
    void surfacesCourseLevelSourceSyncPendingActionOnDashboard() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8))
                .thenReturn(List.of(enrollment("ACTIVE")));
        when(courses.get(COURSE_ID)).thenReturn(course());
        when(modules.nextActionSnapshot(COURSE_ID, LEARNER)).thenReturn(sourceSyncPendingPlayer());

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("SOURCE_SYNC_PENDING");
        assertThat(action.item()).isNull();
        assertThat(action.target().type()).isEqualTo("COURSE");
        assertThat(action.href()).isEqualTo("/courses/production-lms/modules");
        assertThat(action.reason()).contains("đồng bộ");
    }

    @Test
    void returnsEmptyWhenLearnerHasNoActiveEnrollment() {
        when(enrollments.listLearnerEnrollments(LEARNER, 8)).thenReturn(List.of());

        LearnerNextActionDto action = service.nextAction(LEARNER);

        assertThat(action.kind()).isEqualTo("EMPTY");
        assertThat(action.course()).isNull();
        assertThat(action.href()).isEqualTo("/search");
        verify(enrollments).listLearnerEnrollments(LEARNER, 8);
    }

    private static EnrollmentSummary enrollment(String status) {
        return enrollment(COURSE_ID, status);
    }

    private static EnrollmentSummary enrollment(UUID courseId, String status) {
        return new EnrollmentSummary(
                UUID.randomUUID().toString(),
                "4",
                courseId.toString(),
                null,
                status,
                Instant.parse("2026-06-13T00:00:00Z"),
                null,
                "COMPLETED".equals(status) ? Instant.parse("2026-06-13T01:00:00Z") : null,
                null);
    }

    private static CourseDto course() {
        return course(COURSE_ID, COURSE_SLUG);
    }

    private static CourseDto course(UUID courseId, String slug) {
        return new CourseDto(
                courseId.toString(),
                "CF-101",
                "Production LMS",
                slug,
                "Build a production learning platform.",
                "20000000-0000-0000-0000-000000000001",
                "9",
                "BEGINNER",
                "PUBLISHED",
                BigDecimal.ZERO,
                "USD",
                "FREE",
                Instant.parse("2026-06-01T00:00:00Z"),
                List.of());
    }

    private static CourseProgressDto progress(int percent, boolean completed, int completedItems, String itemType) {
        return new CourseProgressDto(
                COURSE_ID.toString(),
                "4",
                1,
                0,
                2,
                completedItems,
                2,
                completedItems,
                percent,
                completed,
                List.of(new ProgressBreakdownDto(itemType, 2, completedItems, 2, completedItems)),
                List.of(new ModuleProgressSummaryDto(MODULE_ID, 2, completedItems, 2, completedItems, percent, completed)),
                List.of(new ItemProgressDto(ITEM_ID, MODULE_ID, itemType, "Next required item", true, "NOT_STARTED", null, null)),
                List.of(new MissingRequirementDto(ITEM_ID, MODULE_ID, itemType, "Next required item")));
    }

    private static CourseProgressDto completedProgress() {
        return new CourseProgressDto(
                COURSE_ID.toString(),
                "4",
                1,
                1,
                2,
                2,
                2,
                2,
                100,
                true,
                List.of(new ProgressBreakdownDto("LESSON", 2, 2, 2, 2)),
                List.of(new ModuleProgressSummaryDto(MODULE_ID, 2, 2, 2, 2, 100, true)),
                List.of(),
                List.of());
    }

    private static LearnerCoursePlayerDto completedPlayer() {
        return completedPlayer(null);
    }

    private static LearnerCoursePlayerDto completedPlayer(CertificateEligibilityDto certificateEligibility) {
        return new LearnerCoursePlayerDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                List.of(module("LESSON", "lesson-ref")),
                completedProgress(),
                certificateEligibility,
                new CoursePlayerNextActionDto(
                        "COURSE_COMPLETE",
                        null,
                        null,
                        "COURSE",
                        "Khóa học đã hoàn tất",
                        false,
                        "Ôn lại khóa học",
                        "Bạn đã hoàn thành các mục bắt buộc của khóa học."),
                List.of(),
                List.of());
    }

    private static CertificateEligibilityDto certificateIssued() {
        return new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                true,
                "ISSUED",
                true,
                true,
                true,
                true,
                new BigDecimal("91.50"),
                new BigDecimal("60.00"),
                "FINALIZED",
                "70000000-0000-0000-0000-000000000001",
                "CF-VERIFY",
                Instant.parse("2026-06-13T01:00:00Z"),
                List.of());
    }

    private static CertificateEligibilityDto certificateEligible() {
        return new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                true,
                "ELIGIBLE",
                true,
                true,
                true,
                false,
                new BigDecimal("91.50"),
                new BigDecimal("60.00"),
                "FINALIZED",
                null,
                null,
                null,
                List.of());
    }

    private static CertificateEligibilityDto certificatePendingGrade() {
        return new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                false,
                "FINAL_GRADE_NOT_FINALIZED",
                true,
                false,
                true,
                false,
                null,
                new BigDecimal("60.00"),
                null,
                null,
                null,
                null,
                List.of());
    }

    private static LearnerCoursePlayerDto sourceSyncPendingPlayer() {
        return new LearnerCoursePlayerDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                List.of(module("QUIZ", "quiz-1")),
                progress(80, false, 1, "QUIZ"),
                null,
                new CoursePlayerNextActionDto(
                        "SOURCE_SYNC_PENDING",
                        null,
                        null,
                        "COURSE",
                        "Đang đồng bộ tiến độ",
                        false,
                        "Làm mới sau",
                        "Các hoạt động bắt buộc đã hoàn tất ở hệ thống nguồn; CourseFlow đang chờ đồng bộ tiến độ."),
                List.of(),
                List.of());
    }

    private static LearnerCoursePlayerDto player(String kind, int percent, boolean completed, int completedItems,
                                                 String itemType, boolean locked) {
        String refId = "QUIZ".equals(itemType) ? "quiz-1" : itemType.toLowerCase() + "-ref";
        return player(kind, progress(percent, completed, completedItems, itemType), module(itemType, refId), locked);
    }

    private static LearnerCoursePlayerDto player(String kind, CourseProgressDto progress, CourseModuleDto module, boolean locked) {
        ModuleItemDto item = module.items().getFirst();
        return new LearnerCoursePlayerDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                List.of(module),
                progress,
                null,
                new CoursePlayerNextActionDto(
                        kind,
                        MODULE_ID,
                        ITEM_ID,
                        item.itemType(),
                        item.title(),
                        locked,
                        locked ? "Xem điều kiện" : "START_COURSE".equals(kind) ? "Bắt đầu học" : null,
                        locked ? "Hoàn thành chương điều kiện trước khi mở bài này." : "Bài bắt buộc tiếp theo chưa hoàn thành."),
                List.of(),
                List.of());
    }

    private static LearnerCoursePlayerDto playerWithSourceState(String kind, int percent, String itemType,
                                                                String sourceStatus, Instant dueAt) {
        CourseModuleDto module = module(itemType, itemType.toLowerCase() + "-ref");
        ModuleItemDto item = module.items().getFirst();
        return new LearnerCoursePlayerDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                OTHER_COURSE_ID.toString(),
                List.of(module),
                progress(percent, false, 1, itemType),
                null,
                new CoursePlayerNextActionDto(
                        kind,
                        MODULE_ID,
                        ITEM_ID,
                        item.itemType(),
                        item.title(),
                        false,
                        "Xem bài quá hạn",
                        "Hoạt động này đã quá hạn và vẫn chưa hoàn tất."),
                List.of(),
                List.of(new CoursePlayerItemStateDto(
                        ITEM_ID,
                        MODULE_ID,
                        item.itemType(),
                        true,
                        "NOT_STARTED",
                        null,
                        null,
                        "SOURCE_VERIFIED",
                        false,
                        null,
                        null,
                        sourceStatus,
                        dueAt,
                        null)));
    }

    private static CourseModuleDto module(String itemType, String refId) {
        return module(itemType, refId, "VIDEO".equals(itemType) ? refId : null);
    }

    private static CourseModuleDto module(String itemType, String refId, String videoMediaId) {
        return new CourseModuleDto(
                MODULE_ID,
                "Module 1",
                "Foundation",
                1,
                "PUBLISHED",
                List.of(new ModuleItemDto(
                        ITEM_ID,
                        itemType,
                        refId,
                        "Next required item",
                        "Do the next thing.",
                        videoMediaId,
                        List.of(),
                        null,
                        15,
                        1,
                        true)));
    }
}
