package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentPreviewRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentPreviewResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentVariantAllocationDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentVariantPreviewRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncentiveExperimentService {

    private static final String POLICY_VERSION = "promotion-experiment-preview-v1";
    private static final String IMPLICIT_HOLDOUT_KEY = "__HOLDOUT__";
    private static final int FULL_TRAFFIC_BPS = 10_000;

    private final IncentiveAccessService access;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;

    public IncentiveExperimentService(IncentiveAccessService access,
                                      IncentiveAuditEventRepository auditEvents,
                                      ObjectMapper objectMapper) {
        this.access = access;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public ExperimentPreviewResponseDto preview(ExperimentPreviewRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        if (request == null || request.context() == null) {
            throw new BadRequestException("Experiment preview context is required");
        }
        EvaluateIncentivesRequestDto context = request.context();
        String tenantId = required(context.tenantId(), "tenantId");
        String applicationId = required(context.applicationId(), "applicationId");
        String experimentKey = required(request.experimentKey(), "experimentKey");
        access.requireAdminAccess(tenantId, applicationId, user);
        access.requireActiveApplication(tenantId, applicationId, user, "experiment-preview");

        Assignment assignment = assignment(context, request.assignmentUnit(), request.assignmentAttributeKey());
        List<Allocation> allocations = allocations(request.variants());
        int bucket = bucket(experimentKey, assignment.unit(), assignment.key());
        Allocation selected = select(allocations, bucket);
        String assignmentKeyHash = hashHex(assignment.unit() + "\n" + assignment.key());
        List<String> reasonCodes = reasonCodes(selected, allocations);
        ExperimentPreviewResponseDto response = new ExperimentPreviewResponseDto(
                true,
                false,
                POLICY_VERSION,
                tenantId,
                applicationId,
                experimentKey,
                assignment.unit(),
                assignmentKeyHash,
                bucket,
                selected.key(),
                selected.holdout(),
                selected.holdout() ? "HOLDOUT" : "APPLY_VARIANT",
                reasonCodes,
                allocations.stream().map(allocation -> allocation.toDto(allocation == selected)).toList(),
                Instant.now());
        audit(response, request.note(), correlationId, access.sourceClientId(user), user);
        return response;
    }

    private Assignment assignment(EvaluateIncentivesRequestDto context,
                                  String requestedUnit,
                                  String attributeKey) {
        String unit = blankToNull(requestedUnit);
        if (unit == null) {
            unit = "PROFILE";
        }
        unit = unit.toUpperCase(Locale.ROOT);
        return switch (unit) {
            case "PROFILE" -> new Assignment(unit, required(context.profileId(), "profileId"));
            case "EXTERNAL_REFERENCE" -> new Assignment(
                    unit,
                    required(context.externalReference(), "externalReference"));
            case "ATTRIBUTE" -> {
                String key = required(attributeKey, "assignmentAttributeKey");
                if (context.attributes() == null || !context.attributes().containsKey(key)) {
                    throw new BadRequestException("assignment attribute is required: " + key);
                }
                Object value = context.attributes().get(key);
                yield new Assignment(unit, required(value == null ? null : String.valueOf(value), key));
            }
            default -> throw new BadRequestException("Unsupported experiment assignmentUnit: " + unit);
        };
    }

    private List<Allocation> allocations(List<ExperimentVariantPreviewRequestDto> variants) {
        if (variants == null || variants.isEmpty()) {
            throw new BadRequestException("Experiment preview requires variants");
        }
        List<Variant> normalized = new ArrayList<>();
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        int totalWeight = 0;
        boolean hasTreatment = false;
        for (ExperimentVariantPreviewRequestDto variant : variants) {
            if (variant == null) {
                throw new BadRequestException("Experiment variant is required");
            }
            String key = required(variant.key(), "variant.key");
            if (IMPLICIT_HOLDOUT_KEY.equalsIgnoreCase(key)) {
                throw new BadRequestException(IMPLICIT_HOLDOUT_KEY + " is reserved for implicit holdout traffic");
            }
            String duplicateKey = key.toLowerCase(Locale.ROOT);
            if (!seen.add(duplicateKey)) {
                throw new BadRequestException("Duplicate experiment variant key: " + key);
            }
            if (variant.weightBps() == null) {
                throw new BadRequestException("variant.weightBps is required");
            }
            if (variant.weightBps() > FULL_TRAFFIC_BPS) {
                throw new BadRequestException("variant.weightBps cannot exceed 10000");
            }
            boolean holdout = Boolean.TRUE.equals(variant.holdout());
            totalWeight += variant.weightBps();
            if (totalWeight > FULL_TRAFFIC_BPS) {
                throw new BadRequestException("Experiment variant weights cannot exceed 10000 bps");
            }
            if (!holdout && variant.weightBps() > 0) {
                hasTreatment = true;
            }
            normalized.add(new Variant(
                    key,
                    variant.weightBps(),
                    holdout,
                    blankToNull(variant.campaignCode()),
                    metadata(variant.metadata()),
                    false));
        }
        int implicitHoldoutWeight = FULL_TRAFFIC_BPS - totalWeight;
        if (implicitHoldoutWeight > 0) {
            normalized.add(new Variant(
                    IMPLICIT_HOLDOUT_KEY,
                    implicitHoldoutWeight,
                    true,
                    null,
                    Map.of(),
                    true));
        }
        long positiveAllocations = normalized.stream().filter(variant -> variant.weightBps() > 0).count();
        if (totalWeight == 0) {
            throw new BadRequestException("Experiment preview requires positive traffic allocation");
        }
        if (!hasTreatment) {
            throw new BadRequestException("Experiment preview requires at least one treatment variant");
        }
        if (positiveAllocations < 2) {
            throw new BadRequestException("Experiment preview requires at least two positive allocations");
        }

        List<Allocation> allocations = new ArrayList<>();
        int cursor = 0;
        for (Variant variant : normalized) {
            int start = cursor;
            int end = cursor + variant.weightBps();
            allocations.add(new Allocation(
                    variant.key(),
                    variant.weightBps(),
                    variant.holdout(),
                    variant.campaignCode(),
                    start,
                    end,
                    variant.metadata(),
                    variant.implicit()));
            cursor = end;
        }
        return List.copyOf(allocations);
    }

    private Allocation select(List<Allocation> allocations, int bucket) {
        return allocations.stream()
                .filter(allocation -> allocation.weightBps() > 0)
                .filter(allocation -> bucket >= allocation.startBucketInclusive()
                        && bucket < allocation.endBucketExclusive())
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("Experiment bucket did not resolve to a variant"));
    }

    private List<String> reasonCodes(Allocation selected, List<Allocation> allocations) {
        List<String> reasons = new ArrayList<>();
        reasons.add("EXPERIMENT_PREVIEW_ONLY");
        reasons.add(selected.holdout() ? "EXPERIMENT_HOLDOUT_SELECTED" : "EXPERIMENT_VARIANT_SELECTED");
        if (allocations.stream().anyMatch(Allocation::implicit)) {
            reasons.add("EXPERIMENT_IMPLICIT_HOLDOUT_CONFIGURED");
        }
        return List.copyOf(reasons);
    }

    private void audit(ExperimentPreviewResponseDto response,
                       String note,
                       String correlationId,
                       String sourceClientId,
                       CurrentUser user) {
        auditEvents.save(new IncentiveAuditEvent(
                response.tenantId(),
                response.applicationId(),
                response.experimentKey(),
                "experiment",
                "experiment.previewed",
                actorId(user),
                note,
                toJson(auditPayload(response)),
                correlationId,
                sourceClientId));
    }

    private Map<String, Object> auditPayload(ExperimentPreviewResponseDto response) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("policyVersion", response.policyVersion());
        payload.put("assignmentUnit", response.assignmentUnit());
        payload.put("assignmentKeyHash", response.assignmentKeyHash());
        payload.put("bucket", response.bucket());
        payload.put("selectedVariantKey", response.selectedVariantKey());
        payload.put("holdout", response.holdout());
        payload.put("recommendedAction", response.recommendedAction());
        payload.put("reasonCodes", response.reasonCodes());
        payload.put("variants", response.variants().stream()
                .map(variant -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("key", variant.key());
                    row.put("weightBps", variant.weightBps());
                    row.put("holdout", variant.holdout());
                    row.put("campaignCode", variant.campaignCode());
                    row.put("startBucketInclusive", variant.startBucketInclusive());
                    row.put("endBucketExclusive", variant.endBucketExclusive());
                    row.put("selected", variant.selected());
                    row.put("metadataKeys", variant.metadata() == null ? List.of() : variant.metadata().keySet());
                    return row;
                })
                .toList());
        return payload;
    }

    private int bucket(String experimentKey, String assignmentUnit, String assignmentKey) {
        byte[] digest = sha256(experimentKey + "\n" + assignmentUnit + "\n" + assignmentKey);
        long value = 0L;
        for (int i = 0; i < Long.BYTES; i++) {
            value = (value << Byte.SIZE) | (digest[i] & 0xffL);
        }
        return (int) Long.remainderUnsigned(value, FULL_TRAFFIC_BPS);
    }

    private String hashHex(String value) {
        return HexFormat.of().formatHex(sha256(value));
    }

    private byte[] sha256(String value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize experiment preview audit payload", ex);
        }
    }

    private Map<String, Object> metadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> sanitized = new LinkedHashMap<>();
        metadata.forEach((key, value) -> {
            String normalized = blankToNull(key);
            if (normalized != null && value != null) {
                sanitized.put(normalized, value);
            }
        });
        return Map.copyOf(sanitized);
    }

    private String required(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw new BadRequestException(field + " is required");
        }
        return normalized;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String actorId(CurrentUser user) {
        if (user == null || user.id() == null) {
            return "system";
        }
        return user.id().toString();
    }

    private record Assignment(String unit, String key) {
    }

    private record Variant(String key,
                           int weightBps,
                           boolean holdout,
                           String campaignCode,
                           Map<String, Object> metadata,
                           boolean implicit) {
    }

    private record Allocation(String key,
                              int weightBps,
                              boolean holdout,
                              String campaignCode,
                              int startBucketInclusive,
                              int endBucketExclusive,
                              Map<String, Object> metadata,
                              boolean implicit) {
        ExperimentVariantAllocationDto toDto(boolean selected) {
            return new ExperimentVariantAllocationDto(
                    key,
                    weightBps,
                    holdout,
                    campaignCode,
                    startBucketInclusive,
                    endBucketExclusive,
                    selected,
                    metadata);
        }
    }
}
