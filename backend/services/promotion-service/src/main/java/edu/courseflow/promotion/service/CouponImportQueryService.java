package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportIssueExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunListItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationQueryResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportOperation;
import edu.courseflow.promotion.model.IncentiveCouponImportRow;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportOperationRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import java.io.IOException;
import java.io.StringWriter;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CouponImportQueryService {

    private static final int DEFAULT_LIMIT = 50;
    private static final int MAX_LIMIT = 200;
    private static final List<String> DRY_RUN_STATUSES = List.of("COMPLETED");
    private static final List<String> OPERATION_STATUSES = List.of(IncentiveCouponImportOperation.STATUS_SUCCEEDED);
    private static final List<String> EXPORT_ROW_STATUSES = List.of("INVALID", "VALID", "ALL");
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };

    private final IncentiveCouponImportBatchRepository batches;
    private final IncentiveCouponImportOperationRepository operations;
    private final IncentiveCouponImportRowRepository rows;
    private final IncentiveAuditEventRepository auditEvents;
    private final IncentiveAccessService access;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final IncentiveMetrics metrics;
    private final ObjectMapper objectMapper;
    private final int issueExportMaxRows;

    public CouponImportQueryService(IncentiveCouponImportBatchRepository batches,
                                    IncentiveCouponImportOperationRepository operations,
                                    IncentiveCouponImportRowRepository rows,
                                    IncentiveAuditEventRepository auditEvents,
                                    IncentiveAccessService access,
                                    AdminOperationRateGuard adminOperationRateGuard,
                                    IncentiveMetrics metrics,
                                    ObjectMapper objectMapper,
                                    @Value("${courseflow.promotion.coupon.import-query.issue-export.max-rows:10000}")
                                    int issueExportMaxRows) {
        this.batches = batches;
        this.operations = operations;
        this.rows = rows;
        this.auditEvents = auditEvents;
        this.access = access;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.metrics = metrics;
        this.objectMapper = objectMapper;
        this.issueExportMaxRows = Math.max(1, issueExportMaxRows);
    }

    @Transactional(readOnly = true)
    public CouponImportDryRunQueryResponseDto dryRuns(Optional<String> tenantId,
                                                      Optional<String> applicationId,
                                                      Optional<UUID> campaignId,
                                                      Optional<String> status,
                                                      Optional<Instant> from,
                                                      Optional<Instant> to,
                                                      Optional<Integer> limit,
                                                      CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            String tenant = requiredText(tenantId, "tenantId");
            String application = requiredText(applicationId, "applicationId");
            access.requireCouponImportReadAccess(tenant, application, user);
            String normalizedStatus = normalizeStatus(status.orElse(null), DRY_RUN_STATUSES, "dry-run");
            int pageSize = boundedLimit(limit.orElse(null));
            List<IncentiveCouponImportBatch> rows = batches.search(
                    tenant,
                    application,
                    campaignId.orElse(null),
                    normalizedStatus,
                    from.orElse(null),
                    to.orElse(null),
                    PageRequest.of(0, pageSize + 1));
            metrics.couponImportQuery("dry_runs", "success", elapsed(startedNanos));
            return new CouponImportDryRunQueryResponseDto(
                    rows.stream().limit(pageSize).map(this::dryRunDto).toList(),
                    pageSize,
                    rows.size() > pageSize,
                    Instant.now());
        } catch (RuntimeException ex) {
            metrics.couponImportQuery("dry_runs", "error", elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional(readOnly = true)
    public CouponImportOperationQueryResponseDto operations(Optional<String> tenantId,
                                                            Optional<String> applicationId,
                                                            Optional<UUID> campaignId,
                                                            Optional<UUID> approvalId,
                                                            Optional<UUID> dryRunId,
                                                            Optional<String> status,
                                                            Optional<Instant> from,
                                                            Optional<Instant> to,
                                                            Optional<Integer> limit,
                                                            CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            String tenant = requiredText(tenantId, "tenantId");
            String application = requiredText(applicationId, "applicationId");
            access.requireCouponImportReadAccess(tenant, application, user);
            String normalizedStatus = normalizeStatus(status.orElse(null), OPERATION_STATUSES, "import operation");
            int pageSize = boundedLimit(limit.orElse(null));
            List<IncentiveCouponImportOperation> rows = operations.search(
                    tenant,
                    application,
                    campaignId.orElse(null),
                    approvalId.orElse(null),
                    dryRunId.orElse(null),
                    normalizedStatus,
                    from.orElse(null),
                    to.orElse(null),
                    PageRequest.of(0, pageSize + 1));
            metrics.couponImportQuery("operations", "success", elapsed(startedNanos));
            return new CouponImportOperationQueryResponseDto(
                    rows.stream().limit(pageSize).map(this::operationDto).toList(),
                    pageSize,
                    rows.size() > pageSize,
                    Instant.now());
        } catch (RuntimeException ex) {
            metrics.couponImportQuery("operations", "error", elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional(readOnly = true)
    public CouponImportOperationDto operation(UUID importId, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            if (importId == null) {
                throw new BadRequestException("importId is required");
            }
            IncentiveCouponImportOperation operation = operations.findById(importId)
                    .orElseThrow(() -> new NotFoundException("Coupon import operation not found: " + importId));
            access.requireCouponImportReadAccess(operation.getTenantId(), operation.getApplicationId(), user);
            metrics.couponImportQuery("operation_detail", "success", elapsed(startedNanos));
            return operationDto(operation);
        } catch (RuntimeException ex) {
            metrics.couponImportQuery("operation_detail", "error", elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public CouponImportOperationExportDto operationExport(UUID importId,
                                                          CurrentUser user,
                                                          String correlationId) {
        long startedNanos = System.nanoTime();
        try {
            if (importId == null) {
                throw new BadRequestException("importId is required");
            }
            IncentiveCouponImportOperation operation = operations.findById(importId)
                    .orElseThrow(() -> new NotFoundException("Coupon import operation not found: " + importId));
            access.requireCouponImportReadAccess(operation.getTenantId(), operation.getApplicationId(), user);
            String sourceClientId = access.sourceClientId(user);
            adminOperationRateGuard.requireAllowed(
                    "coupon_import_operation_export",
                    operation.getTenantId(),
                    operation.getApplicationId(),
                    operation.getCampaignId(),
                    user,
                    sourceClientId,
                    importId.toString());
            String content = operationCsv(operation);
            CouponImportOperationExportDto response = new CouponImportOperationExportDto(
                    operation.getId(),
                    operation.getApprovalId(),
                    operation.getDryRunId(),
                    operation.getCampaignId(),
                    operation.getTenantId(),
                    operation.getApplicationId(),
                    "coupon-import-operation-" + operation.getId() + ".csv",
                    "text/csv",
                    content,
                    Instant.now());
            auditEvents.save(new IncentiveAuditEvent(
                    operation.getTenantId(),
                    operation.getApplicationId(),
                    operation.getId().toString(),
                    "coupon-import-operation",
                    "coupon.import_operation_downloaded",
                    actorId(user),
                    operation.getReason(),
                    toJson(Map.of(
                            "importId", operation.getId().toString(),
                            "approvalId", operation.getApprovalId() == null ? "" : operation.getApprovalId().toString(),
                            "dryRunId", operation.getDryRunId().toString(),
                            "campaignId", operation.getCampaignId().toString(),
                            "status", operation.getStatus(),
                            "requestedRows", operation.getRequestedRows(),
                            "importedRows", operation.getImportedRows(),
                            "changeTicket", operation.getChangeTicket(),
                            "filename", response.filename())),
                    correlationId,
                    sourceClientId));
            metrics.couponImportQuery("operation_export", "success", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.couponImportQuery("operation_export", "error", elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public CouponImportIssueExportDto dryRunIssueExport(UUID dryRunId,
                                                        Optional<String> rowStatus,
                                                        CurrentUser user,
                                                        String correlationId) {
        long startedNanos = System.nanoTime();
        try {
            if (dryRunId == null) {
                throw new BadRequestException("dryRunId is required");
            }
            String normalizedStatus = normalizeExportRowStatus(rowStatus);
            IncentiveCouponImportBatch batch = batches.findById(dryRunId)
                    .orElseThrow(() -> new NotFoundException("Coupon import dry-run not found: " + dryRunId));
            access.requireCouponImportReadAccess(batch.getTenantId(), batch.getApplicationId(), user);
            String sourceClientId = access.sourceClientId(user);
            adminOperationRateGuard.requireAllowed(
                    "coupon_import_issue_export",
                    batch.getTenantId(),
                    batch.getApplicationId(),
                    batch.getCampaignId(),
                    user,
                    sourceClientId,
                    dryRunId.toString() + ":" + normalizedStatus);
            long exportRowCount = issueExportRowCount(dryRunId, normalizedStatus);
            if (exportRowCount > issueExportMaxRows) {
                throw new BadRequestException("EXPORT_TOO_LARGE: coupon import issue export exceeds max rows "
                        + issueExportMaxRows + "; narrow rowStatus or use query history instead");
            }
            List<IncentiveCouponImportRow> exportedRows = "ALL".equals(normalizedStatus)
                    ? rows.findByBatchIdOrderByRowNumber(dryRunId)
                    : rows.findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, normalizedStatus);
            String content = issueCsv(exportedRows);
            CouponImportIssueExportDto response = new CouponImportIssueExportDto(
                    batch.getId(),
                    batch.getCampaignId(),
                    batch.getTenantId(),
                    batch.getApplicationId(),
                    normalizedStatus,
                    exportedRows.size(),
                    "coupon-import-" + batch.getId() + "-" + normalizedStatus.toLowerCase() + ".csv",
                    "text/csv",
                    content,
                    Instant.now());
            auditEvents.save(new IncentiveAuditEvent(
                    batch.getTenantId(),
                    batch.getApplicationId(),
                    batch.getId().toString(),
                    "coupon-import-dry-run",
                    "coupon.import_issue_export_downloaded",
                    actorId(user),
                    null,
                    toJson(Map.of(
                            "dryRunId", batch.getId().toString(),
                            "campaignId", batch.getCampaignId().toString(),
                            "rowStatus", normalizedStatus,
                            "rowCount", exportedRows.size(),
                            "filename", response.filename())),
                    correlationId,
                    sourceClientId));
            metrics.couponImportQuery("issue_export", "success", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.couponImportQuery("issue_export", "error", elapsed(startedNanos));
            throw ex;
        }
    }

    private long issueExportRowCount(UUID dryRunId, String normalizedStatus) {
        return "ALL".equals(normalizedStatus)
                ? rows.countByBatchId(dryRunId)
                : rows.countByBatchIdAndRowStatus(dryRunId, normalizedStatus);
    }

    private CouponImportDryRunListItemDto dryRunDto(IncentiveCouponImportBatch batch) {
        return new CouponImportDryRunListItemDto(
                batch.getId(),
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId(),
                batch.getStatus(),
                batch.getRequestedRows(),
                batch.getValidRows(),
                batch.getInvalidRows(),
                batch.getDuplicateInFileRows(),
                batch.getDuplicateExistingRows(),
                batch.isStorageInventoryReady(),
                batch.isCommitReady(),
                batch.getResultHash(),
                batch.getCreatedBy(),
                batch.getCorrelationId(),
                batch.getSourceClientId(),
                batch.getCreatedAt(),
                batch.getExpiresAt(),
                batch.getCommittedAt(),
                batch.getCommittedBy(),
                batch.getCommittedOperationId(),
                batch.getCommittedRows(),
                batch.getFailureReason());
    }

    private CouponImportOperationDto operationDto(IncentiveCouponImportOperation operation) {
        return new CouponImportOperationDto(
                operation.getId(),
                operation.getApprovalId(),
                operation.getDryRunId(),
                operation.getTenantId(),
                operation.getApplicationId(),
                operation.getCampaignId(),
                operation.getStatus(),
                operation.getRequestedRows(),
                operation.getImportedRows(),
                operation.getResultHash(),
                operation.getReason(),
                operation.getChangeTicket(),
                operation.getCreatedBy(),
                operation.getCorrelationId(),
                operation.getSourceClientId(),
                operation.getCreatedAt());
    }

    private String requiredText(Optional<String> value, String field) {
        String text = value.orElse(null);
        if (text == null || text.isBlank()) {
            throw new BadRequestException(field + " is required");
        }
        return text.trim();
    }

    private String normalizeStatus(String value, List<String> allowed, String label) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String normalized = value.trim().toUpperCase();
        if (!allowed.contains(normalized)) {
            throw new BadRequestException("Unsupported coupon import " + label + " status: " + value);
        }
        return normalized;
    }

    private String normalizeExportRowStatus(Optional<String> rowStatus) {
        String value = rowStatus.orElse(null);
        if (value == null || value.isBlank()) {
            return "INVALID";
        }
        return normalizeStatus(value, EXPORT_ROW_STATUSES, "issue export row");
    }

    private int boundedLimit(Integer requestedLimit) {
        return Math.min(MAX_LIMIT, Math.max(1, requestedLimit == null ? DEFAULT_LIMIT : requestedLimit));
    }

    private String issueCsv(List<IncentiveCouponImportRow> rows) {
        try {
            StringWriter writer = new StringWriter();
            try (CSVPrinter printer = new CSVPrinter(writer, CSVFormat.DEFAULT.builder()
                    .setHeader("rowNumber", "codeMask", "rowStatus", "issueCodes")
                    .build())) {
                for (IncentiveCouponImportRow row : rows) {
                    printer.printRecord(
                            row.getRowNumber(),
                            csvText(row.getCodeMask()),
                            csvText(row.getRowStatus()),
                            csvText(String.join("|", issueCodes(row.getIssueCodesJson()))));
                }
            }
            return writer.toString();
        } catch (IOException ex) {
            throw new IllegalStateException("Unable to write coupon import issue export", ex);
        }
    }

    private String operationCsv(IncentiveCouponImportOperation operation) {
        try {
            StringWriter writer = new StringWriter();
            try (CSVPrinter printer = new CSVPrinter(writer, CSVFormat.DEFAULT.builder()
                    .setHeader(
                            "importId",
                            "approvalId",
                            "dryRunId",
                            "tenantId",
                            "applicationId",
                            "campaignId",
                            "status",
                            "requestedRows",
                            "importedRows",
                            "resultHash",
                            "reason",
                            "changeTicket",
                            "createdBy",
                            "correlationId",
                            "sourceClientId",
                            "createdAt")
                    .build())) {
                printer.printRecord(
                        operation.getId(),
                        operation.getApprovalId(),
                        operation.getDryRunId(),
                        csvText(operation.getTenantId()),
                        csvText(operation.getApplicationId()),
                        operation.getCampaignId(),
                        csvText(operation.getStatus()),
                        operation.getRequestedRows(),
                        operation.getImportedRows(),
                        csvText(operation.getResultHash()),
                        csvText(operation.getReason()),
                        csvText(operation.getChangeTicket()),
                        csvText(operation.getCreatedBy()),
                        csvText(operation.getCorrelationId()),
                        csvText(operation.getSourceClientId()),
                        operation.getCreatedAt());
            }
            return writer.toString();
        } catch (IOException ex) {
            throw new IllegalStateException("Unable to write coupon import operation export", ex);
        }
    }

    private List<String> issueCodes(String issueCodesJson) {
        if (issueCodesJson == null || issueCodesJson.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(issueCodesJson, STRING_LIST);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to read coupon import issue codes", ex);
        }
    }

    private String csvText(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        char first = value.charAt(0);
        if (first == '=' || first == '+' || first == '-' || first == '@' || first == '\t' || first == '\r') {
            return "'" + value;
        }
        return value;
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize coupon import query audit", ex);
        }
    }

    private Duration elapsed(long startedNanos) {
        return Duration.ofNanos(System.nanoTime() - startedNanos);
    }
}
