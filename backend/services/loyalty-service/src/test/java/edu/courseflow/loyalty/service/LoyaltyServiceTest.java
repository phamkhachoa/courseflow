package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyIdempotencyKey;
import edu.courseflow.loyalty.model.LoyaltyPointLot;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.OutboxEvent;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAdjustmentApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyIdempotencyKeyRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class LoyaltyServiceTest {

    @Mock
    private LoyaltyProgramRepository programRepository;
    @Mock
    private LoyaltyAccountRepository accountRepository;
    @Mock
    private LoyaltyPointsEntryRepository pointsEntryRepository;
    @Mock
    private LoyaltyPointLotRepository pointLotRepository;
    @Mock
    private LoyaltyAdjustmentApprovalRepository adjustmentApprovalRepository;
    @Mock
    private LoyaltyIdempotencyKeyRepository idempotencyKeyRepository;
    @Mock
    private LoyaltyAuditEventRepository auditEventRepository;
    @Mock
    private OutboxEventRepository outboxEventRepository;
    @Mock
    private LoyaltyMetrics metrics;
    @Mock
    private LoyaltyAccessService access;

    private ObjectMapper objectMapper;
    private LoyaltyService service;
    private LoyaltyProgram program;
    private LoyaltyAccount account;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper().findAndRegisterModules();
        service = new LoyaltyService(
                programRepository,
                accountRepository,
                pointsEntryRepository,
                pointLotRepository,
                adjustmentApprovalRepository,
                idempotencyKeyRepository,
                auditEventRepository,
                outboxEventRepository,
                objectMapper,
                metrics,
                access);
        program = new LoyaltyProgram("courseflow", "lms", "default", "Default points", "POINT", false, 365, "test");
        account = new LoyaltyAccount(program, "profile-1");
    }

    @Test
    void earnCreatesAccountLedgerAuditOutboxAndIdempotency() throws Exception {
        PointsMutationRequestDto request = earnRequest("order-1", "earn-1", 100);
        when(programRepository.findByTenantIdAndApplicationIdAndProgramId("courseflow", "lms", "default"))
                .thenReturn(Optional.of(program));
        when(idempotencyKeyRepository.findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                "courseflow", "lms", "EARN", "earn-1"))
                .thenReturn(Optional.empty());
        when(accountRepository.findByScopeForUpdate(
                "courseflow", "lms", "default", "profile-1"))
                .thenReturn(Optional.empty());
        when(accountRepository.saveAndFlush(any(LoyaltyAccount.class))).thenReturn(account);
        when(pointsEntryRepository.findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                program.getId(), "EARN", "order-1"))
                .thenReturn(Optional.empty());
        when(pointsEntryRepository.balance(account.getId())).thenReturn(0L);
        when(pointsEntryRepository.save(any(LoyaltyPointsEntry.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(pointLotRepository.findBySourceEntryId(any(UUID.class))).thenReturn(Optional.empty());
        when(pointLotRepository.save(any(LoyaltyPointLot.class))).thenAnswer(invocation -> invocation.getArgument(0));

        PointsMutationResponseDto response = service.earn(request, null);

        assertThat(response.entryType()).isEqualTo("EARN");
        assertThat(response.pointsDelta()).isEqualTo(100);
        assertThat(response.balance()).isEqualTo(100);
        assertThat(response.idempotencyReplay()).isFalse();
        ArgumentCaptor<LoyaltyPointsEntry> entryCaptor = ArgumentCaptor.forClass(LoyaltyPointsEntry.class);
        verify(pointsEntryRepository).save(entryCaptor.capture());
        assertThat(entryCaptor.getValue().getExpiresAt()).isEqualTo(Instant.parse("2027-06-14T10:00:00Z"));
        verify(auditEventRepository).save(any());
        ArgumentCaptor<OutboxEvent> outboxCaptor = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outboxEventRepository).save(outboxCaptor.capture());
        assertThat(ReflectionTestUtils.getField(outboxCaptor.getValue(), "eventType"))
                .isEqualTo("loyalty.points.earned");
        Map<String, Object> payload = objectMapper.readValue(
                (String) ReflectionTestUtils.getField(outboxCaptor.getValue(), "payload"), Map.class);
        assertThat(payload)
                .containsEntry("schemaVersion", 1)
                .containsEntry("tenantId", "courseflow")
                .containsEntry("applicationId", "lms")
                .containsEntry("programId", "default")
                .containsEntry("profileId", "profile-1")
                .containsEntry("entryType", "EARN")
                .containsEntry("pointsDelta", 100);
        assertThat((Map<String, Object>) payload.get("metadata"))
                .containsEntry("correlationId", "corr-1");
        assertThat((Map<String, Object>) ((Map<String, Object>) payload.get("metadata")).get("attributes"))
                .containsEntry("pointUnit", "POINT");
        verify(idempotencyKeyRepository).save(any(LoyaltyIdempotencyKey.class));
        verify(metrics).outboxEnqueued("loyalty.points.earned");
    }

    @Test
    void burnRejectsOverdrawWhenProgramDoesNotAllowNegativeBalance() {
        PointsMutationRequestDto request = burnRequest("order-1-burn", "burn-1", 100);
        when(programRepository.findByTenantIdAndApplicationIdAndProgramId("courseflow", "lms", "default"))
                .thenReturn(Optional.of(program));
        when(idempotencyKeyRepository.findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                "courseflow", "lms", "BURN", "burn-1"))
                .thenReturn(Optional.empty());
        when(accountRepository.findByScopeForUpdate(
                "courseflow", "lms", "default", "profile-1"))
                .thenReturn(Optional.of(account));
        when(pointsEntryRepository.findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                program.getId(), "BURN", "order-1-burn"))
                .thenReturn(Optional.empty());
        when(pointsEntryRepository.balance(account.getId())).thenReturn(50L);

        assertThatThrownBy(() -> service.burn(request, null))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_INSUFFICIENT_BALANCE));
    }

    @Test
    void burnDoesNotInheritProgramDefaultExpiry() {
        PointsMutationRequestDto request = burnRequest("reward-1", "burn-1", 25);
        when(programRepository.findByTenantIdAndApplicationIdAndProgramId("courseflow", "lms", "default"))
                .thenReturn(Optional.of(program));
        when(idempotencyKeyRepository.findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                "courseflow", "lms", "BURN", "burn-1"))
                .thenReturn(Optional.empty());
        when(accountRepository.findByScopeForUpdate(
                "courseflow", "lms", "default", "profile-1"))
                .thenReturn(Optional.of(account));
        when(pointsEntryRepository.findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                program.getId(), "BURN", "reward-1"))
                .thenReturn(Optional.empty());
        when(pointsEntryRepository.balance(account.getId())).thenReturn(100L);
        when(pointLotRepository.activeRemainingPoints(any(UUID.class), any(Instant.class))).thenReturn(100L);
        when(pointLotRepository.activeRemainingLotsForUpdate(any(UUID.class), any(Instant.class)))
                .thenReturn(List.of(activeLot(100)));
        when(pointsEntryRepository.save(any(LoyaltyPointsEntry.class))).thenAnswer(invocation -> invocation.getArgument(0));

        PointsMutationResponseDto response = service.burn(request, null);

        assertThat(response.entryType()).isEqualTo("BURN");
        assertThat(response.pointsDelta()).isEqualTo(-25);
        assertThat(response.balance()).isEqualTo(75);
        ArgumentCaptor<LoyaltyPointsEntry> entryCaptor = ArgumentCaptor.forClass(LoyaltyPointsEntry.class);
        verify(pointsEntryRepository).save(entryCaptor.capture());
        assertThat(entryCaptor.getValue().getExpiresAt()).isNull();
    }

    @Test
    void idempotencyKeyReuseWithDifferentPayloadIsRejected() {
        PointsMutationRequestDto request = earnRequest("order-1", "earn-1", 100);
        LoyaltyIdempotencyKey existing = new LoyaltyIdempotencyKey(
                "courseflow",
                "lms",
                "EARN",
                "earn-1",
                "sha256:different",
                "{}",
                Instant.now().plus(30, ChronoUnit.DAYS));
        when(programRepository.findByTenantIdAndApplicationIdAndProgramId("courseflow", "lms", "default"))
                .thenReturn(Optional.of(program));
        when(idempotencyKeyRepository.findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                "courseflow", "lms", "EARN", "earn-1"))
                .thenReturn(Optional.of(existing));

        assertThatThrownBy(() -> service.earn(request, null))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_IDEMPOTENCY_KEY_REUSED));
    }

    @Test
    void deniedRuntimeBindingStopsEarnBeforeSideEffects() {
        PointsMutationRequestDto request = earnRequest("order-1", "earn-1", 100);
        when(programRepository.findByTenantIdAndApplicationIdAndProgramId("courseflow", "lms", "default"))
                .thenReturn(Optional.of(program));
        doThrow(ForbiddenException.coded(LoyaltyErrorCodes.LOYALTY_CLIENT_NOT_BOUND, "not bound"))
                .when(access).requireRuntimeOperation(program, null, "earn");

        assertThatThrownBy(() -> service.earn(request, null))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_CLIENT_NOT_BOUND));

        verifyNoInteractions(idempotencyKeyRepository, accountRepository, pointsEntryRepository, outboxEventRepository);
    }

    @Test
    void reverseCreatesCompensatingEntryAndUpdatesBalance() {
        LoyaltyPointsEntry original = new LoyaltyPointsEntry(
                account,
                "EARN",
                100,
                "order-1",
                "sha256:original",
                null,
                "purchase",
                "corr-1",
                "{}",
                Instant.parse("2026-06-14T10:00:00Z"),
                null);
        ReversePointsRequestDto request = new ReversePointsRequestDto(
                "reverse-1",
                "refund",
                "corr-reverse-1",
                Map.of("refundId", "refund-1"));
        when(pointsEntryRepository.findById(original.getId())).thenReturn(Optional.of(original));
        when(programRepository.findById(program.getId())).thenReturn(Optional.of(program));
        when(accountRepository.findByIdForUpdate(account.getId())).thenReturn(Optional.of(account));
        when(idempotencyKeyRepository.findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                "courseflow", "lms", "REVERSE", "reverse-1"))
                .thenReturn(Optional.empty());
        when(pointsEntryRepository.findFirstByReversalOfEntryId(original.getId())).thenReturn(Optional.empty());
        when(pointsEntryRepository.balance(account.getId())).thenReturn(100L);
        when(pointLotRepository.activeRemainingPoints(any(UUID.class), any(Instant.class))).thenReturn(100L);
        when(pointLotRepository.activeRemainingLotsForUpdate(any(UUID.class), any(Instant.class)))
                .thenReturn(List.of(activeLot(100)));
        when(pointsEntryRepository.save(any(LoyaltyPointsEntry.class))).thenAnswer(invocation -> invocation.getArgument(0));

        PointsMutationResponseDto response = service.reverse(original.getId(), request, null);

        assertThat(response.entryType()).isEqualTo("REVERSE");
        assertThat(response.pointsDelta()).isEqualTo(-100);
        assertThat(response.balance()).isEqualTo(0);
        assertThat(response.idempotencyReplay()).isFalse();
        verify(auditEventRepository).save(any());
        verify(outboxEventRepository).save(any());
        verify(idempotencyKeyRepository).save(any(LoyaltyIdempotencyKey.class));
    }

    private PointsMutationRequestDto earnRequest(String sourceReference, String idempotencyKey, long points) {
        return new PointsMutationRequestDto(
                "courseflow",
                "lms",
                "default",
                "profile-1",
                points,
                sourceReference,
                idempotencyKey,
                "purchase",
                "corr-1",
                Instant.parse("2026-06-14T10:00:00Z"),
                null,
                Map.of("orderId", sourceReference));
    }

    private LoyaltyPointLot activeLot(long points) {
        LoyaltyPointsEntry earn = new LoyaltyPointsEntry(
                account,
                "EARN",
                points,
                "seed-lot-" + points,
                "sha256:seed-" + points,
                null,
                "seed",
                "corr-seed",
                "{}",
                Instant.parse("2026-06-14T09:00:00Z"),
                Instant.parse("2027-06-14T09:00:00Z"));
        return new LoyaltyPointLot(earn);
    }

    private PointsMutationRequestDto burnRequest(String sourceReference, String idempotencyKey, long points) {
        return new PointsMutationRequestDto(
                "courseflow",
                "lms",
                "default",
                "profile-1",
                points,
                sourceReference,
                idempotencyKey,
                "redeem reward",
                "corr-2",
                Instant.parse("2026-06-14T10:10:00Z"),
                null,
                Map.of("rewardId", sourceReference));
    }
}
