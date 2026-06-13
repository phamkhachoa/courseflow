package edu.courseflow.course.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.LearningDtos.CertificateEligibilityDto;
import edu.courseflow.course.dto.LearningDtos.CertificateMissingRequirementDto;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class CertificateEligibilityClient {

    private static final Logger log = LoggerFactory.getLogger(CertificateEligibilityClient.class);

    private final RestClient certificateClient;
    private final InternalJwtService internalJwt;

    public CertificateEligibilityClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.certificate.service-url:http://certificate-service:8080}") String certificateServiceUrl,
            @Value("${courseflow.certificate.eligibility-timeout-ms:1500}") long eligibilityTimeoutMs,
            InternalJwtService internalJwt) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = (int) Math.max(250, Math.min(eligibilityTimeoutMs, 5000));
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.certificateClient = restClientBuilder.clone()
                .baseUrl(certificateServiceUrl)
                .requestFactory(requestFactory)
                .build();
        this.internalJwt = internalJwt;
    }

    public CertificateEligibilityDto loadEligibility(UUID courseId, CurrentUser user) {
        String studentId = user == null || user.id() == null ? "" : String.valueOf(user.id());
        if (courseId == null || studentId.isBlank()) {
            return unavailable(courseId, studentId, "Learner identity is not available.");
        }
        try {
            CertificateEligibilityDto response = certificateClient.get()
                    .uri(uri -> uri.path("/internal/certificates/eligibility")
                            .queryParam("courseId", courseId)
                            .queryParam("studentId", studentId)
                            .build())
                    .headers(headers -> internalJwt.applyUserToken(headers, user))
                    .retrieve()
                    .body(CertificateEligibilityDto.class);
            return response == null ? unavailable(courseId, studentId, "Certificate service returned an empty response.") : response;
        } catch (RestClientException ex) {
            log.warn("Certificate eligibility enrichment failed", ex);
            return unavailable(courseId, studentId, "Certificate service is temporarily unavailable.");
        }
    }

    private CertificateEligibilityDto unavailable(UUID courseId, String studentId, String detail) {
        return new CertificateEligibilityDto(
                Instant.now(),
                courseId == null ? null : courseId.toString(),
                studentId,
                false,
                "ELIGIBILITY_UNAVAILABLE",
                false,
                false,
                false,
                false,
                null,
                null,
                null,
                null,
                null,
                null,
                List.of(new CertificateMissingRequirementDto(
                        "CERTIFICATE_ELIGIBILITY_UNAVAILABLE",
                        "Chưa kiểm tra được điều kiện chứng chỉ",
                        detail)));
    }
}
