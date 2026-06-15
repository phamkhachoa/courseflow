package edu.courseflow.enrollment.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollResultDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.ChangeStatusRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.CourseAccessDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentBenefitReconciliationQueryResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentCheckoutResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentPromotionApplicationStateDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentRemediationCaseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentStatsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.LearnerCouponWalletDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PaymentStatusUpdateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionApplicationActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RemediationCaseActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RemediationCaseAssignRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyEvaluateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyEvaluationResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.SetCapacityRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistRequestDto;
import edu.courseflow.enrollment.service.EnrollmentService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EnrollmentController {

    private final EnrollmentService enrollments;

    public EnrollmentController(EnrollmentService enrollments) {
        this.enrollments = enrollments;
    }

    @GetMapping("/internal/enrollments")
    public List<EnrollmentDto> list(@RequestParam Optional<UUID> courseId,
                                    @RequestParam Optional<String> studentId,
                                    CurrentUser user) {
        return enrollments.list(courseId, studentId, user);
    }

    @PostMapping("/internal/enrollments")
    public EnrollmentDto enroll(@Valid @RequestBody EnrollRequestDto request, CurrentUser user) {
        return enrollments.enroll(request, user);
    }

    @PostMapping("/internal/enrollments/promotion-preview")
    public PromotionPreviewDto promotionPreview(@Valid @RequestBody PromotionPreviewRequestDto request,
                                                CurrentUser user) {
        return enrollments.previewPromotion(request, user);
    }

    @GetMapping("/internal/enrollments/coupons")
    public LearnerCouponWalletDto learnerCoupons(CurrentUser user) {
        return enrollments.learnerCoupons(user);
    }

    @PostMapping("/internal/enrollments/checkout")
    public EnrollmentCheckoutResponseDto checkout(@Valid @RequestBody EnrollRequestDto request, CurrentUser user) {
        return enrollments.checkout(request, user);
    }

    @PostMapping("/internal/enrollments/orders/{id}:record-payment")
    public EnrollmentCheckoutResponseDto recordOrderPayment(
            @PathVariable UUID id,
            @Valid @RequestBody PaymentStatusUpdateRequestDto request,
            CurrentUser user) {
        return enrollments.recordOrderPayment(id, request, user);
    }

    @GetMapping("/internal/enrollments/access")
    public CourseAccessDto access(@RequestParam UUID courseId,
                                  @RequestParam String studentId) {
        return enrollments.courseAccess(courseId, studentId);
    }

    @GetMapping("/internal/enrollments/roster")
    public List<EnrollmentDto> activeRoster(@RequestParam UUID courseId,
                                            @RequestParam Optional<UUID> cohortId) {
        return enrollments.activeRoster(courseId, cohortId);
    }

    @GetMapping("/internal/learner-memberships")
    public List<EnrollmentDto> learnerMemberships(@RequestParam String studentId) {
        return enrollments.learnerMemberships(studentId);
    }

    @GetMapping("/internal/enrollments/audit")
    public List<AuditLogEntryDto> auditLogQuery(
            @RequestParam Optional<UUID> enrollmentId,
            @RequestParam Optional<UUID> courseId,
            @RequestParam Optional<String> studentId,
            @RequestParam Optional<String> correlationId,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return enrollments.auditLog(enrollmentId, courseId, studentId, correlationId, limit, user);
    }

    @GetMapping("/internal/waitlist")
    public List<WaitlistEntryDto> waitlist(@RequestParam UUID courseId, CurrentUser user) {
        return enrollments.listWaitlist(courseId, user);
    }

    @PostMapping("/internal/waitlist")
    public WaitlistEntryDto joinWaitlist(@Valid @RequestBody WaitlistRequestDto request, CurrentUser user) {
        return enrollments.waitlist(request, user);
    }

    @GetMapping("/internal/enrollments/{id}")
    public EnrollmentDto get(@PathVariable UUID id, CurrentUser user) {
        return enrollments.get(id, user);
    }

    @GetMapping("/internal/enrollments/{id}/promotion-application")
    public EnrollmentPromotionApplicationStateDto promotionApplication(@PathVariable UUID id, CurrentUser user) {
        return enrollments.promotionApplication(id, user);
    }

    @GetMapping("/internal/enrollments/promotion-applications")
    public List<EnrollmentPromotionApplicationStateDto> promotionApplicationQueue(
            @RequestParam Optional<String> status,
            @RequestParam Optional<UUID> courseId,
            @RequestParam Optional<String> studentId,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return enrollments.promotionApplicationQueue(status, courseId, studentId, limit, user);
    }

    @GetMapping("/internal/enrollments/benefit-reconciliation")
    public EnrollmentBenefitReconciliationQueryResponseDto benefitReconciliation(
            @RequestParam Optional<UUID> enrollmentId,
            @RequestParam Optional<UUID> courseId,
            @RequestParam Optional<String> studentId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Boolean> includeMatched,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return enrollments.benefitReconciliation(
                enrollmentId,
                courseId,
                studentId,
                status,
                includeMatched,
                limit,
                user);
    }

    @PostMapping("/internal/enrollments/refund-drop-policy:evaluate")
    public RefundDropPolicyEvaluationResponseDto evaluateRefundDropPolicy(
            @Valid @RequestBody RefundDropPolicyEvaluateRequestDto request,
            CurrentUser user) {
        return enrollments.evaluateRefundDropPolicy(request, user);
    }

    @PostMapping("/internal/enrollments/promotion-applications/{id}:retry-commit")
    public EnrollmentPromotionApplicationStateDto retryPromotionApplicationCommit(
            @PathVariable UUID id,
            @RequestBody(required = false) PromotionApplicationActionRequestDto request,
            CurrentUser user) {
        return enrollments.retryPromotionApplicationCommit(id, request, user);
    }

    @PostMapping("/internal/enrollments/promotion-applications/{id}:cancel-reservation")
    public EnrollmentPromotionApplicationStateDto cancelPromotionApplicationReservation(
            @PathVariable UUID id,
            @RequestBody(required = false) PromotionApplicationActionRequestDto request,
            CurrentUser user) {
        return enrollments.cancelPromotionApplicationReservation(id, request, user);
    }

    @GetMapping("/internal/enrollments/remediation-cases")
    public List<EnrollmentRemediationCaseDto> remediationCaseQueue(
            @RequestParam Optional<String> status,
            @RequestParam Optional<UUID> courseId,
            @RequestParam Optional<UUID> enrollmentId,
            @RequestParam Optional<UUID> promotionApplicationId,
            @RequestParam Optional<UUID> orderId,
            @RequestParam Optional<String> studentId,
            @RequestParam Optional<UUID> couponId,
            @RequestParam Optional<UUID> redemptionId,
            @RequestParam Optional<String> correlationId,
            @RequestParam Optional<String> assigneeId,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return enrollments.remediationCaseQueue(
                status,
                courseId,
                enrollmentId,
                promotionApplicationId,
                orderId,
                studentId,
                couponId,
                redemptionId,
                correlationId,
                assigneeId,
                limit,
                user);
    }

    @GetMapping("/internal/enrollments/remediation-cases/{id}")
    public EnrollmentRemediationCaseDto remediationCase(@PathVariable UUID id, CurrentUser user) {
        return enrollments.remediationCase(id, user);
    }

    @PostMapping("/internal/enrollments/remediation-cases/{id}:assign")
    public EnrollmentRemediationCaseDto assignRemediationCase(
            @PathVariable UUID id,
            @Valid @RequestBody RemediationCaseAssignRequestDto request,
            CurrentUser user) {
        return enrollments.assignRemediationCase(id, request, user);
    }

    @PostMapping("/internal/enrollments/remediation-cases/{id}:note")
    public EnrollmentRemediationCaseDto addRemediationCaseNote(
            @PathVariable UUID id,
            @RequestBody(required = false) RemediationCaseActionRequestDto request,
            CurrentUser user) {
        return enrollments.addRemediationCaseNote(id, request, user);
    }

    @PostMapping("/internal/enrollments/remediation-cases/{id}:resolve")
    public EnrollmentRemediationCaseDto resolveRemediationCase(
            @PathVariable UUID id,
            @RequestBody(required = false) RemediationCaseActionRequestDto request,
            CurrentUser user) {
        return enrollments.resolveRemediationCase(id, request, user);
    }

    @PatchMapping("/internal/enrollments/{id}/status")
    public EnrollmentDto changeStatus(@PathVariable UUID id,
                                      @Valid @RequestBody ChangeStatusRequestDto req,
                                      CurrentUser user) {
        return enrollments.changeStatus(id, req, user);
    }

    @PostMapping("/internal/enrollments/batch")
    public BatchEnrollResultDto batchEnroll(@Valid @RequestBody BatchEnrollRequestDto req, CurrentUser user) {
        return enrollments.batchEnroll(req, user);
    }

    @PutMapping("/internal/courses/{courseId}/capacity")
    public void setCapacity(@PathVariable UUID courseId,
                            @Valid @RequestBody SetCapacityRequestDto req,
                            CurrentUser user) {
        enrollments.setCapacity(courseId, req, user);
    }

    @GetMapping("/internal/enrollments/stats")
    public EnrollmentStatsDto stats(@RequestParam UUID courseId, CurrentUser user) {
        return enrollments.stats(courseId, user);
    }

    @GetMapping("/internal/enrollments/{id}/audit")
    public List<AuditLogEntryDto> auditLog(@PathVariable UUID id, CurrentUser user) {
        return enrollments.auditLog(id, user);
    }

}
