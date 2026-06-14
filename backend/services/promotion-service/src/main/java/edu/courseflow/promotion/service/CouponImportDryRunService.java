package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_ACQUIRE_FAILED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_NOT_REPLAYABLE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_REUSED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunIssueDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRowDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportRow;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CouponImportDryRunService {

    private static final int DEFAULT_MAX_ROWS = 5_000;
    private static final int HARD_MAX_ROWS = 10_000;
    private static final int MAX_BYTES = 10 * 1024 * 1024;
    private static final int MAX_ISSUES = 200;
    private static final int MAX_SAMPLE_ROWS = 100;
    private static final int LOOKUP_CHUNK_SIZE = 500;
    private static final Duration IDEMPOTENCY_TTL = Duration.ofDays(7);
    private static final String DRY_RUN_OPERATION = "COUPON_IMPORT_DRY_RUN";
    private static final List<String> STORAGE_FORMAT_ORDER = List.of(
            "current_hmac",
            "previous_hmac",
            "legacy_sha",
            "legacy_raw",
            "malformed");
    private static final Set<String> STANDARD_HEADERS = Set.of(
            "code",
            "holderprofileid",
            "startsat",
            "expiresat",
            "maxredemptions",
            "maxredemptionsperprofile");

    private final IncentiveCampaignRepository campaigns;
    private final IncentiveCouponRepository coupons;
    private final IncentiveCouponImportBatchRepository importBatches;
    private final IncentiveCouponImportRowRepository importRows;
    private final IncentiveIdempotencyKeyRepository idempotencyKeys;
    private final IncentiveAuditEventRepository auditEvents;
    private final IncentiveAccessService access;
    private final CouponCodeFingerprintService couponFingerprints;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final IncentiveMetrics metrics;
    private final ObjectMapper objectMapper;
    private final boolean cleanupEnabled;
    private final int dryRunTtlDays;

    public CouponImportDryRunService(IncentiveCampaignRepository campaigns,
                                     IncentiveCouponRepository coupons,
                                     IncentiveCouponImportBatchRepository importBatches,
                                     IncentiveCouponImportRowRepository importRows,
                                     IncentiveIdempotencyKeyRepository idempotencyKeys,
                                     IncentiveAuditEventRepository auditEvents,
                                     IncentiveAccessService access,
                                     CouponCodeFingerprintService couponFingerprints,
                                     AdminOperationRateGuard adminOperationRateGuard,
                                     IncentiveMetrics metrics,
                                     ObjectMapper objectMapper,
                                     @Value("${courseflow.promotion.coupon.import-dry-run.cleanup-enabled:true}")
                                     boolean cleanupEnabled,
                                     @Value("${courseflow.promotion.coupon.import-dry-run.ttl-days:30}")
                                     int dryRunTtlDays) {
        this.campaigns = campaigns;
        this.coupons = coupons;
        this.importBatches = importBatches;
        this.importRows = importRows;
        this.idempotencyKeys = idempotencyKeys;
        this.auditEvents = auditEvents;
        this.access = access;
        this.couponFingerprints = couponFingerprints;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.metrics = metrics;
        this.objectMapper = objectMapper;
        this.cleanupEnabled = cleanupEnabled;
        this.dryRunTtlDays = Math.max(1, dryRunTtlDays);
    }

    @Transactional
    public CouponImportDryRunResponseDto dryRun(CouponImportDryRunRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        long startedNanos = System.nanoTime();
        try {
            return dryRunInternal(request, user, correlationId, startedNanos);
        } catch (RuntimeException ex) {
            metrics.couponImportDryRun("error", 0, elapsed(startedNanos));
            throw ex;
        }
    }

    private CouponImportDryRunResponseDto dryRunInternal(CouponImportDryRunRequestDto request,
                                                         CurrentUser user,
                                                         String correlationId,
                                                         long startedNanos) {
        if (request == null) {
            throw new BadRequestException("Coupon import dry-run request is required");
        }
        IncentiveCampaign campaign = campaigns.findById(request.campaignId())
                .orElseThrow(() -> new NotFoundException("Campaign not found: " + request.campaignId()));
        access.requireCouponImportManageAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        String sourceClientId = access.sourceClientId(user);
        String contentHash = contentHash(request.csvContent());
        adminOperationRateGuard.requireAllowed(
                "coupon_import_dry_run",
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                user,
                sourceClientId,
                contentHash);
        String requestHash = requestHash(campaign.getId(), contentHash, request);
        IdempotencySlot idempotency = acquireIdempotency(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                normalizeIdempotencyKey(request.idempotencyKey()),
                requestHash);
        if (idempotency.replay() != null) {
            metrics.couponImportDryRun("replay", idempotency.replay().requestedRows(), elapsed(startedNanos));
            return idempotency.replay();
        }

        List<RowDraft> rows = parseCsv(request);
        Map<String, ExistingCodeMatch> existingCodes = existingCodes(campaign.getId(), rows);
        applyDuplicateRules(rows, existingCodes);

        StorageReadiness storageReadiness = storageReadiness(campaign);
        Instant generatedAt = Instant.now();
        UUID dryRunId = UUID.randomUUID();
        List<CouponImportDryRunIssueDto> issues = rows.stream()
                .flatMap(row -> row.issues.stream())
                .limit(MAX_ISSUES)
                .toList();
        List<String> warnings = warnings(rows, issues, storageReadiness);
        List<CouponImportDryRunRowDto> sampleRows = rows.stream()
                .limit(MAX_SAMPLE_ROWS)
                .map(row -> new CouponImportDryRunRowDto(
                        row.rowNumber,
                        row.codeMask,
                        row.issues.isEmpty() ? "VALID" : "INVALID",
                        row.issues.stream().map(CouponImportDryRunIssueDto::reasonCode).distinct().toList()))
                .toList();

        long duplicateInFileRows = rows.stream().filter(row -> row.hasIssue("DUPLICATE_IN_FILE")).count();
        long duplicateExistingRows = rows.stream().filter(row -> row.hasIssue("DUPLICATE_EXISTING")).count();
        long invalidRows = rows.stream().filter(RowDraft::hasIssues).count();
        boolean storageReady = storageReadiness.ready();
        boolean commitReady = !rows.isEmpty() && invalidRows == 0 && storageReady;
        String resultHash = resultHash(campaign.getId(), contentHash, requestHash, rows, storageReadiness);
        CouponImportDryRunResponseDto response = new CouponImportDryRunResponseDto(
                dryRunId,
                campaign.getId(),
                true,
                rows.size(),
                Math.toIntExact(rows.size() - invalidRows),
                Math.toIntExact(invalidRows),
                Math.toIntExact(duplicateInFileRows),
                Math.toIntExact(duplicateExistingRows),
                storageReady,
                commitReady,
                resultHash,
                generatedAt,
                warnings,
                issues,
                sampleRows);

        AuditMetadata auditMetadata = new AuditMetadata(correlationId, sourceClientId);
        importBatches.save(new IncentiveCouponImportBatch(
                dryRunId,
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                requestHash,
                normalizeIdempotencyKey(request.idempotencyKey()),
                contentHash,
                resultHash,
                response.requestedRows(),
                response.validRows(),
                response.invalidRows(),
                response.duplicateInFileRows(),
                response.duplicateExistingRows(),
                response.storageInventoryReady(),
                response.commitReady(),
                toJson(response),
                actorId(user),
                auditMetadata.correlationId(),
                auditMetadata.sourceClientId(),
                generatedAt.plus(Duration.ofDays(dryRunTtlDays))));
        importRows.saveAll(rows.stream()
                .map(row -> new IncentiveCouponImportRow(
                        dryRunId,
                        row.rowNumber,
                        row.codeMask,
                        row.issues.isEmpty() ? "VALID" : "INVALID",
                        toJson(row.issues.stream()
                                .map(CouponImportDryRunIssueDto::reasonCode)
                                .distinct()
                                .toList()),
                        toJson(row.issues)))
                .toList());
        auditEvents.save(new IncentiveAuditEvent(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                dryRunId.toString(),
                "coupon-import-dry-run",
                "coupon.import_dry_run_created",
                actorId(user),
                null,
                toJson(Map.of(
                        "campaignId", campaign.getId().toString(),
                        "requestedRows", response.requestedRows(),
                        "validRows", response.validRows(),
                        "invalidRows", response.invalidRows(),
                        "duplicateInFileRows", response.duplicateInFileRows(),
                        "duplicateExistingRows", response.duplicateExistingRows(),
                        "storageInventoryReady", response.storageInventoryReady(),
                        "commitReady", response.commitReady(),
                        "resultHash", response.resultHash())),
                auditMetadata.correlationId(),
                auditMetadata.sourceClientId()));
        completeIdempotency(idempotency.key(), response);
        metrics.couponImportDryRun(response.commitReady() ? "commit_ready" : "completed",
                response.requestedRows(),
                elapsed(startedNanos));
        return response;
    }

    @Transactional(readOnly = true)
    public CouponImportDryRunResponseDto dryRun(UUID dryRunId, CurrentUser user) {
        IncentiveCouponImportBatch batch = importBatches.findById(dryRunId)
                .orElseThrow(() -> new NotFoundException("Coupon import dry-run not found: " + dryRunId));
        access.requireCouponImportReadAccess(batch.getTenantId(), batch.getApplicationId(), user);
        try {
            return objectMapper.readValue(batch.getResultJson(), CouponImportDryRunResponseDto.class);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to deserialize coupon import dry-run result", ex);
        }
    }

    DryRunEvaluation evaluateForCommit(CouponImportDryRunRequestDto request, CurrentUser user) {
        if (request == null) {
            throw new BadRequestException("Coupon import dry-run request is required");
        }
        String contentHash = contentHash(request.csvContent());
        IncentiveCampaign campaign = campaigns.findById(request.campaignId())
                .orElseThrow(() -> new NotFoundException("Campaign not found: " + request.campaignId()));
        access.requireCouponImportManageAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        String requestHash = requestHash(campaign.getId(), contentHash, request);
        List<RowDraft> rows = parseCsv(request);
        Map<String, ExistingCodeMatch> existingCodes = existingCodes(campaign.getId(), rows);
        applyDuplicateRules(rows, existingCodes);
        StorageReadiness storageReadiness = storageReadiness(campaign);
        long duplicateInFileRows = rows.stream().filter(row -> row.hasIssue("DUPLICATE_IN_FILE")).count();
        long duplicateExistingRows = rows.stream().filter(row -> row.hasIssue("DUPLICATE_EXISTING")).count();
        long invalidRows = rows.stream().filter(RowDraft::hasIssues).count();
        boolean commitReady = !rows.isEmpty() && invalidRows == 0 && storageReadiness.ready();
        String resultHash = resultHash(campaign.getId(), contentHash, requestHash, rows, storageReadiness);
        return new DryRunEvaluation(
                campaign,
                rows,
                contentHash,
                requestHash,
                resultHash,
                rows.size(),
                Math.toIntExact(rows.size() - invalidRows),
                Math.toIntExact(invalidRows),
                Math.toIntExact(duplicateInFileRows),
                Math.toIntExact(duplicateExistingRows),
                storageReadiness.ready(),
                commitReady);
    }

    CouponImportDryRunRequestDto commitDryRunRequest(edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto request) {
        return new CouponImportDryRunRequestDto(
                request.campaignId(),
                request.csvContent(),
                request.maxRows(),
                request.holderProfileId(),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                request.metadata(),
                null);
    }

    @Scheduled(fixedDelayString = "${courseflow.promotion.coupon.import-dry-run.cleanup-fixed-delay-ms:3600000}")
    @Transactional
    public void purgeExpiredDryRuns() {
        if (!cleanupEnabled) {
            return;
        }
        long startedNanos = System.nanoTime();
        try {
            int deleted = importBatches.deleteExpiredUncommitted(Instant.now());
            metrics.couponImportDryRunCleanup("success", deleted, elapsed(startedNanos));
        } catch (RuntimeException ex) {
            metrics.couponImportDryRunCleanup("error", 0, elapsed(startedNanos));
            throw ex;
        }
    }

    private IdempotencySlot acquireIdempotency(String tenantId,
                                               String applicationId,
                                               String idempotencyKey,
                                               String requestHash) {
        if (idempotencyKey == null) {
            return new IdempotencySlot(null, null);
        }
        Instant expiresAt = Instant.now().plus(IDEMPOTENCY_TTL);
        idempotencyKeys.insertInProgressIfAbsent(
                UUID.randomUUID(),
                tenantId,
                applicationId,
                DRY_RUN_OPERATION,
                idempotencyKey,
                requestHash,
                expiresAt);
        Optional<IncentiveIdempotencyKey> lockedKey = idempotencyKeys.lockByScope(
                tenantId,
                applicationId,
                DRY_RUN_OPERATION,
                idempotencyKey);
        if (lockedKey.isEmpty()) {
            metrics.idempotency(DRY_RUN_OPERATION, "acquire_failed");
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_ACQUIRE_FAILED,
                    "Could not acquire idempotency key");
        }
        IncentiveIdempotencyKey key = lockedKey.get();
        if (!key.getRequestHash().equals(requestHash)) {
            metrics.idempotency(DRY_RUN_OPERATION, "payload_conflict");
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_REUSED,
                    "Idempotency key was reused with a different payload");
        }
        if (key.expired(Instant.now())) {
            metrics.idempotency(DRY_RUN_OPERATION, "expired");
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_EXPIRED,
                    "Idempotency key has expired; use a new key");
        }
        if (key.succeeded()) {
            metrics.idempotency(DRY_RUN_OPERATION, "replay");
            return new IdempotencySlot(key, readResponse(key.getResponseJson()));
        }
        if (!key.inProgress()) {
            metrics.idempotency(DRY_RUN_OPERATION, "not_replayable");
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_NOT_REPLAYABLE,
                    "Idempotency key is not replayable");
        }
        metrics.idempotency(DRY_RUN_OPERATION, "acquired");
        return new IdempotencySlot(key, null);
    }

    private void completeIdempotency(IncentiveIdempotencyKey key, CouponImportDryRunResponseDto response) {
        if (key == null) {
            return;
        }
        key.complete(toJson(response), Instant.now().plus(IDEMPOTENCY_TTL));
        idempotencyKeys.save(key);
    }

    private CouponImportDryRunResponseDto readResponse(String responseJson) {
        try {
            return objectMapper.readValue(responseJson, CouponImportDryRunResponseDto.class);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to deserialize coupon import dry-run idempotency response", ex);
        }
    }

    private List<RowDraft> parseCsv(CouponImportDryRunRequestDto request) {
        String csv = request.csvContent() == null ? "" : stripBom(request.csvContent());
        if (csv.isBlank()) {
            throw new BadRequestException("Coupon CSV content is required");
        }
        if (csv.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES) {
            throw new BadRequestException("Coupon CSV content must be at most 10MB");
        }
        int maxRows = maxRows(request.maxRows());
        try (CSVParser parser = CSVFormat.DEFAULT.builder()
                .setHeader()
                .setSkipHeaderRecord(true)
                .setIgnoreEmptyLines(true)
                .setTrim(true)
                .build()
                .parse(new StringReader(csv))) {
            Map<String, String> headers = canonicalHeaders(parser);
            if (!headers.containsKey("code")) {
                throw new BadRequestException("Coupon CSV must contain a code header");
            }
            List<RowDraft> rows = new ArrayList<>();
            for (CSVRecord record : parser) {
                if (rows.size() >= maxRows) {
                    throw new BadRequestException("Coupon CSV row count exceeds maxRows: " + maxRows);
                }
                RowDraft row = rowDraft(record, headers, request);
                rows.add(row);
            }
            if (rows.isEmpty()) {
                throw new BadRequestException("Coupon CSV must contain at least one data row");
            }
            return rows;
        } catch (IllegalArgumentException | IOException ex) {
            throw new BadRequestException("Invalid coupon CSV content: " + ex.getMessage());
        }
    }

    private RowDraft rowDraft(CSVRecord record,
                              Map<String, String> headers,
                              CouponImportDryRunRequestDto request) {
        int rowNumber = Math.toIntExact(record.getRecordNumber() + 1);
        String rawCode = value(record, headers, "code");
        String normalizedCode = CouponCodeNormalizer.normalize(rawCode);
        String codeMask = normalizedCode.isBlank() ? null : CouponCodeNormalizer.mask(normalizedCode);
        RowDraft row = new RowDraft(rowNumber, normalizedCode, codeMask);
        if (normalizedCode.isBlank()) {
            row.issue("code", "CODE_REQUIRED", "Coupon code is required");
        } else if (normalizedCode.length() > 128) {
            row.issue("code", "CODE_TOO_LONG", "Coupon code must be at most 128 normalized characters");
        }

        String holderProfileId = firstNonBlank(value(record, headers, "holderprofileid"), request.holderProfileId());
        if (holderProfileId != null && holderProfileId.length() > 120) {
            row.issue("holderProfileId", "HOLDER_PROFILE_TOO_LONG",
                    "holderProfileId must be at most 120 characters");
        }
        Instant startsAt = parseInstant(row, "startsAt", firstNonBlank(value(record, headers, "startsat"),
                request.startsAt() == null ? null : request.startsAt().toString()));
        Instant expiresAt = parseInstant(row, "expiresAt", firstNonBlank(value(record, headers, "expiresat"),
                request.expiresAt() == null ? null : request.expiresAt().toString()));
        Integer maxRedemptions = parseInteger(row, "maxRedemptions",
                firstNonBlank(value(record, headers, "maxredemptions"),
                        request.maxRedemptions() == null ? null : request.maxRedemptions().toString()));
        Integer maxRedemptionsPerProfile = parseInteger(row, "maxRedemptionsPerProfile",
                firstNonBlank(value(record, headers, "maxredemptionsperprofile"),
                        request.maxRedemptionsPerProfile() == null ? null : request.maxRedemptionsPerProfile().toString()));
        try {
            CouponValidationSupport.validateWindowAndLimits(
                    startsAt,
                    expiresAt,
                    maxRedemptions,
                    maxRedemptionsPerProfile);
        } catch (BadRequestException ex) {
            row.issue("limits", "INVALID_WINDOW_OR_LIMIT", ex.getMessage());
        }

        Map<String, Object> metadata = new LinkedHashMap<>();
        if (request.metadata() != null) {
            metadata.putAll(request.metadata());
        }
        for (String header : headers.values()) {
            String canonical = canonical(header);
            if (!STANDARD_HEADERS.contains(canonical)) {
                String metadataKey = metadataKey(header);
                String metadataValue = blankToNull(record.get(header));
                if (metadataKey != null && metadataValue != null) {
                    metadata.put(metadataKey, metadataValue);
                }
            }
        }
        row.holderProfileId = holderProfileId;
        row.startsAt = startsAt;
        row.expiresAt = expiresAt;
        row.maxRedemptions = maxRedemptions;
        row.maxRedemptionsPerProfile = maxRedemptionsPerProfile;
        row.metadata = metadata;
        return row;
    }

    private Map<String, ExistingCodeMatch> existingCodes(UUID campaignId, List<RowDraft> rows) {
        Map<String, ExistingCodeMatch> matchesByNormalizedCode = new HashMap<>();
        Map<String, List<String>> fingerprintsByNormalizedCode = new HashMap<>();
        Set<String> lookupFingerprints = new LinkedHashSet<>();
        for (RowDraft row : rows) {
            if (row.normalizedCode == null || row.normalizedCode.isBlank()) {
                continue;
            }
            List<String> fingerprints = couponFingerprints.lookupFingerprints(row.normalizedCode);
            fingerprintsByNormalizedCode.put(row.normalizedCode, fingerprints);
            lookupFingerprints.addAll(fingerprints);
        }
        Set<String> existingFingerprints = new HashSet<>();
        List<String> lookupList = List.copyOf(lookupFingerprints);
        for (int start = 0; start < lookupList.size(); start += LOOKUP_CHUNK_SIZE) {
            List<String> chunk = lookupList.subList(start, Math.min(start + LOOKUP_CHUNK_SIZE, lookupList.size()));
            coupons.findByCampaignIdAndNormalizedCodeIn(campaignId, chunk)
                    .stream()
                    .map(IncentiveCoupon::getNormalizedCode)
                    .forEach(existingFingerprints::add);
        }
        for (Map.Entry<String, List<String>> entry : fingerprintsByNormalizedCode.entrySet()) {
            entry.getValue().stream()
                    .filter(existingFingerprints::contains)
                    .findFirst()
                    .ifPresent(fingerprint -> matchesByNormalizedCode.put(
                            entry.getKey(),
                            new ExistingCodeMatch(fingerprint)));
        }
        return matchesByNormalizedCode;
    }

    private void applyDuplicateRules(List<RowDraft> rows, Map<String, ExistingCodeMatch> existingCodes) {
        Set<String> seenCodes = new HashSet<>();
        for (RowDraft row : rows) {
            if (row.normalizedCode == null || row.normalizedCode.isBlank()) {
                continue;
            }
            if (!seenCodes.add(row.normalizedCode)) {
                row.issue("code", "DUPLICATE_IN_FILE", "Coupon code is duplicated in the CSV file");
            }
            if (existingCodes.containsKey(row.normalizedCode)) {
                row.issue("code", "DUPLICATE_EXISTING", "Coupon code already exists for campaign");
            }
        }
    }

    private StorageReadiness storageReadiness(IncentiveCampaign campaign) {
        Map<String, Long> counts = new LinkedHashMap<>();
        STORAGE_FORMAT_ORDER.forEach(storageFormat -> counts.put(storageFormat, 0L));
        coupons.countByStorageFormat(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                true,
                couponFingerprints.currentStoragePrefix()).forEach(row ->
                counts.merge(row.getStorageFormat(), row.getCouponCount(), Long::sum));
        long legacy = counts.get("legacy_sha") + counts.get("legacy_raw");
        long malformed = counts.get("malformed");
        return new StorageReadiness(legacy == 0 && malformed == 0, legacy, malformed);
    }

    private List<String> warnings(List<RowDraft> rows,
                                  List<CouponImportDryRunIssueDto> visibleIssues,
                                  StorageReadiness storageReadiness) {
        List<String> warnings = new ArrayList<>();
        long totalIssues = rows.stream().mapToLong(row -> row.issues.size()).sum();
        if (totalIssues > visibleIssues.size()) {
            warnings.add("ISSUES_TRUNCATED");
        }
        if (rows.size() > MAX_SAMPLE_ROWS) {
            warnings.add("SAMPLE_ROWS_TRUNCATED");
        }
        if (!storageReadiness.ready()) {
            warnings.add("COUPON_STORAGE_MIGRATION_NOT_READY");
        }
        return warnings;
    }

    private String requestHash(UUID campaignId, String contentHash, CouponImportDryRunRequestDto request) {
        LinkedHashMap<String, Object> identity = new LinkedHashMap<>();
        identity.put("operation", DRY_RUN_OPERATION);
        identity.put("campaignId", campaignId.toString());
        identity.put("contentHash", contentHash);
        identity.put("maxRows", maxRows(request.maxRows()));
        identity.put("holderProfileId", blankToNull(request.holderProfileId()));
        identity.put("startsAt", request.startsAt() == null ? null : request.startsAt().toString());
        identity.put("expiresAt", request.expiresAt() == null ? null : request.expiresAt().toString());
        identity.put("maxRedemptions", request.maxRedemptions());
        identity.put("maxRedemptionsPerProfile", request.maxRedemptionsPerProfile());
        identity.put("metadata", sortedMetadata(request.metadata()));
        return hash(identity);
    }

    private String resultHash(UUID campaignId,
                              String contentHash,
                              String requestHash,
                              List<RowDraft> rows,
                              StorageReadiness storageReadiness) {
        List<Map<String, Object>> safeRows = rows.stream()
                .map(row -> {
                    Map<String, Object> rowIdentity = new LinkedHashMap<>();
                    rowIdentity.put("rowNumber", row.rowNumber);
                    rowIdentity.put("codeIdentityHash", hashText(row.normalizedCode == null ? "" : row.normalizedCode));
                    rowIdentity.put("issueCodes", row.issues.stream()
                            .map(CouponImportDryRunIssueDto::reasonCode)
                            .distinct()
                            .toList());
                    return rowIdentity;
                })
                .toList();
        LinkedHashMap<String, Object> identity = new LinkedHashMap<>();
        identity.put("operation", DRY_RUN_OPERATION);
        identity.put("campaignId", campaignId.toString());
        identity.put("contentHash", contentHash);
        identity.put("requestHash", requestHash);
        identity.put("rows", safeRows);
        identity.put("storageInventoryReady", storageReadiness.ready());
        identity.put("legacyCoupons", storageReadiness.legacyCoupons());
        identity.put("malformedCoupons", storageReadiness.malformedCoupons());
        return hash(identity);
    }

    private Map<String, String> canonicalHeaders(CSVParser parser) {
        Map<String, String> headers = new LinkedHashMap<>();
        for (String header : parser.getHeaderMap().keySet()) {
            String canonical = canonical(header);
            if (canonical.isBlank()) {
                throw new BadRequestException("Coupon CSV contains a blank header");
            }
            if (headers.putIfAbsent(canonical, header) != null) {
                throw new BadRequestException("Coupon CSV contains a duplicate header: " + header);
            }
        }
        return headers;
    }

    private Instant parseInstant(RowDraft row, String field, String value) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            return null;
        }
        try {
            return Instant.parse(normalized);
        } catch (DateTimeParseException ex) {
            row.issue(field, "INVALID_DATE_TIME", field + " must be an ISO-8601 instant");
            return null;
        }
    }

    private Integer parseInteger(RowDraft row, String field, String value) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            return null;
        }
        try {
            return Integer.parseInt(normalized);
        } catch (NumberFormatException ex) {
            row.issue(field, "INVALID_INTEGER", field + " must be an integer");
            return null;
        }
    }

    private String value(CSVRecord record, Map<String, String> headers, String canonicalHeader) {
        String header = headers.get(canonicalHeader);
        return header == null ? null : record.get(header);
    }

    private String metadataKey(String header) {
        String trimmed = blankToNull(header);
        if (trimmed == null) {
            return null;
        }
        if (trimmed.regionMatches(true, 0, "metadata.", 0, "metadata.".length())) {
            trimmed = trimmed.substring("metadata.".length());
        }
        return blankToNull(trimmed);
    }

    private String firstNonBlank(String first, String second) {
        String normalized = blankToNull(first);
        return normalized == null ? blankToNull(second) : normalized;
    }

    private int maxRows(Integer requestedMaxRows) {
        return Math.max(1, Math.min(requestedMaxRows == null ? DEFAULT_MAX_ROWS : requestedMaxRows,
                HARD_MAX_ROWS));
    }

    private Map<String, Object> sortedMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> sorted = new TreeMap<>();
        metadata.forEach((key, value) -> {
            if (key != null && value != null) {
                sorted.put(key, value);
            }
        });
        return sorted;
    }

    private String stripBom(String value) {
        return value.startsWith("\uFEFF") ? value.substring(1) : value;
    }

    private String canonical(String header) {
        if (header == null) {
            return "";
        }
        return header.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private String normalizeIdempotencyKey(String value) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            return null;
        }
        if (normalized.length() > 160) {
            throw new BadRequestException("idempotencyKey must be at most 160 characters");
        }
        return normalized;
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private String hash(Object value) {
        try {
            return couponFingerprints.integrityHash("coupon-import-identity", toJson(value));
        } catch (RuntimeException ex) {
            throw new IllegalStateException("Unable to hash coupon import dry-run", ex);
        }
    }

    private String hashText(String value) {
        return couponFingerprints.integrityHash("coupon-import-row-code", value);
    }

    private String contentHash(String csvContent) {
        String normalized = csvContent == null ? "" : stripBom(csvContent);
        return couponFingerprints.integrityHash("coupon-import-content", normalized);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize coupon import dry-run", ex);
        }
    }

    private Duration elapsed(long startedNanos) {
        return Duration.ofNanos(System.nanoTime() - startedNanos);
    }

    static final class RowDraft {
        private final int rowNumber;
        private final String normalizedCode;
        private final String codeMask;
        private final List<CouponImportDryRunIssueDto> issues = new ArrayList<>();
        private String holderProfileId;
        private Instant startsAt;
        private Instant expiresAt;
        private Integer maxRedemptions;
        private Integer maxRedemptionsPerProfile;
        private Map<String, Object> metadata = Map.of();

        private RowDraft(int rowNumber, String normalizedCode, String codeMask) {
            this.rowNumber = rowNumber;
            this.normalizedCode = normalizedCode;
            this.codeMask = codeMask;
        }

        private void issue(String field, String reasonCode, String message) {
            issues.add(new CouponImportDryRunIssueDto(rowNumber, codeMask, field, reasonCode, message));
        }

        private boolean hasIssue(String reasonCode) {
            return issues.stream().anyMatch(issue -> reasonCode.equals(issue.reasonCode()));
        }

        private boolean hasIssues() {
            return !issues.isEmpty();
        }

        int rowNumber() { return rowNumber; }
        String normalizedCode() { return normalizedCode; }
        String codeMask() { return codeMask; }
        String holderProfileId() { return holderProfileId; }
        Instant startsAt() { return startsAt; }
        Instant expiresAt() { return expiresAt; }
        Integer maxRedemptions() { return maxRedemptions; }
        Integer maxRedemptionsPerProfile() { return maxRedemptionsPerProfile; }
        Map<String, Object> metadata() { return metadata; }
    }

    private record ExistingCodeMatch(String fingerprint) {
    }

    private record StorageReadiness(boolean ready, long legacyCoupons, long malformedCoupons) {
    }

    private record IdempotencySlot(IncentiveIdempotencyKey key, CouponImportDryRunResponseDto replay) {
    }

    record DryRunEvaluation(
            IncentiveCampaign campaign,
            List<RowDraft> rows,
            String contentHash,
            String requestHash,
            String resultHash,
            int requestedRows,
            int validRows,
            int invalidRows,
            int duplicateInFileRows,
            int duplicateExistingRows,
            boolean storageInventoryReady,
            boolean commitReady
    ) {
    }
}
