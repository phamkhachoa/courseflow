package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterActionRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalReviewRequestDto;
import edu.courseflow.loyalty.model.LoyaltyInboundDeadLetter;
import edu.courseflow.loyalty.model.LoyaltyInboundDeadLetterApproval;
import edu.courseflow.loyalty.repository.LoyaltyInboundDeadLetterApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyInboundDeadLetterRepository;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;

@ExtendWith(MockitoExtension.class)
class LoyaltyInboundDeadLetterServiceTest {

    @Mock
    private LoyaltyInboundDeadLetterRepository deadLetters;
    @Mock
    private LoyaltyInboundDeadLetterApprovalRepository approvals;
    @Mock
    private LoyaltyAccessService access;
    @Mock
    private KafkaTemplate<Object, Object> kafkaTemplate;
    @Mock
    private LoyaltyMetrics metrics;

    private LoyaltyInboundDeadLetterService service;
    private CurrentUser maker;
    private CurrentUser checker;

    @BeforeEach
    void setUp() {
        service = new LoyaltyInboundDeadLetterService(
                deadLetters,
                approvals,
                access,
                new ObjectMapper().findAndRegisterModules(),
                kafkaTemplate,
                metrics);
        maker = new CurrentUser(1L, "maker@example.test", "ADMIN");
        checker = new CurrentUser(2L, "checker@example.test", "ADMIN");
    }

    @Test
    void replayRequiresApprovedApprovalId() {
        LoyaltyInboundDeadLetter deadLetter = deadLetter();
        when(deadLetters.findByIdForUpdate(deadLetter.getId())).thenReturn(Optional.of(deadLetter));

        assertThatThrownBy(() -> service.replay(
                deadLetter.getId(),
                new LoyaltyInboundDeadLetterActionRequestDto("broker fixed", false, null),
                maker))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("approvalId");

        verify(kafkaTemplate, never()).send(any(), any(), any());
    }

    @Test
    void requesterCannotApproveOwnInboundDltAction() {
        LoyaltyInboundDeadLetterApproval approval = new LoyaltyInboundDeadLetterApproval(
                UUID.randomUUID(),
                "REPLAY",
                "broker fixed",
                "INC-42",
                "LOYALTY_INBOUND_DLT_DUAL_CONTROL_V1",
                "sha256:payload",
                "sha256:request",
                "1");
        when(approvals.findByIdForUpdate(approval.getId())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.approveApproval(
                approval.getId(),
                new LoyaltyInboundDeadLetterApprovalReviewRequestDto("checked"),
                maker))
                .isInstanceOf(ForbiddenException.class);
    }

    @Test
    void replayWithApprovedApprovalPublishesAndMarksApprovalExecuted() {
        LoyaltyInboundDeadLetter deadLetter = deadLetter();
        when(deadLetters.findById(deadLetter.getId())).thenReturn(Optional.of(deadLetter));
        when(approvals.findFirstByDeadLetterIdAndActionAndRequestHashAndStatusInOrderByRequestedAtDesc(
                any(), any(), any(), any())).thenReturn(Optional.empty());
        when(approvals.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var submitted = service.requestApproval(
                deadLetter.getId(),
                new LoyaltyInboundDeadLetterApprovalRequestDto("REPLAY", "broker fixed", "INC-42"),
                maker);
        LoyaltyInboundDeadLetterApproval approval = approvals.save(new LoyaltyInboundDeadLetterApproval(
                submitted.deadLetterId(),
                submitted.action(),
                submitted.reason(),
                submitted.evidenceReference(),
                submitted.thresholdPolicy(),
                submitted.payloadHash(),
                submitted.requestHash(),
                submitted.requestedBy()));
        approval.approve("2", "checked");

        when(deadLetters.findByIdForUpdate(deadLetter.getId())).thenReturn(Optional.of(deadLetter));
        when(approvals.findByIdForUpdate(approval.getId())).thenReturn(Optional.of(approval));
        when(kafkaTemplate.send(deadLetter.getSourceTopic(), deadLetter.getRecordKey(), deadLetter.getPayload()))
                .thenReturn(CompletableFuture.completedFuture(null));
        when(deadLetters.save(deadLetter)).thenReturn(deadLetter);

        var response = service.replay(
                deadLetter.getId(),
                new LoyaltyInboundDeadLetterActionRequestDto("broker fixed", false, approval.getId()),
                checker);

        assertThat(response.replayed()).isTrue();
        assertThat(response.status()).isEqualTo("REPLAYED");
        assertThat(approval.getStatus()).isEqualTo("EXECUTED");
        verify(kafkaTemplate).send(deadLetter.getSourceTopic(), deadLetter.getRecordKey(), deadLetter.getPayload());
    }

    private LoyaltyInboundDeadLetter deadLetter() {
        String payload = "{\"event\":\"points\"}";
        return new LoyaltyInboundDeadLetter(
                "incentive.redemption.committed",
                "incentive.redemption.committed.DLT",
                "loyalty-service",
                0,
                42L,
                0,
                41L,
                "reservation-1",
                payload,
                LoyaltyInboundDeadLetterService.payloadHash(payload),
                "TimeoutException",
                "broker timeout",
                "stacktrace",
                "{}");
    }
}
