package edu.courseflow.certificate.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.certificate.dto.IssueCertificateRequestDto;
import edu.courseflow.certificate.model.ProcessedEvent;
import edu.courseflow.certificate.repository.CertificateRepository;
import edu.courseflow.certificate.repository.ProcessedEventRepository;
import edu.courseflow.certificate.service.CertificateService;
import java.math.BigDecimal;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Consumes gradebook final-grade events and auto-issues a certificate on a passing grade.
 *
 * <p>The dedup insert into {@code processed_events} and the {@link CertificateService#issue}
 * call share one transaction, so any failure rolls back the processed_events row and the event
 * will be retried.
 */
@Component
public class FinalGradeEventConsumer {
    private static final Logger log = LoggerFactory.getLogger(FinalGradeEventConsumer.class);
    private static final String CONSUMER = "certificate:gradebook.final_grade.updated";

    private final CertificateService certificateService;
    private final CertificateRepository certificates;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;

    public FinalGradeEventConsumer(CertificateService certificateService,
            CertificateRepository certificates,
            ProcessedEventRepository processedEvents,
            ObjectMapper objectMapper) {
        this.certificateService = certificateService;
        this.certificates = certificates;
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "gradebook.final_grade.updated", groupId = "certificate-service")
    @Transactional
    public void onFinalGradeUpdated(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);

        // Null-safe parsing: a payload missing required fields must not throw an NPE that turns the
        // record into an un-skippable poison message. Skip malformed events with a clear log; the
        // DefaultErrorHandler/DLT backstops genuinely unexpected (non-data) failures.
        String eventIdText = text(event, "eventId");
        if (eventIdText == null) {
            log.warn("certificate: final-grade event missing eventId; skipping payload={}", payload);
            return;
        }
        UUID eventId;
        try {
            eventId = UUID.fromString(eventIdText);
        } catch (IllegalArgumentException ex) {
            log.warn("certificate: final-grade event has non-UUID eventId '{}'; skipping", eventIdText);
            return;
        }

        if (processedEvents.existsById(eventId)) {
            return;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, CONSUMER));
        } catch (DataIntegrityViolationException duplicate) {
            return;
        }

        JsonNode passedNode = event.get("passed");
        boolean passed = passedNode != null && !passedNode.isNull() && passedNode.asBoolean();
        if (!passed) {
            log.debug("Final grade event {} not passing; no certificate issued", eventId);
            return;
        }

        String studentId = text(event, "studentId");
        String courseId = text(event, "courseId");
        String finalScoreText = text(event, "finalScore");
        if (studentId == null || courseId == null || finalScoreText == null) {
            log.warn("certificate: final-grade event {} missing studentId/courseId/finalScore; skipping", eventId);
            return;
        }

        UUID courseUuid;
        BigDecimal finalScore;
        try {
            courseUuid = UUID.fromString(courseId);
            finalScore = new BigDecimal(finalScoreText);
        } catch (IllegalArgumentException ex) {
            log.warn("certificate: final-grade event {} has malformed courseId/finalScore; skipping", eventId);
            return;
        }

        boolean exists = certificates.existsByStudentIdAndCourseIdAndStatus(studentId, courseUuid, "ISSUED");
        if (exists) return;

        // actorId is the system principal here; certificates auto-issued from a passing grade are not
        // attributed to a human actor (manual issue/revoke require ADMIN/INSTRUCTOR via the controller).
        certificateService.issue(new IssueCertificateRequestDto(studentId, courseId, finalScore, "system"));
    }

    /** Read a text field, returning null when absent or JSON null (no NPE on missing keys). */
    private static String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return text.isBlank() ? null : text;
    }
}
