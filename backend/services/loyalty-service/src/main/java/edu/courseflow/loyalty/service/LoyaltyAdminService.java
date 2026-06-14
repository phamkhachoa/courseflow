package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ACCOUNT_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INVALID_READINESS_QUERY;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INVALID_RECONCILIATION_QUERY;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INVALID_STATUS;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_NOT_FOUND;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAccountDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAuditEventDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAuditQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBalanceBucketDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBalanceBucketResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramAdminDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramClientBindingDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyReconciliationEntryDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyReconciliationQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointLotBackfillAccountResultDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointLotBackfillRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointLotBackfillResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LedgerQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyApprovalEvidencePackDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsEntryDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyFinanceCloseoutExportDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyFinanceCloseoutTotalsDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramReadinessDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateAccountStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateProgramRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateProgramStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpsertClientBindingRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyAdjustmentApproval;
import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import edu.courseflow.loyalty.model.LoyaltyPointLot;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyProgramClientBinding;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAdjustmentApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramClientBindingRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyAdminService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };
    private static final String BALANCE_BUCKET_PROJECTION_MODE = "FIFO_BY_EXPIRY_THEN_OCCURRED_AT_READ_MODEL";
    private static final String LOT_ALLOCATIONS_METADATA_KEY = "lotAllocations";
    private static final Instant NO_EXPIRY = Instant.parse("9999-12-31T23:59:59Z");

    private final LoyaltyProgramRepository programs;
    private final LoyaltyProgramClientBindingRepository clientBindings;
    private final LoyaltyAccountRepository accounts;
    private final LoyaltyAdjustmentApprovalRepository adjustmentApprovals;
    private final LoyaltyPointLotRepository pointLots;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyAuditEventRepository auditEvents;
    private final OutboxEventRepository outboxEvents;
    private final LoyaltyAccessService access;
    private final ObjectMapper objectMapper;

    public LoyaltyAdminService(
            LoyaltyProgramRepository programs,
            LoyaltyProgramClientBindingRepository clientBindings,
            LoyaltyAccountRepository accounts,
            LoyaltyAdjustmentApprovalRepository adjustmentApprovals,
            LoyaltyPointLotRepository pointLots,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyAuditEventRepository auditEvents,
            OutboxEventRepository outboxEvents,
            LoyaltyAccessService access,
            ObjectMapper objectMapper) {
        this.programs = programs;
        this.clientBindings = clientBindings;
        this.accounts = accounts;
        this.adjustmentApprovals = adjustmentApprovals;
        this.pointLots = pointLots;
        this.pointsEntries = pointsEntries;
        this.auditEvents = auditEvents;
        this.outboxEvents = outboxEvents;
        this.access = access;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public List<LoyaltyProgramAdminDto> listPrograms(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> status,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        return programs.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        normalizedStatus(status.orElse(null)),
                        PageRequest.of(0, boundedLimit(limit.orElse(50))))
                .stream()
                .map(this::programDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public LoyaltyProgramAdminDto program(UUID programId, CurrentUser user) {
        LoyaltyProgram program = programById(programId);
        access.requireReadAccess(program.getTenantId(), program.getApplicationId(), user);
        return programDto(program);
    }

    @Transactional
    public LoyaltyProgramAdminDto updateProgram(
            UUID programId,
            UpdateProgramRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyProgram program = programById(programId);
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        program.update(request.name(), request.pointUnit(), request.allowNegativeBalance(),
                request.defaultPointsExpiryDays());
        LoyaltyProgram saved = programs.save(program);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("programId", saved.getProgramId());
        payload.put("name", saved.getName());
        payload.put("pointUnit", saved.getPointUnit());
        payload.put("allowNegativeBalance", saved.isAllowNegativeBalance());
        payload.put("defaultPointsExpiryDays", saved.getDefaultPointsExpiryDays());
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-program",
                "loyalty.program.updated", access.actorId(user), null, correlationId, payload);
        return programDto(saved);
    }

    @Transactional
    public LoyaltyProgramAdminDto updateProgramStatus(
            UUID programId,
            UpdateProgramStatusRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyProgram program = programById(programId);
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        try {
            program.changeStatus(request.status());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_INVALID_STATUS, ex.getMessage());
        }
        LoyaltyProgram saved = programs.save(program);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-program",
                "loyalty.program.status_changed", access.actorId(user), request.note(), correlationId, Map.of(
                        "programId", saved.getProgramId(),
                        "status", saved.getStatus()));
        return programDto(saved);
    }

    @Transactional
    public LoyaltyProgramClientBindingDto upsertClientBinding(
            UUID programId,
            UpsertClientBindingRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyProgram program = programById(programId);
        LoyaltyProgramClientBinding saved;
        try {
            saved = access.upsertClientBinding(program, request, user);
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_INVALID_STATUS, ex.getMessage());
        }
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-program-client-binding", "loyalty.program_client_binding.upserted",
                access.actorId(user), null, correlationId, Map.of(
                        "programUuid", program.getId().toString(),
                        "programId", program.getProgramId(),
                        "clientId", saved.getClientId(),
                        "status", saved.getStatus(),
                        "allowedOperations", readStringList(saved.getAllowedOperations())));
        return bindingDto(saved);
    }

    @Transactional(readOnly = true)
    public LoyaltyProgramReadinessDto programReadiness(
            String tenantId,
            String applicationId,
            String programId,
            Optional<String> clientId,
            Optional<String> operation,
            CurrentUser user) {
        String tenant = blankToNull(tenantId);
        String application = blankToNull(applicationId);
        String programKey = blankToNull(programId);
        if (tenant == null || application == null || programKey == null) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_READINESS_QUERY,
                    "tenantId, applicationId and programId are required for loyalty readiness");
        }

        String requestedOperation = readinessOperation(operation);
        if (!access.canReadAccess(tenant, application, user) && !access.canServiceOperation(user, requestedOperation)) {
            access.requireReadAccess(tenant, application, user);
        }
        String resolvedClientId = blankToNull(clientId.orElse(null));
        if (resolvedClientId == null) {
            resolvedClientId = blankToNull(access.sourceClientId(user));
        }
        List<String> blockers = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        Optional<LoyaltyProgram> maybeProgram = programs.findByTenantIdAndApplicationIdAndProgramId(
                tenant, application, programKey);
        if (maybeProgram.isEmpty()) {
            blockers.add("LOYALTY_PROGRAM_NOT_FOUND");
            return new LoyaltyProgramReadinessDto(
                    null,
                    tenant,
                    application,
                    programKey,
                    resolvedClientId,
                    requestedOperation,
                    false,
                    "MISSING",
                    false,
                    null,
                    List.of(),
                    blockers,
                    warnings);
        }

        LoyaltyProgram program = maybeProgram.get();
        if (!"ACTIVE".equalsIgnoreCase(program.getStatus())) {
            blockers.add("LOYALTY_PROGRAM_NOT_ACTIVE");
        }
        if (resolvedClientId == null) {
            blockers.add("LOYALTY_CLIENT_ID_REQUIRED");
        }

        LoyaltyProgramClientBinding binding = null;
        List<String> allowedOperations = List.of();
        if (resolvedClientId != null) {
            binding = clientBindings.findByTenantIdAndApplicationIdAndProgramIdAndClientId(
                            tenant, application, programKey, resolvedClientId)
                    .orElse(null);
            if (binding == null) {
                blockers.add("LOYALTY_CLIENT_NOT_BOUND");
            } else {
                allowedOperations = readStringList(binding.getAllowedOperations());
                if (!binding.active()) {
                    blockers.add("LOYALTY_CLIENT_BINDING_NOT_ACTIVE");
                }
                if (allowedOperations.stream().noneMatch(requestedOperation::equalsIgnoreCase)) {
                    blockers.add("LOYALTY_CLIENT_OPERATION_NOT_ALLOWED");
                }
            }
        }

        return new LoyaltyProgramReadinessDto(
                program.getId(),
                tenant,
                application,
                programKey,
                resolvedClientId,
                requestedOperation,
                blockers.isEmpty(),
                program.getStatus(),
                binding != null,
                binding == null ? null : binding.getStatus(),
                allowedOperations,
                blockers,
                warnings);
    }

    @Transactional(readOnly = true)
    public List<LoyaltyAccountDto> listAccounts(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<String> status,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        return accounts.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        blankToNull(profileId.orElse(null)),
                        normalizedStatus(status.orElse(null)),
                        PageRequest.of(0, boundedLimit(limit.orElse(50))))
                .stream()
                .map(this::accountDto)
                .toList();
    }

    @Transactional
    public PointLotBackfillResponseDto backfillPointLots(PointLotBackfillRequestDto request, CurrentUser user) {
        String tenantId = blankToNull(request.tenantId());
        String applicationId = blankToNull(request.applicationId());
        if (tenantId == null || applicationId == null) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_RECONCILIATION_QUERY,
                    "tenantId and applicationId are required for point lot backfill");
        }
        access.requireAdminAccess(tenantId, applicationId, user);
        boolean dryRun = request.dryRun() == null || request.dryRun();
        int limit = boundedLimit(request.limit() == null ? 50 : request.limit());
        String programId = blankToNull(request.programId());
        String profileId = blankToNull(request.profileId());
        Instant generatedAt = Instant.now();
        List<LoyaltyAccount> scopedAccounts = scopedBackfillAccounts(
                tenantId, applicationId, programId, profileId, request.accountId(), dryRun, limit);
        List<PointLotBackfillAccountResultDto> previewItems = scopedAccounts.stream()
                .map(account -> backfillAccountPointLots(account, true, generatedAt))
                .toList();
        String resultHash = pointLotBackfillResultHash(
                tenantId, applicationId, programId, profileId, request.accountId(), limit, previewItems);
        if (!dryRun) {
            String expectedResultHash = blankToNull(request.expectedResultHash());
            if (expectedResultHash == null) {
                throw BadRequestException.coded(
                        LOYALTY_INVALID_RECONCILIATION_QUERY,
                        "expectedResultHash is required to execute point lot backfill");
            }
            if (!expectedResultHash.equals(resultHash)) {
                throw ConflictException.coded(
                        LOYALTY_INVALID_RECONCILIATION_QUERY,
                        "Point lot backfill dry-run hash no longer matches current ledger state");
            }
        }
        List<PointLotBackfillAccountResultDto> items = dryRun
                ? previewItems
                : scopedAccounts.stream()
                .map(account -> backfillAccountPointLots(account, false, generatedAt))
                .toList();
        int affectedAccounts = (int) items.stream()
                .filter(item -> item.positiveEntryCount() > 0
                        || item.missingLotCount() > 0
                        || item.resetLotCount() > 0
                        || item.unallocatedDebitPoints() > 0)
                .count();
        int missingLots = items.stream().mapToInt(PointLotBackfillAccountResultDto::missingLotCount).sum();
        int resetLots = dryRun ? 0 : items.stream().mapToInt(PointLotBackfillAccountResultDto::resetLotCount).sum();
        long unallocatedDebit = items.stream().mapToLong(PointLotBackfillAccountResultDto::unallocatedDebitPoints).sum();
        List<String> warnings = new ArrayList<>();
        if (dryRun) {
            warnings.add("DRY_RUN_NO_LOTS_MUTATED");
        }
        boolean hasMore = scopedAccounts.size() == limit && request.accountId() == null;
        if (hasMore) {
            warnings.add("RESULT_LIMIT_REACHED");
        }
        if (unallocatedDebit > 0) {
            warnings.add("SOME_ACCOUNTS_HAVE_NEGATIVE_UNALLOCATED_DEBITS");
        }
        if (!dryRun) {
            audit(tenantId, applicationId, tenantId + "/" + applicationId, "loyalty-point-lot-backfill",
                    "loyalty.point_lots.backfilled", access.actorId(user), request.reason(),
                    request.correlationId(), Map.of(
                            "programId", programId == null ? "" : programId,
                            "profileId", profileId == null ? "" : profileId,
                            "accountId", request.accountId() == null ? "" : request.accountId().toString(),
                            "scannedAccountCount", scopedAccounts.size(),
                            "affectedAccountCount", affectedAccounts,
                            "missingLotCount", missingLots,
                            "resetLotCount", resetLots,
                            "unallocatedDebitPoints", unallocatedDebit,
                            "resultHash", resultHash));
        }
        return new PointLotBackfillResponseDto(
                tenantId,
                applicationId,
                programId,
                profileId,
                request.accountId(),
                dryRun,
                scopedAccounts.size(),
                affectedAccounts,
                missingLots,
                resetLots,
                unallocatedDebit,
                hasMore,
                resultHash,
                generatedAt,
                items,
                warnings);
    }

    @Transactional
    public LoyaltyAccountDto updateAccountStatus(
            UUID accountId,
            UpdateAccountStatusRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyAccount account = accounts.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        access.requireAdminAccess(account.getTenantId(), account.getApplicationId(), user);
        try {
            account.changeStatus(request.status());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_INVALID_STATUS, ex.getMessage());
        }
        LoyaltyAccount saved = accounts.save(account);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-account",
                "loyalty.account.status_changed", access.actorId(user), request.note(), correlationId, Map.of(
                        "programId", saved.getProgramId(),
                        "profileId", saved.getProfileId(),
                        "status", saved.getStatus()));
        return accountDto(saved);
    }

    @Transactional(readOnly = true)
    public LedgerQueryResponseDto ledger(UUID accountId, CurrentUser user) {
        LoyaltyAccount account = accounts.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        access.requireReadAccess(account.getTenantId(), account.getApplicationId(), user);
        List<PointsEntryDto> items = pointsEntries.findTop100ByAccountIdOrderByCreatedAtDesc(accountId)
                .stream()
                .map(this::entryDto)
                .toList();
        return new LedgerQueryResponseDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                pointsEntries.balance(account.getId()),
                items);
    }

    @Transactional(readOnly = true)
    public LoyaltyBalanceBucketResponseDto balanceBuckets(UUID accountId, Optional<Instant> asOf, CurrentUser user) {
        LoyaltyAccount account = accounts.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        access.requireAdminAccess(account.getTenantId(), account.getApplicationId(), user);
        Instant effectiveAsOf = asOf.orElseGet(Instant::now);
        List<LoyaltyPointLot> materializedLots = pointLots.findByAccountIdOrderByExpiresAtAscOccurredAtAsc(accountId);
        if (!materializedLots.isEmpty()) {
            List<LoyaltyBalanceBucketDto> buckets = materializedLots.stream()
                    .filter(lot -> lot.getRemainingPoints() > 0)
                    .map(lot -> bucketDto(lot, effectiveAsOf))
                    .toList();
            long activePoints = buckets.stream()
                    .filter(bucket -> "ACTIVE".equals(bucket.status()))
                    .mapToLong(LoyaltyBalanceBucketDto::remainingPoints)
                    .sum();
            long expiredPoints = buckets.stream()
                    .filter(bucket -> "EXPIRED".equals(bucket.status()))
                    .mapToLong(LoyaltyBalanceBucketDto::remainingPoints)
                    .sum();
            long ledgerBalance = pointsEntries.balance(account.getId());
            long remainingPoints = buckets.stream().mapToLong(LoyaltyBalanceBucketDto::remainingPoints).sum();
            long unallocatedDebitPoints = Math.max(0L, remainingPoints - ledgerBalance);
            List<String> warnings = new ArrayList<>();
            warnings.add("MATERIALIZED_LOTS_ARE_OPERATIONAL_SETTLEMENT_STATE");
            if (unallocatedDebitPoints > 0) {
                warnings.add("NEGATIVE_BALANCE_HAS_UNALLOCATED_DEBITS");
            }
            return new LoyaltyBalanceBucketResponseDto(
                    account.getId(),
                    account.getTenantId(),
                    account.getApplicationId(),
                    account.getProgramId(),
                    account.getProfileId(),
                    ledgerBalance,
                    activePoints,
                    expiredPoints,
                    unallocatedDebitPoints,
                    "MATERIALIZED_REMAINING_LOT_TABLE",
                    effectiveAsOf,
                    buckets,
                    warnings);
        }
        List<LoyaltyPointsEntry> entries = pointsEntries.findByAccountIdOrderByOccurredAtAscCreatedAtAsc(accountId);
        BucketProjection projection = projectBuckets(entries);
        List<LoyaltyBalanceBucketDto> buckets = projection.lots().stream()
                .filter(lot -> lot.remainingPoints > 0)
                .map(lot -> bucketDto(lot, effectiveAsOf))
                .toList();
        long activePoints = buckets.stream()
                .filter(bucket -> "ACTIVE".equals(bucket.status()))
                .mapToLong(LoyaltyBalanceBucketDto::remainingPoints)
                .sum();
        long expiredPoints = buckets.stream()
                .filter(bucket -> "EXPIRED".equals(bucket.status()))
                .mapToLong(LoyaltyBalanceBucketDto::remainingPoints)
                .sum();
        long ledgerBalance = pointsEntries.balance(account.getId());
        long projectedBalance = buckets.stream().mapToLong(LoyaltyBalanceBucketDto::remainingPoints).sum()
                - projection.unallocatedDebitPoints();
        List<String> warnings = new ArrayList<>();
        warnings.add("READ_ONLY_FIFO_PROJECTION_NOT_A_SETTLEMENT_LEDGER");
        if (projection.unallocatedDebitPoints() > 0) {
            warnings.add("NEGATIVE_BALANCE_HAS_UNALLOCATED_DEBITS");
        }
        if (ledgerBalance != projectedBalance) {
            warnings.add("PROJECTION_BALANCE_MISMATCH");
        }
        return new LoyaltyBalanceBucketResponseDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                ledgerBalance,
                activePoints,
                expiredPoints,
                projection.unallocatedDebitPoints(),
                BALANCE_BUCKET_PROJECTION_MODE,
                effectiveAsOf,
                buckets,
                warnings);
    }

    @Transactional(readOnly = true)
    public LoyaltyReconciliationQueryResponseDto reconciliationEntries(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<UUID> accountId,
            Optional<String> entryType,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant == null || application == null) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_RECONCILIATION_QUERY,
                    "tenantId and applicationId are required for loyalty reconciliation queries");
        }
        access.requireReadAccess(tenant, application, user);
        if (from.isPresent() && to.isPresent() && !from.get().isBefore(to.get())) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_RECONCILIATION_QUERY,
                    "Reconciliation from timestamp must be before to timestamp");
        }
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyPointsEntry> rows = pointsEntries.searchReconciliationEntries(
                tenant,
                application,
                blankToNull(programId.orElse(null)),
                blankToNull(profileId.orElse(null)),
                accountId.orElse(null),
                normalizeEntryType(entryType.orElse(null)),
                from.orElse(null),
                to.orElse(null),
                PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        return new LoyaltyReconciliationQueryResponseDto(
                rows.stream().limit(pageSize).map(this::reconciliationDto).toList(),
                pageSize,
                hasMore,
                Instant.now());
    }

    @Transactional(readOnly = true)
    public LoyaltyAdjustmentApprovalQueryResponseDto adjustmentApprovals(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<String> status,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant == null || application == null) {
            access.requirePlatformAdmin(user);
            return new LoyaltyAdjustmentApprovalQueryResponseDto(List.of(), boundedLimit(limit.orElse(50)), false);
        }
        access.requireReadAccess(tenant, application, user);
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyAdjustmentApproval> rows = adjustmentApprovals.search(
                tenant,
                application,
                blankToNull(programId.orElse(null)),
                blankToNull(profileId.orElse(null)),
                normalizedStatus(status.orElse(null)),
                from.orElse(null),
                to.orElse(null),
                PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        return new LoyaltyAdjustmentApprovalQueryResponseDto(
                rows.stream().limit(pageSize).map(this::approvalDto).toList(),
                pageSize,
                hasMore);
    }

    @Transactional(readOnly = true)
    public LoyaltyApprovalEvidencePackDto approvalEvidencePack(UUID approvalId, CurrentUser user) {
        LoyaltyAdjustmentApproval approval = adjustmentApprovals.findById(approvalId)
                .orElseThrow(() -> NotFoundException.coded(
                        "LOYALTY_ADJUSTMENT_APPROVAL_NOT_FOUND",
                        "Loyalty approval not found"));
        access.requireReadAccess(approval.getTenantId(), approval.getApplicationId(), user);
        Map<String, Object> metadata = readMap(approval.getMetadataJson());
        String operationType = approvalOperationType(metadata);
        List<LoyaltyAuditEventDto> audit = auditEvents.search(
                        approval.getTenantId(),
                        approval.getApplicationId(),
                        operationType.equals("EXPIRY") ? "loyalty-expiry-approval" : "loyalty-adjustment-approval",
                        approval.getId().toString(),
                        null,
                        null,
                        null,
                        Instant.EPOCH,
                        Instant.parse("9999-12-31T23:59:59Z"),
                        PageRequest.of(0, 200))
                .stream()
                .map(this::auditDto)
                .toList();
        List<LoyaltyReconciliationEntryDto> ledgerEntries = evidenceLedgerEntries(approval, operationType)
                .stream()
                .map(this::reconciliationDto)
                .toList();
        List<String> warnings = evidenceWarnings(approval, operationType, ledgerEntries);
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("operationType", operationType);
        summary.put("approvalStatus", approval.getStatus());
        summary.put("requestedBy", approval.getRequestedBy());
        summary.put("reviewedBy", approval.getReviewedBy());
        summary.put("executedAt", approval.getExecutedAt());
        summary.put("ledgerEntryCount", ledgerEntries.size());
        summary.put("netPoints", ledgerEntries.stream().mapToLong(LoyaltyReconciliationEntryDto::pointsDelta).sum());
        summary.put("pendingOutboxCount", ledgerEntries.stream()
                .filter(entry -> "PENDING_OUTBOX".equals(entry.outboxStatus()))
                .count());
        summary.put("missingOutboxCount", ledgerEntries.stream()
                .filter(entry -> "MISSING_OUTBOX".equals(entry.outboxStatus()))
                .count());
        summary.put("metadata", metadata);
        return new LoyaltyApprovalEvidencePackDto(
                approval.getId(),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getProgramId(),
                operationType,
                Instant.now(),
                approvalDto(approval),
                audit,
                ledgerEntries,
                summary,
                warnings);
    }

    @Transactional(readOnly = true)
    public LoyaltyFinanceCloseoutExportDto financeCloseout(
            String tenantId,
            String applicationId,
            Optional<String> programId,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            Optional<String> cursor,
            CurrentUser user) {
        String tenant = blankToNull(tenantId);
        String application = blankToNull(applicationId);
        if (tenant == null || application == null) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_RECONCILIATION_QUERY,
                    "tenantId and applicationId are required for finance closeout");
        }
        access.requireReadAccess(tenant, application, user);
        Instant fromInstant = from.orElse(Instant.EPOCH);
        Instant toInstant = to.orElse(Instant.parse("9999-12-31T23:59:59Z"));
        String closeoutProgramId = blankToNull(programId.orElse(null));
        CloseoutCursor closeoutCursor = closeoutCursor(cursor);
        int pageSize = Math.max(1, Math.min(limit.orElse(closeoutCursor == null ? 1000 : closeoutCursor.limit()), 5000));
        int pageIndex = closeoutCursor == null ? 0 : closeoutCursor.page();
        if (closeoutCursor != null && closeoutCursor.limit() != pageSize) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_RECONCILIATION_QUERY,
                    "Closeout cursor must be used with the same limit");
        }
        LoyaltyFinanceCloseoutTotalsDto totals = financeTotals(
                tenant,
                application,
                closeoutProgramId,
                fromInstant,
                toInstant);
        List<LoyaltyPointsEntry> rows = pointsEntries.searchReconciliationEntries(
                tenant,
                application,
                closeoutProgramId,
                null,
                null,
                null,
                fromInstant,
                toInstant,
                PageRequest.of(pageIndex, pageSize));
        boolean hasMore = ((long) pageIndex + 1L) * pageSize < totals.entryCount();
        String nextCursor = hasMore ? encodeCloseoutCursor(pageIndex + 1, pageSize) : null;
        List<LoyaltyReconciliationEntryDto> items = rows.stream()
                .map(this::reconciliationDto)
                .toList();
        List<String> warnings = new ArrayList<>();
        if (hasMore) {
            warnings.add("RESULT_LIMIT_REACHED");
        }
        if (totals.pendingOutboxCount() > 0) {
            warnings.add("PENDING_OUTBOX_EVENTS");
        }
        if (totals.missingOutboxCount() > 0) {
            warnings.add("MISSING_OUTBOX_EVENTS");
        }
        if (hasMore) {
            warnings.add("CLOSEOUT_EXPORT_NOT_COMPLETE");
        }
        String resultHash = financeCloseoutResultHash(
                tenant,
                application,
                closeoutProgramId,
                fromInstant,
                toInstant,
                totals);
        boolean certifiable = !hasMore
                && totals.pendingOutboxCount() == 0
                && totals.missingOutboxCount() == 0;
        if (!certifiable) {
            warnings.add("CLOSEOUT_NOT_CERTIFIABLE");
        }
        return new LoyaltyFinanceCloseoutExportDto(
                "loyalty-closeout-" + resultHash.substring(0, 24),
                tenant,
                application,
                closeoutProgramId,
                fromInstant,
                toInstant,
                resultHash,
                certifiable,
                Instant.now(),
                totals,
                items,
                pageSize,
                hasMore,
                nextCursor,
                warnings);
    }

    @Transactional(readOnly = true)
    public LoyaltyAuditQueryResponseDto audit(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> aggregateType,
            Optional<String> aggregateId,
            Optional<String> action,
            Optional<String> actorId,
            Optional<String> correlationId,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyAuditEvent> rows = auditEvents.search(
                blankToNull(tenantId.orElse(null)),
                blankToNull(applicationId.orElse(null)),
                blankToNull(aggregateType.orElse(null)),
                blankToNull(aggregateId.orElse(null)),
                blankToNull(action.orElse(null)),
                blankToNull(actorId.orElse(null)),
                blankToNull(correlationId.orElse(null)),
                from.orElse(Instant.EPOCH),
                to.orElse(Instant.parse("9999-12-31T23:59:59Z")),
                PageRequest.of(0, pageSize + 1));
        return auditResponse(rows, pageSize);
    }

    @Transactional(readOnly = true)
    public LoyaltyAuditQueryResponseDto programTimeline(UUID programId, Optional<Integer> limit, CurrentUser user) {
        LoyaltyProgram program = programById(programId);
        access.requireReadAccess(program.getTenantId(), program.getApplicationId(), user);
        int pageSize = boundedLimit(limit.orElse(100));
        List<String> aggregateIds = new ArrayList<>();
        aggregateIds.add(program.getId().toString());
        clientBindings.findByTenantIdAndApplicationIdAndProgramId(
                        program.getTenantId(), program.getApplicationId(), program.getProgramId())
                .forEach(binding -> aggregateIds.add(binding.getId().toString()));
        List<LoyaltyAuditEvent> rows = auditEvents.timeline(
                program.getTenantId(),
                program.getApplicationId(),
                aggregateIds,
                PageRequest.of(0, pageSize + 1));
        return auditResponse(rows, pageSize);
    }

    @Transactional(readOnly = true)
    public LoyaltyAuditQueryResponseDto accountTimeline(UUID accountId, Optional<Integer> limit, CurrentUser user) {
        LoyaltyAccount account = accounts.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        access.requireReadAccess(account.getTenantId(), account.getApplicationId(), user);
        int pageSize = boundedLimit(limit.orElse(100));
        List<LoyaltyAuditEvent> rows = auditEvents.timeline(
                account.getTenantId(),
                account.getApplicationId(),
                List.of(account.getId().toString()),
                PageRequest.of(0, pageSize + 1));
        return auditResponse(rows, pageSize);
    }

    private void requireAdminForScope(Optional<String> tenantId, Optional<String> applicationId, CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireAdminAccess(tenant, application, user);
            return;
        }
        access.requirePlatformAdmin(user);
    }

    private void requireReadForScope(Optional<String> tenantId, Optional<String> applicationId, CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireReadAccess(tenant, application, user);
            return;
        }
        access.requirePlatformAdmin(user);
    }

    private LoyaltyProgram programById(UUID programId) {
        return programs.findById(programId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private LoyaltyProgramAdminDto programDto(LoyaltyProgram program) {
        return new LoyaltyProgramAdminDto(
                program.getId(),
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                program.getName(),
                program.getPointUnit(),
                program.getStatus(),
                program.isAllowNegativeBalance(),
                program.getDefaultPointsExpiryDays(),
                program.getCreatedAt(),
                program.getUpdatedAt(),
                clientBindings.findByTenantIdAndApplicationIdAndProgramId(
                                program.getTenantId(), program.getApplicationId(), program.getProgramId())
                        .stream()
                        .map(this::bindingDto)
                        .toList());
    }

    private LoyaltyProgramClientBindingDto bindingDto(LoyaltyProgramClientBinding binding) {
        return new LoyaltyProgramClientBindingDto(
                binding.getId(),
                binding.getTenantId(),
                binding.getApplicationId(),
                binding.getProgramId(),
                binding.getClientId(),
                binding.getStatus(),
                readStringList(binding.getAllowedOperations()),
                binding.getCreatedBy(),
                binding.getCreatedAt(),
                binding.getUpdatedAt());
    }

    private LoyaltyAccountDto accountDto(LoyaltyAccount account) {
        return new LoyaltyAccountDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                account.getStatus(),
                pointsEntries.balance(account.getId()),
                account.getOpenedAt());
    }

    private LoyaltyAdjustmentApprovalDto approvalDto(LoyaltyAdjustmentApproval approval) {
        Map<String, Object> metadata = readMap(approval.getMetadataJson());
        String operationType = approvalOperationType(metadata);
        return new LoyaltyAdjustmentApprovalDto(
                approval.getId(),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getProgramId(),
                approval.getProfileId(),
                approval.getPointsDelta(),
                approval.getSourceReference(),
                approval.getReason(),
                approval.getCorrelationId(),
                approval.getOccurredAt(),
                approval.getExpiresAt(),
                approval.getStatus(),
                approval.getRequestedBy(),
                approval.getReviewedBy(),
                approval.getReviewNote(),
                approval.getRequestedAt(),
                approval.getReviewedAt(),
                approval.getExecutedAt(),
                approval.getExecutedEntryId(),
                operationType,
                metadata);
    }

    private String approvalOperationType(Map<String, Object> metadata) {
        Object raw = metadata.get("operationType");
        return raw == null || raw.toString().isBlank() ? "ADJUSTMENT" : raw.toString().trim();
    }

    private List<LoyaltyPointsEntry> evidenceLedgerEntries(
            LoyaltyAdjustmentApproval approval,
            String operationType) {
        if ("ADJUSTMENT".equalsIgnoreCase(operationType) && approval.getExecutedEntryId() != null) {
            return pointsEntries.findById(approval.getExecutedEntryId())
                    .map(entry -> List.of(entry))
                    .orElseGet(() -> List.of());
        }
        if ("EXPIRY".equalsIgnoreCase(operationType)) {
            return pointsEntries.findEvidenceEntries(
                    approval.getTenantId(),
                    approval.getApplicationId(),
                    approval.getProgramId(),
                    approval.getCorrelationId(),
                    null,
                    PageRequest.of(0, 500));
        }
        return pointsEntries.findEvidenceEntries(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getProgramId(),
                approval.getCorrelationId(),
                approval.getSourceReference(),
                PageRequest.of(0, 200));
    }

    private List<String> evidenceWarnings(
            LoyaltyAdjustmentApproval approval,
            String operationType,
            List<LoyaltyReconciliationEntryDto> ledgerEntries) {
        List<String> warnings = new ArrayList<>();
        if ("EXPIRY".equalsIgnoreCase(operationType)
                && "EXECUTED".equals(approval.getStatus())
                && ledgerEntries.isEmpty()) {
            warnings.add("EXECUTED_EXPIRY_HAS_NO_LEDGER_ENTRIES");
        }
        if ("ADJUSTMENT".equalsIgnoreCase(operationType)
                && "EXECUTED".equals(approval.getStatus())
                && approval.getExecutedEntryId() != null
                && ledgerEntries.isEmpty()) {
            warnings.add("EXECUTED_ADJUSTMENT_ENTRY_NOT_FOUND");
        }
        if (ledgerEntries.stream().anyMatch(entry -> "PENDING_OUTBOX".equals(entry.outboxStatus()))) {
            warnings.add("PENDING_OUTBOX_EVENTS");
        }
        if (ledgerEntries.stream().anyMatch(entry -> "MISSING_OUTBOX".equals(entry.outboxStatus()))) {
            warnings.add("MISSING_OUTBOX_EVENTS");
        }
        return warnings;
    }

    private LoyaltyFinanceCloseoutTotalsDto financeTotals(
            String tenantId,
            String applicationId,
            String programId,
            Instant from,
            Instant to) {
        LoyaltyPointsEntryRepository.FinanceTotalsProjection ledgerTotals = pointsEntries.financeTotals(
                tenantId,
                applicationId,
                programId,
                from,
                to);
        long pendingOutbox = outboxEvents.countPendingLoyaltyPointEntries(
                tenantId,
                applicationId,
                programId,
                from,
                to);
        long missingOutbox = outboxEvents.countMissingLoyaltyPointEntries(
                tenantId,
                applicationId,
                programId,
                from,
                to);
        return new LoyaltyFinanceCloseoutTotalsDto(
                valueOrZero(ledgerTotals.getEarnedPoints()),
                valueOrZero(ledgerTotals.getBurnedPoints()),
                valueOrZero(ledgerTotals.getReversedPoints()),
                valueOrZero(ledgerTotals.getAdjustedPoints()),
                valueOrZero(ledgerTotals.getExpiredPoints()),
                valueOrZero(ledgerTotals.getNetPoints()),
                safeInt(valueOrZero(ledgerTotals.getEntryCount())),
                safeInt(pendingOutbox),
                safeInt(missingOutbox));
    }

    private long valueOrZero(Long value) {
        return value == null ? 0L : value;
    }

    private int safeInt(long value) {
        return value > Integer.MAX_VALUE ? Integer.MAX_VALUE : (int) value;
    }

    private BucketProjection projectBuckets(List<LoyaltyPointsEntry> entries) {
        List<PointLot> lots = new ArrayList<>();
        long unallocatedDebitPoints = 0;
        for (LoyaltyPointsEntry entry : entries) {
            long delta = entry.getPointsDelta();
            if (delta > 0) {
                lots.add(new PointLot(entry, delta));
                continue;
            }
            if (delta < 0) {
                long debit = Math.abs(delta);
                List<PointLot> allocationOrder = lots.stream()
                        .filter(lot -> lot.remainingPoints > 0)
                        .sorted(pointLotComparator())
                        .toList();
                for (PointLot lot : allocationOrder) {
                    if (debit == 0) {
                        break;
                    }
                    long consumed = Math.min(lot.remainingPoints, debit);
                    lot.remainingPoints -= consumed;
                    debit -= consumed;
                }
                unallocatedDebitPoints += debit;
            }
        }
        return new BucketProjection(lots, unallocatedDebitPoints);
    }

    private Comparator<PointLot> pointLotComparator() {
        return Comparator
                .comparing((PointLot lot) -> lot.entry.getExpiresAt() == null ? NO_EXPIRY : lot.entry.getExpiresAt())
                .thenComparing(lot -> lot.entry.getOccurredAt())
                .thenComparing(lot -> lot.entry.getCreatedAt());
    }

    private LoyaltyBalanceBucketDto bucketDto(PointLot lot, Instant asOf) {
        LoyaltyPointsEntry entry = lot.entry;
        String status = entry.getExpiresAt() != null && !entry.getExpiresAt().isAfter(asOf) ? "EXPIRED" : "ACTIVE";
        return new LoyaltyBalanceBucketDto(
                entry.getId(),
                entry.getAccountId(),
                entry.getProfileId(),
                entry.getEntryType(),
                lot.originalPoints,
                lot.originalPoints - lot.remainingPoints,
                lot.remainingPoints,
                entry.getSourceReference(),
                entry.getOccurredAt(),
                entry.getExpiresAt(),
                status);
    }

    private LoyaltyBalanceBucketDto bucketDto(LoyaltyPointLot lot, Instant asOf) {
        String status = lot.getExpiresAt() != null && !lot.getExpiresAt().isAfter(asOf) ? "EXPIRED" : "ACTIVE";
        return new LoyaltyBalanceBucketDto(
                lot.getSourceEntryId(),
                lot.getAccountId(),
                lot.getProfileId(),
                lot.getEntryType(),
                lot.getOriginalPoints(),
                lot.getConsumedPoints(),
                lot.getRemainingPoints(),
                lot.getSourceReference(),
                lot.getOccurredAt(),
                lot.getExpiresAt(),
                status);
    }

    private LoyaltyReconciliationEntryDto reconciliationDto(LoyaltyPointsEntry entry) {
        String outboxStatus = outboxStatus(entry);
        return new LoyaltyReconciliationEntryDto(
                entry.getId(),
                entry.getId() + ":" + entry.getEntryType(),
                reconciliationStatus(outboxStatus),
                reconciliationReasons(outboxStatus),
                entry.getPointsDelta() >= 0 ? "CREDIT" : "DEBIT",
                entry.getEntryType(),
                entry.getAccountId(),
                entry.getTenantId(),
                entry.getApplicationId(),
                entry.getProgramId(),
                entry.getProfileId(),
                entry.getPointsDelta(),
                entry.getSourceReference(),
                entry.getReversalOfEntryId(),
                outboxStatus,
                entry.getCorrelationId(),
                entry.getOccurredAt(),
                entry.getExpiresAt(),
                entry.getCreatedAt());
    }

    private String outboxStatus(LoyaltyPointsEntry entry) {
        String aggregateId = entry.getId().toString();
        long outboxCount = outboxEvents.countLoyaltyPointEvents(aggregateId);
        if (outboxCount == 0) {
            return "MISSING_OUTBOX";
        }
        long publishedCount = outboxEvents.countPublishedLoyaltyPointEvents(aggregateId);
        return publishedCount > 0 ? "PUBLISHED" : "PENDING_OUTBOX";
    }

    private String reconciliationStatus(String outboxStatus) {
        return switch (outboxStatus) {
            case "PUBLISHED" -> "MATCHED";
            case "PENDING_OUTBOX" -> "PENDING";
            default -> "MISSING_OUTBOX";
        };
    }

    private List<String> reconciliationReasons(String outboxStatus) {
        return "PUBLISHED".equals(outboxStatus) ? List.of() : List.of(outboxStatus);
    }

    private PointsEntryDto entryDto(LoyaltyPointsEntry entry) {
        return new PointsEntryDto(
                entry.getId(),
                entry.getAccountId(),
                entry.getTenantId(),
                entry.getApplicationId(),
                entry.getProgramId(),
                entry.getProfileId(),
                entry.getEntryType(),
                entry.getPointsDelta(),
                entry.getSourceReference(),
                entry.getReversalOfEntryId(),
                entry.getReason(),
                entry.getCorrelationId(),
                entry.getOccurredAt(),
                entry.getExpiresAt(),
                entry.getCreatedAt());
    }

    private LoyaltyAuditQueryResponseDto auditResponse(List<LoyaltyAuditEvent> rows, int limit) {
        boolean hasMore = rows.size() > limit;
        return new LoyaltyAuditQueryResponseDto(
                rows.stream().limit(limit).map(this::auditDto).toList(),
                limit,
                hasMore);
    }

    private LoyaltyAuditEventDto auditDto(LoyaltyAuditEvent event) {
        return new LoyaltyAuditEventDto(
                event.getId(),
                event.getTenantId(),
                event.getApplicationId(),
                event.getAggregateId(),
                event.getAggregateType(),
                event.getAction(),
                event.getActorId(),
                event.getNote(),
                readMap(event.getPayloadJson()),
                event.getCorrelationId(),
                event.getCreatedAt());
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, String correlationId, Map<String, Object> payload) {
        auditEvents.save(new LoyaltyAuditEvent(
                tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, correlationId,
                toJson(payload)));
    }

    private List<LoyaltyAccount> scopedBackfillAccounts(
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            UUID accountId,
            boolean dryRun,
            int limit) {
        if (accountId != null) {
            LoyaltyAccount account = (dryRun ? accounts.findById(accountId) : accounts.findByIdForUpdate(accountId))
                    .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
            if (!account.getTenantId().equals(tenantId)
                    || !account.getApplicationId().equals(applicationId)
                    || (programId != null && !account.getProgramId().equals(programId))
                    || (profileId != null && !account.getProfileId().equals(profileId))) {
                throw BadRequestException.coded(
                        LOYALTY_INVALID_RECONCILIATION_QUERY,
                        "Backfill accountId does not belong to the requested scope");
            }
            return List.of(account);
        }
        List<LoyaltyAccount> scopedAccounts = accounts.search(
                tenantId,
                applicationId,
                programId,
                profileId,
                null,
                PageRequest.of(0, limit));
        if (dryRun) {
            return scopedAccounts;
        }
        List<LoyaltyAccount> lockedAccounts = new ArrayList<>();
        scopedAccounts.stream()
                .map(LoyaltyAccount::getId)
                .sorted(Comparator.comparing(UUID::toString))
                .forEach(id -> lockedAccounts.add(accounts.findByIdForUpdate(id)
                        .orElseThrow(() -> NotFoundException.coded(
                                LOYALTY_ACCOUNT_NOT_FOUND,
                                "Loyalty account not found"))));
        return lockedAccounts;
    }

    private PointLotBackfillAccountResultDto backfillAccountPointLots(
            LoyaltyAccount account,
            boolean dryRun,
            Instant generatedAt) {
        List<LoyaltyPointsEntry> entries = pointsEntries.findByAccountIdOrderByOccurredAtAscCreatedAtAsc(account.getId());
        List<LoyaltyPointLot> existingLots = dryRun
                ? pointLots.findByAccountIdOrderByExpiresAtAscOccurredAtAsc(account.getId())
                : pointLots.findByAccountIdForUpdate(account.getId());
        Map<UUID, LoyaltyPointLot> existingBySource = new HashMap<>();
        for (LoyaltyPointLot lot : existingLots) {
            existingBySource.put(lot.getSourceEntryId(), lot);
        }

        List<BackfillLot> projectedLots = projectBackfillLots(entries);
        int positiveEntryCount = (int) entries.stream().filter(entry -> entry.getPointsDelta() > 0).count();
        int debitEntryCount = (int) entries.stream().filter(entry -> entry.getPointsDelta() < 0).count();
        int missingLotCount = (int) entries.stream()
                .filter(entry -> entry.getPointsDelta() > 0)
                .filter(entry -> !existingBySource.containsKey(entry.getId()))
                .count();
        int resetLotCount = existingLots.size();
        if (!dryRun) {
            List<LoyaltyPointLot> lotsToSave = new ArrayList<>();
            for (BackfillLot projected : projectedLots) {
                LoyaltyPointLot lot = existingBySource.get(projected.entry.getId());
                if (lot == null) {
                    lot = new LoyaltyPointLot(projected.entry);
                } else {
                    lot.resetConsumption();
                }
                long consumedPoints = projected.originalPoints - projected.remainingPoints;
                if (consumedPoints > 0) {
                    lot.consume(consumedPoints);
                }
                lotsToSave.add(lot);
            }
            pointLots.saveAll(lotsToSave);
        }

        long ledgerBalance = pointsEntries.balance(account.getId());
        long projectedRemainingPoints = projectedLots.stream().mapToLong(lot -> lot.remainingPoints).sum();
        long projectedExpiredPoints = projectedLots.stream()
                .filter(lot -> lot.entry.getExpiresAt() != null && !lot.entry.getExpiresAt().isAfter(generatedAt))
                .mapToLong(lot -> lot.remainingPoints)
                .sum();
        long unallocatedDebitPoints = Math.max(0L, projectedRemainingPoints - ledgerBalance);
        List<String> warnings = new ArrayList<>();
        if (missingLotCount > 0) {
            warnings.add("MISSING_MATERIALIZED_LOTS");
        }
        if (existingLots.size() > positiveEntryCount) {
            warnings.add("POINT_LOT_ROWS_WITHOUT_POSITIVE_LEDGER_ENTRY");
        }
        if (unallocatedDebitPoints > 0) {
            warnings.add("NEGATIVE_BALANCE_HAS_UNALLOCATED_DEBITS");
        }
        if (positiveEntryCount == 0 && ledgerBalance != 0L) {
            warnings.add("LEDGER_HAS_BALANCE_WITHOUT_POSITIVE_LOTS");
        }
        return new PointLotBackfillAccountResultDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                ledgerBalance,
                projectedRemainingPoints,
                projectedExpiredPoints,
                unallocatedDebitPoints,
                positiveEntryCount,
                debitEntryCount,
                existingLots.size(),
                missingLotCount,
                resetLotCount,
                warnings);
    }

    private List<BackfillLot> projectBackfillLots(List<LoyaltyPointsEntry> entries) {
        List<BackfillLot> activeLots = new ArrayList<>();
        for (LoyaltyPointsEntry entry : entries) {
            if (entry.getPointsDelta() > 0) {
                if ("REVERSE".equals(entry.getEntryType()) && restoreProjectedLotAllocations(entry, activeLots)) {
                    continue;
                }
                activeLots.add(new BackfillLot(entry));
                continue;
            }
            if (entry.getPointsDelta() >= 0) {
                continue;
            }
            long debit = Math.abs(entry.getPointsDelta());
            activeLots.sort(backfillLotComparator());
            for (BackfillLot lot : activeLots) {
                if (debit == 0) {
                    break;
                }
                long consumed = Math.min(debit, lot.remainingPoints);
                lot.remainingPoints -= consumed;
                debit -= consumed;
            }
        }
        return activeLots;
    }

    private boolean restoreProjectedLotAllocations(LoyaltyPointsEntry entry, List<BackfillLot> activeLots) {
        List<BackfillAllocation> allocations = backfillAllocations(entry);
        if (allocations.isEmpty()) {
            return false;
        }
        long remainingRestore = entry.getPointsDelta();
        for (BackfillAllocation allocation : allocations) {
            BackfillLot target = activeLots.stream()
                    .filter(lot -> lot.entry.getId().equals(allocation.sourceEntryId()))
                    .findFirst()
                    .orElse(null);
            if (target == null) {
                return false;
            }
            long restored = Math.min(allocation.points(), target.originalPoints - target.remainingPoints);
            if (restored <= 0) {
                return false;
            }
            target.remainingPoints += restored;
            remainingRestore -= restored;
            if (remainingRestore == 0) {
                return true;
            }
        }
        return remainingRestore == 0;
    }

    private List<BackfillAllocation> backfillAllocations(LoyaltyPointsEntry entry) {
        Object raw = readMap(entry.getMetadataJson()).get(LOT_ALLOCATIONS_METADATA_KEY);
        if (!(raw instanceof List<?> rows)) {
            return List.of();
        }
        List<BackfillAllocation> allocations = new ArrayList<>();
        for (Object row : rows) {
            if (!(row instanceof Map<?, ?> map)) {
                continue;
            }
            UUID sourceEntryId = uuidValue(map.get("sourceEntryId"));
            long points = longValue(map.get("points"));
            if (sourceEntryId != null && points > 0) {
                allocations.add(new BackfillAllocation(sourceEntryId, points));
            }
        }
        return allocations;
    }

    private Comparator<BackfillLot> backfillLotComparator() {
        return Comparator
                .comparing((BackfillLot lot) -> lot.entry.getExpiresAt() == null ? NO_EXPIRY : lot.entry.getExpiresAt())
                .thenComparing(lot -> lot.entry.getOccurredAt())
                .thenComparing(lot -> lot.entry.getCreatedAt());
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, MAP_TYPE);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of("raw", json);
        }
    }

    private List<String> readStringList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<String> result = objectMapper.readValue(json, STRING_LIST);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }

    private String financeCloseoutResultHash(
            String tenantId,
            String applicationId,
            String programId,
            Instant from,
            Instant to,
            LoyaltyFinanceCloseoutTotalsDto totals) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("operation", "LOYALTY_FINANCE_CLOSEOUT");
        payload.put("tenantId", tenantId);
        payload.put("applicationId", applicationId);
        payload.put("programId", programId == null ? "" : programId);
        payload.put("from", from.toString());
        payload.put("to", to.toString());
        payload.put("earnedPoints", totals.earnedPoints());
        payload.put("burnedPoints", totals.burnedPoints());
        payload.put("reversedPoints", totals.reversedPoints());
        payload.put("adjustedPoints", totals.adjustedPoints());
        payload.put("expiredPoints", totals.expiredPoints());
        payload.put("netPoints", totals.netPoints());
        payload.put("entryCount", totals.entryCount());
        payload.put("pendingOutboxCount", totals.pendingOutboxCount());
        payload.put("missingOutboxCount", totals.missingOutboxCount());
        return sha256Hex(toJson(payload));
    }

    private CloseoutCursor closeoutCursor(Optional<String> cursor) {
        String token = blankToNull(cursor.orElse(null));
        if (token == null) {
            return null;
        }
        try {
            String decoded = new String(Base64.getUrlDecoder().decode(token), StandardCharsets.UTF_8);
            Map<String, Object> payload = readMap(decoded);
            long version = longValue(payload.get("version"));
            long page = longValue(payload.get("page"));
            long limit = longValue(payload.get("limit"));
            if (!payload.containsKey("version")
                    || !payload.containsKey("page")
                    || !payload.containsKey("limit")
                    || version != 1L
                    || page < 0
                    || page > Integer.MAX_VALUE
                    || limit < 1
                    || limit > 5000) {
                throw invalidCloseoutCursor();
            }
            return new CloseoutCursor((int) page, (int) limit);
        } catch (IllegalArgumentException ex) {
            throw invalidCloseoutCursor();
        }
    }

    private String encodeCloseoutCursor(int page, int limit) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("version", 1);
        payload.put("page", page);
        payload.put("limit", limit);
        return Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(toJson(payload).getBytes(StandardCharsets.UTF_8));
    }

    private BadRequestException invalidCloseoutCursor() {
        return BadRequestException.coded(
                LOYALTY_INVALID_RECONCILIATION_QUERY,
                "Invalid finance closeout cursor");
    }

    private String pointLotBackfillResultHash(
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            UUID accountId,
            int limit,
            List<PointLotBackfillAccountResultDto> items) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("operation", "POINT_LOT_BACKFILL");
        payload.put("tenantId", tenantId);
        payload.put("applicationId", applicationId);
        payload.put("programId", programId == null ? "" : programId);
        payload.put("profileId", profileId == null ? "" : profileId);
        payload.put("accountId", accountId == null ? "" : accountId.toString());
        payload.put("limit", limit);
        payload.put("items", items.stream()
                .sorted(Comparator.comparing(item -> item.accountId().toString()))
                .map(item -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("accountId", item.accountId().toString());
                    row.put("ledgerBalance", item.ledgerBalance());
                    row.put("projectedRemainingPoints", item.projectedRemainingPoints());
                    row.put("projectedExpiredPoints", item.projectedExpiredPoints());
                    row.put("unallocatedDebitPoints", item.unallocatedDebitPoints());
                    row.put("positiveEntryCount", item.positiveEntryCount());
                    row.put("debitEntryCount", item.debitEntryCount());
                    row.put("existingLotCount", item.existingLotCount());
                    row.put("missingLotCount", item.missingLotCount());
                    row.put("resetLotCount", item.resetLotCount());
                    row.put("warnings", item.warnings());
                    return row;
                })
                .toList());
        return sha256Hex(toJson(payload));
    }

    private String sha256Hex(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is required", ex);
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Unable to serialize loyalty admin audit payload", ex);
        }
    }

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 200));
    }

    private String readinessOperation(Optional<String> operation) {
        String value = blankToNull(operation.orElse(null));
        String normalized = value == null ? "earn" : value.toLowerCase(Locale.ROOT);
        if (!List.of("admin", "read", "earn", "burn", "reverse", "adjust", "expire").contains(normalized)) {
            throw BadRequestException.coded(
                    LOYALTY_INVALID_READINESS_QUERY,
                    "Unsupported loyalty readiness operation: " + value);
        }
        return normalized;
    }

    private String normalizeEntryType(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? null : normalized.toUpperCase();
    }

    private String normalizedStatus(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? null : normalized.toUpperCase();
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private UUID uuidValue(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(String.valueOf(value));
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value == null || String.valueOf(value).isBlank()) {
            return 0L;
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return 0L;
        }
    }

    private record BucketProjection(List<PointLot> lots, long unallocatedDebitPoints) {
    }

    private record CloseoutCursor(int page, int limit) {
    }

    private record BackfillAllocation(UUID sourceEntryId, long points) {
    }

    private static final class PointLot {
        private final LoyaltyPointsEntry entry;
        private final long originalPoints;
        private long remainingPoints;

        private PointLot(LoyaltyPointsEntry entry, long originalPoints) {
            this.entry = entry;
            this.originalPoints = originalPoints;
            this.remainingPoints = originalPoints;
        }
    }

    private static final class BackfillLot {
        private final LoyaltyPointsEntry entry;
        private final long originalPoints;
        private long remainingPoints;

        private BackfillLot(LoyaltyPointsEntry entry) {
            this.entry = entry;
            this.originalPoints = entry.getPointsDelta();
            this.remainingPoints = entry.getPointsDelta();
        }
    }
}
