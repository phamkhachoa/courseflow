package edu.courseflow.enrollment.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class CoursePricingClient {

    private final RestClient courseClient;
    private final InternalJwtService internalJwt;

    public CoursePricingClient(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            @Value("${courseflow.entitlement.course-service-url:http://course-service:8080}") String courseServiceUrl) {
        this.courseClient = restClientBuilder.clone().baseUrl(courseServiceUrl).build();
        this.internalJwt = internalJwt;
    }

    public CoursePricingSnapshot pricing(String courseId) {
        try {
            CoursePricingSnapshot response = courseClient.get()
                    .uri("/internal/courses/{courseId}/pricing", courseId)
                    .headers(internalJwt::applyServiceToken)
                    .retrieve()
                    .body(CoursePricingSnapshot.class);
            if (response == null || !response.purchasable() || response.listPrice() == null || response.currency() == null) {
                throw new CoursePricingUnavailableException("Course pricing is not configured");
            }
            return response;
        } catch (RestClientException ex) {
            throw new CoursePricingUnavailableException("Course pricing is unavailable", ex);
        }
    }

    public record CoursePricingSnapshot(
            String courseId,
            BigDecimal listPrice,
            String currency,
            String priceStatus,
            boolean purchasable,
            String priceSource
    ) {
    }

    public static class CoursePricingUnavailableException extends RuntimeException {
        CoursePricingUnavailableException(String message) {
            super(message);
        }

        CoursePricingUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
