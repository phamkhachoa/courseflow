package edu.courseflow.certificate.service;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import java.math.BigDecimal;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class CertificateEligibilityClient {

    private static final String SYSTEM_USER_ID = "0";
    private static final String SYSTEM_EMAIL = "system@courseflow.local";

    private final RestClient enrollmentClient;
    private final RestClient gradebookClient;
    private final String serviceToken;

    public CertificateEligibilityClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.certificate.enrollment-service-url:http://localhost:8084}") String enrollmentServiceUrl,
            @Value("${courseflow.certificate.gradebook-service-url:http://localhost:8094}") String gradebookServiceUrl,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.enrollmentClient = restClientBuilder.baseUrl(enrollmentServiceUrl).build();
        this.gradebookClient = restClientBuilder.baseUrl(gradebookServiceUrl).build();
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    public Eligibility requireEligible(String studentId, UUID courseId, BigDecimal requestedFinalGrade) {
        requireServiceTokenConfigured();
        CourseAccessResponse enrollment = fetchEnrollment(studentId, courseId);
        if (enrollment == null || !enrollment.enrolled() || !"COMPLETED".equalsIgnoreCase(enrollment.status())) {
            throw new BadRequestException("Certificate requires a COMPLETED enrollment");
        }

        FinalGradeResponse finalGrade = fetchFinalGrade(studentId, courseId);
        if (finalGrade == null || !"FINALIZED".equalsIgnoreCase(finalGrade.status())) {
            throw new BadRequestException("Certificate requires a finalized final grade");
        }
        if (!finalGrade.passed()) {
            throw new BadRequestException("Certificate requires a passing final grade");
        }
        if (requestedFinalGrade != null && finalGrade.finalScore() != null
                && finalGrade.finalScore().compareTo(requestedFinalGrade) != 0) {
            throw new BadRequestException("Requested final grade does not match the finalized grade");
        }
        return new Eligibility(finalGrade.finalScore());
    }

    private CourseAccessResponse fetchEnrollment(String studentId, UUID courseId) {
        try {
            return enrollmentClient.get()
                    .uri(uri -> uri.path("/internal/enrollments/access")
                            .queryParam("courseId", courseId)
                            .queryParam("studentId", studentId)
                            .build())
                    .header(GatewayHeaders.SERVICE_TOKEN, serviceToken)
                    .retrieve()
                    .body(CourseAccessResponse.class);
        } catch (RestClientException ex) {
            throw new BadRequestException("Unable to verify completed enrollment for certificate");
        }
    }

    private FinalGradeResponse fetchFinalGrade(String studentId, UUID courseId) {
        try {
            return gradebookClient.get()
                    .uri("/internal/gradebook/courses/{courseId}/students/{studentId}/final-grade", courseId, studentId)
                    .headers(this::systemHeaders)
                    .retrieve()
                    .body(FinalGradeResponse.class);
        } catch (RestClientException ex) {
            throw new BadRequestException("Unable to verify finalized grade for certificate");
        }
    }

    private void systemHeaders(HttpHeaders headers) {
        headers.set(GatewayHeaders.SERVICE_TOKEN, serviceToken);
        headers.set(GatewayHeaders.USER_ID, SYSTEM_USER_ID);
        headers.set(GatewayHeaders.USER_EMAIL, SYSTEM_EMAIL);
        headers.set(GatewayHeaders.USER_ROLE, "ADMIN");
        headers.set(GatewayHeaders.USER_ROLES, "ADMIN");
    }

    private void requireServiceTokenConfigured() {
        if (serviceToken.isBlank()) {
            throw new ForbiddenException("Certificate eligibility service token is not configured");
        }
    }

    public record Eligibility(BigDecimal finalScore) {
    }

    public record CourseAccessResponse(
            String courseId,
            String studentId,
            boolean enrolled,
            String status
    ) {
    }

    public record FinalGradeResponse(
            String id,
            String courseId,
            String studentId,
            BigDecimal finalScore,
            String letter,
            boolean passed,
            String status,
            String finalizedBy,
            java.time.Instant finalizedAt
    ) {
    }
}
