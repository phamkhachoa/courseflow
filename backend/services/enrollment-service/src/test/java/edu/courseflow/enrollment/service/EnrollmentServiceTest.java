package edu.courseflow.enrollment.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.enrollment.dto.EnrollmentDtos.ChangeStatusRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.exception.ForbiddenException;
import edu.courseflow.enrollment.model.EnrollmentPromotionApplication;
import edu.courseflow.enrollment.repository.EnrollmentPromotionApplicationJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRepository;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReverseResult;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class EnrollmentServiceTest {

    @Mock
    private EnrollmentRepository repo;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private EnrollmentPromotionApplicationJpaRepository promotionApplications;
    @Mock
    private PromotionEnrollmentClient promotions;

    private EnrollmentService service;

    private static final UUID COURSE = UUID.fromString("00000000-0000-0000-0000-0000000000c1");

    @BeforeEach
    void setUp() {
        service = new EnrollmentService(repo, new ObjectMapper(), courseAccess);
    }

    private static CurrentUser student(long id) {
        return new CurrentUser(id, "s" + id + "@x.io", "STUDENT", Set.of("STUDENT"));
    }

    private static CurrentUser instructor(long id) {
        return new CurrentUser(id, "i" + id + "@x.io", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static EnrollmentDto enrollment(UUID id, String studentId, String status) {
        return new EnrollmentDto(id.toString(), studentId, COURSE.toString(), null, status,
                Instant.parse("2026-01-01T00:00:00Z"), null, null, null);
    }

    private static EnrollmentPromotionApplication appliedPromotion(UUID enrollmentId, UUID redemptionId) {
        return new EnrollmentPromotionApplication(
                enrollmentId,
                "7",
                COURSE,
                "APPLIED",
                "SAVE10",
                null,
                UUID.randomUUID(),
                redemptionId,
                "flow-1",
                "[]",
                "[]",
                "Coupon applied");
    }

    // ---------------------------------------------------------------------------------------------
    // Status transition rules
    // ---------------------------------------------------------------------------------------------

    @Nested
    class StatusTransitions {

        @Test
        void activeToDropped_isAllowed() {
            UUID id = UUID.randomUUID();
            EnrollmentDto active = enrollment(id, "7", "ACTIVE");
            when(repo.findById(id)).thenReturn(Optional.of(active));
            when(repo.changeStatus(eq(id), eq("7"), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            // no waitlist to promote
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("DROPPED", "changed mind"), student(7));

            assertThat(result.status()).isEqualTo("DROPPED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.dropped"), anyString());
        }

        @Test
        void activeToCompleted_isAllowed_forStaff() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("COMPLETED"), any()))
                    .thenReturn(enrollment(id, "7", "COMPLETED"));

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), instructor(99));

            assertThat(result.status()).isEqualTo("COMPLETED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.completed"), anyString());
        }

        @Test
        void droppedToActive_reEnroll_isAllowed_andRechecksCapacity() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "DROPPED")));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty()); // unlimited
            when(repo.changeStatus(eq(id), anyString(), eq("ACTIVE"), any()))
                    .thenReturn(enrollment(id, "7", "ACTIVE"));

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("ACTIVE", null), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            verify(repo).lockCapacity(COURSE);
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.created"), anyString());
        }

        @Test
        void completedIsTerminal_rejectsAnyTransition() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "COMPLETED")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("ACTIVE", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Illegal transition COMPLETED -> ACTIVE");
        }

        @Test
        void droppedToCompleted_isRejected() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "DROPPED")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Illegal transition DROPPED -> COMPLETED");
        }

        @Test
        void unknownStatus_isRejected() {
            UUID id = UUID.randomUUID();

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("ARCHIVED", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Invalid status");
        }

        @Test
        void student_cannotComplete_ownEnrollment() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), student(7)))
                    .isInstanceOf(ForbiddenException.class);
        }

        @Test
        void student_cannotDrop_someoneElsesEnrollment() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "8", "ACTIVE")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("DROPPED", null), student(7)))
                    .isInstanceOf(ForbiddenException.class);
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Capacity "last seat" behavior
    // ---------------------------------------------------------------------------------------------

    @Nested
    class Capacity {

        @Test
        void lastSeat_enrollSucceeds() {
            // capacity 10, 9 active -> one seat left
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(10));
            when(repo.countActive(COURSE)).thenReturn(9);
            when(repo.enroll("7", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "7", "ACTIVE"));

            EnrollmentDto result = service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            verify(repo).enroll("7", COURSE);
        }

        @Test
        void courseFull_enrollRejectedWith409() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(10));
            when(repo.countActive(COURSE)).thenReturn(10); // full

            assertThatThrownBy(() -> service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7)))
                    .isInstanceOf(ConflictException.class)
                    .hasMessageContaining("full");

            verify(repo, never()).enroll(anyString(), any());
        }

        @Test
        void noCapacityRow_meansUnlimited() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());
            when(repo.enroll("7", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "7", "ACTIVE"));

            EnrollmentDto result = service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            // countActive never consulted when capacity is unlimited
            verify(repo, never()).countActive(any());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Waitlist promotion ordering
    // ---------------------------------------------------------------------------------------------

    @Nested
    class WaitlistPromotion {

        @Test
        void drop_promotesHeadOfWaitlist_andCompacts() {
            UUID id = UUID.randomUUID();
            EnrollmentDto active = enrollment(id, "7", "ACTIVE");
            when(repo.findById(id)).thenReturn(Optional.of(active));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));

            // After the drop: capacity 1, 0 active -> a seat is free, so the head must be promoted.
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countActive(COURSE)).thenReturn(0);

            WaitlistEntryDto head = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "42", COURSE.toString(), 1, "WAITING",
                    Instant.parse("2026-01-01T00:00:00Z"));
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.of(head));
            when(repo.enroll("42", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "42", "ACTIVE"));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            InOrder inOrder = Mockito.inOrder(repo);
            inOrder.verify(repo).enroll("42", COURSE);
            inOrder.verify(repo).markWaitlistPromoted(UUID.fromString(head.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
        }

        @Test
        void drop_skipsCompletedWaitlistHead_andPromotesNextEligibleStudent() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countActive(COURSE)).thenReturn(0);

            WaitlistEntryDto completedHead = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "42", COURSE.toString(), 1, "WAITING",
                    Instant.parse("2026-01-01T00:00:00Z"));
            WaitlistEntryDto next = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "43", COURSE.toString(), 2, "WAITING",
                    Instant.parse("2026-01-01T00:01:00Z"));
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.of(completedHead), Optional.of(next));
            when(repo.find("42", COURSE)).thenReturn(Optional.of(enrollment(UUID.randomUUID(), "42", "COMPLETED")));
            when(repo.find("43", COURSE)).thenReturn(Optional.empty());
            when(repo.enroll("43", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "43", "ACTIVE"));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            InOrder inOrder = Mockito.inOrder(repo);
            inOrder.verify(repo).markWaitlistSkipped(UUID.fromString(completedHead.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
            inOrder.verify(repo).enroll("43", COURSE);
            inOrder.verify(repo).markWaitlistPromoted(UUID.fromString(next.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
        }

        @Test
        void drop_whenStillFull_doesNotPromote() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));

            // capacity 1 but still 1 active after the drop (e.g. another seat taken) -> no free seat
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countActive(COURSE)).thenReturn(1);

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            verify(repo, never()).firstWaiting(any());
            verify(repo, never()).enroll(anyString(), any());
        }

        @Test
        void drop_withEmptyWaitlist_promotesNobody() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countActive(COURSE)).thenReturn(0);
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.empty());

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            verify(repo, never()).markWaitlistPromoted(any());
            verify(repo, never()).compactWaitlist(any());
        }
    }

    @Nested
    class PromotionCompensation {

        @Test
        void drop_reversesAppliedCouponRedemption() {
            service = new EnrollmentService(repo, promotionApplications, new ObjectMapper(), courseAccess, promotions);
            UUID id = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            EnrollmentPromotionApplication application = appliedPromotion(id, redemptionId);
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());
            when(promotionApplications.findByEnrollmentId(id)).thenReturn(Optional.of(application));
            when(promotions.reverse(eq(redemptionId), anyString(), anyString()))
                    .thenReturn(new ReverseResult(true, redemptionId, "REVERSED", List.of("REVERSED"), List.of()));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", "refund"), student(7));

            verify(promotions).reverse(eq(redemptionId), anyString(), anyString());
            verify(promotionApplications).save(application);
            assertThat(application.getStatus()).isEqualTo("REVERSED");
        }
    }

    // ---------------------------------------------------------------------------------------------
    // System completion (course.completed consumer path)
    // ---------------------------------------------------------------------------------------------

    @Nested
    class SystemCompletion {

        @Test
        void completesActiveEnrollment_andEmitsEvent() {
            UUID id = UUID.randomUUID();
            when(repo.find("7", COURSE)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), eq("system"), eq("COMPLETED"), any()))
                    .thenReturn(enrollment(id, "7", "COMPLETED"));

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isPresent();
            assertThat(result.get().status()).isEqualTo("COMPLETED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.completed"), anyString());
        }

        @Test
        void noOp_whenAlreadyCompleted() {
            UUID id = UUID.randomUUID();
            when(repo.find("7", COURSE)).thenReturn(Optional.of(enrollment(id, "7", "COMPLETED")));

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isEmpty();
            verify(repo, never()).changeStatus(any(), anyString(), anyString(), any());
            verify(repo, never()).outbox(any(), anyString(), anyString(), anyString());
        }

        @Test
        void noOp_whenEnrollmentMissing() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isEmpty();
            verify(repo, never()).changeStatus(any(), anyString(), anyString(), any());
        }
    }
}
