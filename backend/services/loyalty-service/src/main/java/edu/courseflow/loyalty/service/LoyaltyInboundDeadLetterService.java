package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_DEAD_LETTER_INVALID_STATE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_DEAD_LETTER_NOT_FOUND;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterActionRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterActionResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterDetailDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterSummaryDto;
import edu.courseflow.loyalty.model.LoyaltyInboundDeadLetter;
import edu.courseflow.loyalty.repository.LoyaltyInboundDeadLetterRepository;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.Headers;
import org.springframework.data.domain.PageRequest;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyInboundDeadLetterService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final String ORIGINAL_TOPIC_HEADER = "kafka_dlt-original-topic";
    private static final String ORIGINAL_PARTITION_HEADER = "kafka_dlt-original-partition";
    private static final String ORIGINAL_OFFSET_HEADER = "kafka_dlt-original-offset";
    private static final String ORIGINAL_CONSUMER_GROUP_HEADER = "kafka_dlt-original-consumer-group";
    private static final String EXCEPTION_FQCN_HEADER = "kafka_dlt-exception-fqcn";
    private static final String EXCEPTION_MESSAGE_HEADER = "kafka_dlt-exception-message";
    private static final String EXCEPTION_STACKTRACE_HEADER = "kafka_dlt-exception-stacktrace";

    private final LoyaltyInboundDeadLetterRepository deadLetters;
    private final LoyaltyAccessService access;
    private final ObjectMapper objectMapper;
    private final KafkaTemplate<Object, Object> kafkaTemplate;
    private final LoyaltyMetrics metrics;

    public LoyaltyInboundDeadLetterService(
            LoyaltyInboundDeadLetterRepository deadLetters,
            LoyaltyAccessService access,
            ObjectMapper objectMapper,
            KafkaTemplate<Object, Object> kafkaTemplate,
            LoyaltyMetrics metrics) {
        this.deadLetters = deadLetters;
        this.access = access;
        this.objectMapper = objectMapper;
        this.kafkaTemplate = kafkaTemplate;
        this.metrics = metrics;
    }

    @Transactional
    public void record(ConsumerRecord<String, String> record) {
        if (deadLetters.findByDltTopicAndKafkaPartitionAndKafkaOffset(
                record.topic(), record.partition(), record.offset()).isPresent()) {
            return;
        }
        LoyaltyInboundDeadLetter deadLetter = new LoyaltyInboundDeadLetter(
                sourceTopic(record),
                record.topic(),
                headerText(record.headers(), ORIGINAL_CONSUMER_GROUP_HEADER),
                record.partition(),
                record.offset(),
                headerInteger(record.headers(), ORIGINAL_PARTITION_HEADER),
                headerLong(record.headers(), ORIGINAL_OFFSET_HEADER),
                abbreviate(record.key(), 512),
                record.value(),
                payloadHash(record.value()),
                abbreviate(headerText(record.headers(), EXCEPTION_FQCN_HEADER), 240),
                abbreviate(headerText(record.headers(), EXCEPTION_MESSAGE_HEADER), 4000),
                abbreviate(headerText(record.headers(), EXCEPTION_STACKTRACE_HEADER), 20000),
                toJson(headers(record.headers())));
        deadLetters.save(deadLetter);
        metrics.inboundDeadLetter("persist", "success", record.topic());
    }

    @Transactional(readOnly = true)
    public LoyaltyInboundDeadLetterQueryResponseDto search(
            Optional<String> status,
            Optional<String> sourceTopic,
            Optional<String> dltTopic,
            Optional<String> payloadHash,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        access.requirePlatformAdmin(user);
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyInboundDeadLetter> rows = deadLetters.search(
                normalized(status.orElse(null)),
                blankToNull(sourceTopic.orElse(null)),
                blankToNull(dltTopic.orElse(null)),
                blankToNull(payloadHash.orElse(null)),
                from.orElse(Instant.EPOCH),
                to.orElse(Instant.parse("9999-12-31T23:59:59Z")),
                PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        return new LoyaltyInboundDeadLetterQueryResponseDto(
                rows.stream().limit(pageSize).map(this::summary).toList(),
                pageSize,
                hasMore);
    }

    @Transactional(readOnly = true)
    public LoyaltyInboundDeadLetterDetailDto get(UUID id, CurrentUser user) {
        access.requirePlatformAdmin(user);
        return detail(record(id));
    }

    @Transactional
    public LoyaltyInboundDeadLetterActionResponseDto replay(
            UUID id,
            LoyaltyInboundDeadLetterActionRequestDto request,
            CurrentUser user) {
        access.requirePlatformAdmin(user);
        LoyaltyInboundDeadLetter deadLetter = recordForUpdate(id);
        if (Boolean.TRUE.equals(request == null ? null : request.dryRun())) {
            return actionResponse(deadLetter, "REPLAY", "DRY_RUN", true, false, false,
                    deadLetter.replayable() ? "WOULD_REPLAY" : "NOT_REPLAYABLE");
        }
        String reason = required(request == null ? null : request.reason(), "reason");
        if (!deadLetter.replayable()) {
            return actionResponse(deadLetter, "REPLAY", "FAILED", false, false, false, "NOT_REPLAYABLE");
        }
        try {
            kafkaTemplate.send(deadLetter.getSourceTopic(), deadLetter.getRecordKey(), deadLetter.getPayload()).join();
            deadLetter.markReplayed(actorId(user), reason);
            LoyaltyInboundDeadLetter saved = deadLetters.save(deadLetter);
            metrics.inboundDeadLetter("replay", "success", saved.getSourceTopic());
            return actionResponse(saved, "REPLAY", "REPLAYED", false, true, false, "REPLAYED");
        } catch (RuntimeException ex) {
            deadLetter.markReplayFailed(abbreviate(rootMessage(ex), 4000));
            LoyaltyInboundDeadLetter saved = deadLetters.save(deadLetter);
            metrics.inboundDeadLetter("replay", "error", saved.getSourceTopic());
            return actionResponse(saved, "REPLAY", "FAILED", false, false, false, "PUBLISH_FAILED");
        }
    }

    @Transactional
    public LoyaltyInboundDeadLetterActionResponseDto discard(
            UUID id,
            LoyaltyInboundDeadLetterActionRequestDto request,
            CurrentUser user) {
        access.requirePlatformAdmin(user);
        LoyaltyInboundDeadLetter deadLetter = recordForUpdate(id);
        if (Boolean.TRUE.equals(request == null ? null : request.dryRun())) {
            return actionResponse(deadLetter, "DISCARD", "DRY_RUN", true, false, false,
                    deadLetter.discardable() ? "WOULD_DISCARD" : "NOT_DISCARDABLE");
        }
        String reason = required(request == null ? null : request.reason(), "reason");
        if (!deadLetter.discardable()) {
            return actionResponse(deadLetter, "DISCARD", "FAILED", false, false, false, "NOT_DISCARDABLE");
        }
        try {
            deadLetter.discard(actorId(user), reason);
        } catch (IllegalStateException ex) {
            throw BadRequestException.coded(LOYALTY_DEAD_LETTER_INVALID_STATE, ex.getMessage());
        }
        LoyaltyInboundDeadLetter saved = deadLetters.save(deadLetter);
        metrics.inboundDeadLetter("discard", "success", saved.getSourceTopic());
        return actionResponse(saved, "DISCARD", "DISCARDED", false, false, true, "DISCARDED");
    }

    public static String payloadHash(String payload) {
        try {
            return "sha256:" + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest((payload == null ? "" : payload).getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private LoyaltyInboundDeadLetter record(UUID id) {
        return deadLetters.findById(id)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_DEAD_LETTER_NOT_FOUND,
                        "Loyalty inbound dead letter not found"));
    }

    private LoyaltyInboundDeadLetter recordForUpdate(UUID id) {
        return deadLetters.findByIdForUpdate(id)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_DEAD_LETTER_NOT_FOUND,
                        "Loyalty inbound dead letter not found"));
    }

    private LoyaltyInboundDeadLetterSummaryDto summary(LoyaltyInboundDeadLetter record) {
        return new LoyaltyInboundDeadLetterSummaryDto(
                record.getId(),
                record.getSourceTopic(),
                record.getDltTopic(),
                record.getConsumerGroup(),
                record.getKafkaPartition(),
                record.getKafkaOffset(),
                record.getOriginalPartition(),
                record.getOriginalOffset(),
                record.getRecordKey(),
                record.getStatus(),
                record.getReplayAttempts(),
                record.getPayloadHash(),
                record.getExceptionClass(),
                record.getExceptionMessage(),
                record.getCreatedAt(),
                record.getUpdatedAt(),
                record.getLastReplayAt(),
                record.getReplayedAt(),
                record.getDiscardedAt());
    }

    private LoyaltyInboundDeadLetterDetailDto detail(LoyaltyInboundDeadLetter record) {
        return new LoyaltyInboundDeadLetterDetailDto(
                record.getId(),
                record.getSourceTopic(),
                record.getDltTopic(),
                record.getConsumerGroup(),
                record.getKafkaPartition(),
                record.getKafkaOffset(),
                record.getOriginalPartition(),
                record.getOriginalOffset(),
                record.getRecordKey(),
                record.getStatus(),
                record.getReplayAttempts(),
                record.getPayloadHash(),
                record.getPayload() == null ? 0 : record.getPayload().getBytes(StandardCharsets.UTF_8).length,
                record.getExceptionClass(),
                record.getExceptionMessage(),
                record.getStacktrace(),
                record.getLastReplayError(),
                record.getResolvedBy(),
                record.getResolutionNote(),
                readMap(record.getHeadersJson()),
                record.getCreatedAt(),
                record.getUpdatedAt(),
                record.getLastReplayAt(),
                record.getReplayedAt(),
                record.getDiscardedAt());
    }

    private LoyaltyInboundDeadLetterActionResponseDto actionResponse(
            LoyaltyInboundDeadLetter record,
            String action,
            String status,
            boolean dryRun,
            boolean replayed,
            boolean discarded,
            String reasonCode) {
        return new LoyaltyInboundDeadLetterActionResponseDto(
                record.getId(),
                action,
                status,
                dryRun,
                replayed,
                discarded,
                reasonCode,
                record.getPayloadHash(),
                Instant.now());
    }

    private String sourceTopic(ConsumerRecord<String, String> record) {
        String original = headerText(record.headers(), ORIGINAL_TOPIC_HEADER);
        if (original != null) {
            return original;
        }
        if (record.topic().endsWith(".DLT")) {
            return record.topic().substring(0, record.topic().length() - 4);
        }
        return record.topic();
    }

    private Map<String, Object> headers(Headers headers) {
        Map<String, Object> values = new LinkedHashMap<>();
        for (Header header : headers) {
            Object value = displayHeaderValue(header.value());
            Object existing = values.get(header.key());
            if (existing instanceof List<?> list) {
                List<Object> updated = new ArrayList<>(list);
                updated.add(value);
                values.put(header.key(), updated);
            } else if (existing != null) {
                values.put(header.key(), new ArrayList<>(List.of(existing, value)));
            } else {
                values.put(header.key(), value);
            }
        }
        return values;
    }

    private Object displayHeaderValue(byte[] value) {
        if (value == null) {
            return null;
        }
        String text = new String(value, StandardCharsets.UTF_8);
        if (text.chars().allMatch(ch -> ch == '\n' || ch == '\r' || ch == '\t' || (ch >= 32 && ch < 127))) {
            return abbreviate(text, 4000);
        }
        if (value.length == Integer.BYTES) {
            return ByteBuffer.wrap(value).getInt();
        }
        if (value.length == Long.BYTES) {
            return ByteBuffer.wrap(value).getLong();
        }
        return "base64:" + Base64.getEncoder().encodeToString(value);
    }

    private String headerText(Headers headers, String name) {
        Header header = headers.lastHeader(name);
        if (header == null || header.value() == null) {
            return null;
        }
        Object value = displayHeaderValue(header.value());
        return value == null ? null : String.valueOf(value);
    }

    private Integer headerInteger(Headers headers, String name) {
        Long value = headerLong(headers, name);
        if (value == null) {
            return null;
        }
        return value > Integer.MAX_VALUE || value < Integer.MIN_VALUE ? null : value.intValue();
    }

    private Long headerLong(Headers headers, String name) {
        Header header = headers.lastHeader(name);
        if (header == null || header.value() == null) {
            return null;
        }
        byte[] value = header.value();
        if (value.length == Integer.BYTES) {
            return (long) ByteBuffer.wrap(value).getInt();
        }
        if (value.length == Long.BYTES) {
            return ByteBuffer.wrap(value).getLong();
        }
        try {
            return Long.parseLong(new String(value, StandardCharsets.UTF_8));
        } catch (NumberFormatException ex) {
            return null;
        }
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

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw BadRequestException.coded(
                    LOYALTY_DEAD_LETTER_INVALID_STATE,
                    "Unable to serialize loyalty dead-letter metadata");
        }
    }

    private String required(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw BadRequestException.coded(LOYALTY_DEAD_LETTER_INVALID_STATE, field + " is required");
        }
        return normalized;
    }

    private String actorId(CurrentUser user) {
        if (user == null) {
            return null;
        }
        if (user.id() != null) {
            return user.id().toString();
        }
        return user.email();
    }

    private String rootMessage(Throwable ex) {
        Throwable root = ex;
        while (root.getCause() != null) {
            root = root.getCause();
        }
        return root.getMessage() == null ? root.getClass().getSimpleName() : root.getMessage();
    }

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 200));
    }

    private String normalized(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? null : normalized.toUpperCase();
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String abbreviate(String value, int maxLength) {
        if (value == null || value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }
}
