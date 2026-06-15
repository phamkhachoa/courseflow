package edu.courseflow.analytics.service;

import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelIngestResponseDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelRowDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelStageDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecordMarketingFunnelEventRequestDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.model.MarketingFunnelEventReceipt;
import edu.courseflow.analytics.model.MarketingFunnelMetric;
import edu.courseflow.analytics.repository.ReportingRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ReportingService {

    private static final int DEFAULT_MARKETING_FUNNEL_LIMIT = 500;
    private static final int MAX_MARKETING_FUNNEL_LIMIT = 5_000;
    private static final int DEFAULT_RECOMMENDATION_LIMIT = 10;
    private static final int MAX_RECOMMENDATION_LIMIT = 50;
    private static final int DEFAULT_RELATED_LIMIT = 6;
    private static final int MAX_RELATED_LIMIT = 12;
    private static final long MAX_MARKETING_FUNNEL_EVENT_COUNT = 100_000;
    private static final Pattern SAFE_DIMENSION = Pattern.compile("[A-Za-z0-9._:-]{1,120}");
    private static final List<String> STANDARD_FUNNEL_STAGES = List.of(
            "IMPRESSION",
            "COURSE_VIEW",
            "CHECKOUT_STARTED",
            "PAYMENT_SUCCESS",
            "ENROLLED");

    private final ReportingRepository reporting;

    public ReportingService(ReportingRepository reporting) {
        this.reporting = reporting;
    }

    public CourseCompletionDto courseCompletion(UUID courseId) {
        return reporting.courseCompletion(courseId)
                .orElse(new CourseCompletionDto(courseId.toString(), 0, 0, 0.0, null, Instant.now()));
    }

    public List<TimeSpentDto> timeSpent(String studentId) {
        return reporting.timeSpentByStudent(studentId);
    }

    public OrgDashboardDto orgDashboard(String orgId) {
        return reporting.orgDashboard(orgId)
                .orElse(new OrgDashboardDto(orgId, 0, 0, 0.0, Instant.now()));
    }

    public List<RecommendationDto> recommendations(String studentId, int limit) {
        return reporting.recommendations(studentId, normalizeBoundedLimit(
                limit,
                DEFAULT_RECOMMENDATION_LIMIT,
                MAX_RECOMMENDATION_LIMIT));
    }

    public List<RelatedCourseDto> relatedCourses(UUID courseId, int limit) {
        return reporting.relatedCourses(courseId, normalizeBoundedLimit(limit, DEFAULT_RELATED_LIMIT, MAX_RELATED_LIMIT));
    }

    public MarketingFunnelDto marketingFunnel(String tenantId,
                                              String applicationId,
                                              String campaignCode,
                                              String source,
                                              LocalDate from,
                                              LocalDate to,
                                              int limit) {
        String normalizedTenant = required(tenantId, "tenantId");
        String normalizedApplication = required(applicationId, "applicationId");
        int safeLimit = normalizeLimit(limit);
        List<MarketingFunnelMetric> rows = reporting.marketingFunnel(
                normalizedTenant,
                normalizedApplication,
                blankToNull(campaignCode),
                blankToNull(source),
                from,
                to,
                safeLimit);
        return new MarketingFunnelDto(
                normalizedTenant,
                normalizedApplication,
                blankToNull(campaignCode),
                blankToNull(source),
                from,
                to,
                aggregateStages(rows),
                rows.stream().map(this::toRowDto).toList(),
                Instant.now());
    }

    @Transactional
    public MarketingFunnelIngestResponseDto recordMarketingFunnelEvent(
            RecordMarketingFunnelEventRequestDto request,
            CurrentUser actor) {
        UUID eventId = request.eventId();
        String tenantId = requiredDimension(request.tenantId(), "tenantId", 80);
        String applicationId = requiredDimension(request.applicationId(), "applicationId", 80);
        String campaignCode = optionalDimension(request.campaignCode(), "campaignCode", 120);
        String source = optionalDimension(request.source(), "source", 120);
        String stage = normalizeStage(request.stage());
        LocalDate bucketDate = bucketDate(request);
        long eventCount = eventCount(request.eventCount());
        String requestHash = requestHash(
                eventId,
                tenantId,
                applicationId,
                campaignCode,
                source,
                stage,
                bucketDate,
                eventCount);

        var existing = reporting.findMarketingFunnelReceipt(eventId);
        if (existing.isPresent()) {
            ensureSameReceipt(existing.get(), requestHash);
            return new MarketingFunnelIngestResponseDto(eventId, false, true, stage, bucketDate, eventCount);
        }

        try {
            reporting.saveMarketingFunnelReceipt(new MarketingFunnelEventReceipt(
                    eventId,
                    tenantId,
                    applicationId,
                    campaignCode,
                    source,
                    stage,
                    bucketDate,
                    eventCount,
                    requestHash,
                    actorId(actor)));
        } catch (DataIntegrityViolationException duplicate) {
            var receipt = reporting.findMarketingFunnelReceipt(eventId)
                    .orElseThrow(() -> duplicate);
            ensureSameReceipt(receipt, requestHash);
            return new MarketingFunnelIngestResponseDto(eventId, false, true, stage, bucketDate, eventCount);
        }

        reporting.incrementMarketingFunnelMetric(
                tenantId,
                applicationId,
                campaignCode,
                source,
                stage,
                bucketDate,
                eventCount);
        return new MarketingFunnelIngestResponseDto(eventId, true, false, stage, bucketDate, eventCount);
    }

    private List<MarketingFunnelStageDto> aggregateStages(List<MarketingFunnelMetric> rows) {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (String stage : STANDARD_FUNNEL_STAGES) {
            counts.put(stage, 0L);
        }
        for (MarketingFunnelMetric row : rows) {
            counts.merge(row.getStage(), row.getEventCount(), Long::sum);
        }

        long firstCount = counts.values().stream().filter(count -> count > 0).findFirst().orElse(0L);
        long previous = 0L;
        List<MarketingFunnelStageDto> stages = new ArrayList<>();
        for (Map.Entry<String, Long> entry : counts.entrySet()) {
            long count = entry.getValue();
            Double stepRate = previous <= 0 ? null : percentage(count, previous);
            Double overallRate = firstCount <= 0 ? null : percentage(count, firstCount);
            stages.add(new MarketingFunnelStageDto(entry.getKey(), count, stepRate, overallRate));
            previous = count;
        }
        return stages;
    }

    private MarketingFunnelRowDto toRowDto(MarketingFunnelMetric row) {
        return new MarketingFunnelRowDto(
                row.getBucketDate(),
                row.getCampaignCode(),
                row.getSource(),
                row.getStage(),
                row.getEventCount());
    }

    private static void ensureSameReceipt(MarketingFunnelEventReceipt receipt, String requestHash) {
        if (!requestHash.equals(receipt.getRequestHash())) {
            throw ConflictException.coded(
                    "ANALYTICS_MARKETING_FUNNEL_IDEMPOTENCY_CONFLICT",
                    "Marketing funnel event id was already used with a different payload");
        }
    }

    private static LocalDate bucketDate(RecordMarketingFunnelEventRequestDto request) {
        if (request.bucketDate() != null) {
            return request.bucketDate();
        }
        Instant occurredAt = request.occurredAt() == null ? Instant.now() : request.occurredAt();
        return occurredAt.atZone(ZoneOffset.UTC).toLocalDate();
    }

    private static long eventCount(Long requested) {
        long count = requested == null ? 1L : requested;
        if (count <= 0 || count > MAX_MARKETING_FUNNEL_EVENT_COUNT) {
            throw BadRequestException.coded(
                    "ANALYTICS_MARKETING_FUNNEL_INVALID_COUNT",
                    "Marketing funnel eventCount must be between 1 and " + MAX_MARKETING_FUNNEL_EVENT_COUNT);
        }
        return count;
    }

    private static String normalizeStage(String value) {
        String stage = required(value, "stage").trim().toUpperCase().replace('-', '_');
        if (!STANDARD_FUNNEL_STAGES.contains(stage)) {
            throw BadRequestException.coded(
                    "ANALYTICS_MARKETING_FUNNEL_UNKNOWN_STAGE",
                    "Marketing funnel stage is not supported: " + value);
        }
        return stage;
    }

    private static String requiredDimension(String value, String field, int maxLength) {
        return safeDimension(required(value, field), field, maxLength);
    }

    private static String optionalDimension(String value, String field, int maxLength) {
        String normalized = blankToNull(value);
        return normalized == null ? null : safeDimension(normalized, field, maxLength);
    }

    private static String safeDimension(String value, String field, int maxLength) {
        if (value.length() > maxLength || !SAFE_DIMENSION.matcher(value).matches()) {
            throw BadRequestException.coded(
                    "ANALYTICS_MARKETING_FUNNEL_UNSAFE_DIMENSION",
                    field + " must use a non-PII code containing only letters, numbers, dot, underscore, colon or hyphen");
        }
        return value;
    }

    private static String requestHash(UUID eventId,
                                      String tenantId,
                                      String applicationId,
                                      String campaignCode,
                                      String source,
                                      String stage,
                                      LocalDate bucketDate,
                                      long eventCount) {
        String canonical = String.join("|",
                eventId.toString(),
                tenantId,
                applicationId,
                campaignCode == null ? "" : campaignCode,
                source == null ? "" : source,
                stage,
                bucketDate.toString(),
                String.valueOf(eventCount));
        return sha256(canonical);
    }

    private static String sha256(String canonical) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(canonical.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private static String actorId(CurrentUser actor) {
        if (actor == null) {
            return "unknown";
        }
        if (actor.id() != null) {
            return "user:" + actor.id();
        }
        if (actor.internalToken() != null) {
            return "service";
        }
        return "unknown";
    }

    private static double percentage(long numerator, long denominator) {
        return Math.round((numerator * 10_000.0 / denominator)) / 100.0;
    }

    private static int normalizeLimit(int limit) {
        if (limit <= 0) {
            return DEFAULT_MARKETING_FUNNEL_LIMIT;
        }
        return Math.min(limit, MAX_MARKETING_FUNNEL_LIMIT);
    }

    private static int normalizeBoundedLimit(int limit, int defaultLimit, int maxLimit) {
        if (limit <= 0) {
            return defaultLimit;
        }
        return Math.min(limit, maxLimit);
    }

    private static String required(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw new IllegalArgumentException(field + " is required");
        }
        return normalized;
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
