package edu.courseflow.certificate.service;

import edu.courseflow.certificate.dto.CertificateEligibilityDto;
import edu.courseflow.certificate.dto.CertificateEligibilityDto.MissingRequirementDto;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class CertificateEligibilityClient {

    private final RestClient enrollmentClient;
    private final RestClient gradebookClient;
    private final RestClient courseClient;
    private final InternalJwtService internalJwt;

    public CertificateEligibilityClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.certificate.enrollment-service-url:http://enrollment-service:8080}") String enrollmentServiceUrl,
            @Value("${courseflow.certificate.gradebook-service-url:http://gradebook-service:8080}") String gradebookServiceUrl,
            @Value("${courseflow.certificate.course-service-url:http://course-service:8080}") String courseServiceUrl,
            @Value("${courseflow.certificate.eligibility-timeout-ms:1500}") long eligibilityTimeoutMs,
            InternalJwtService internalJwt) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = (int) Math.max(250, Math.min(eligibilityTimeoutMs, 5000));
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.enrollmentClient = restClientBuilder.clone().baseUrl(enrollmentServiceUrl).requestFactory(requestFactory).build();
        this.gradebookClient = restClientBuilder.clone().baseUrl(gradebookServiceUrl).requestFactory(requestFactory).build();
        this.courseClient = restClientBuilder.clone().baseUrl(courseServiceUrl).requestFactory(requestFactory).build();
        this.internalJwt = internalJwt;
    }

    public Eligibility requireEligible(String studentId, UUID courseId, BigDecimal requestedFinalGrade) {
        CourseAccessResponse enrollment = fetchEnrollment(studentId, courseId);
        if (enrollment == null || !enrollment.enrolled() || !"COMPLETED".equalsIgnoreCase(enrollment.status())) {
            throw new BadRequestException("Certificate requires a COMPLETED enrollment");
        }
        CourseProgressResponse progress = fetchCourseProgress(studentId, courseId);
        if (progress == null || !progress.completed()) {
            throw new BadRequestException("Certificate requires all required published course items to be completed");
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

    public CertificateEligibilityDto evaluate(String studentId, UUID courseId) {
        Instant generatedAt = Instant.now();
        DependencyResult<CourseAccessResponse> enrollmentResult = readEnrollment(studentId, courseId);
        DependencyResult<CourseProgressResponse> courseProgressResult = readCourseProgress(studentId, courseId);
        DependencyResult<FinalGradeResponse> finalGradeResult = readFinalGrade(studentId, courseId);
        List<MissingRequirementDto> missing = new ArrayList<>();

        boolean dependencyUnavailable = enrollmentResult.unavailable()
                || courseProgressResult.unavailable()
                || finalGradeResult.unavailable();
        CourseAccessResponse enrollment = enrollmentResult.value();
        boolean completionEligible = enrollment != null
                && enrollment.enrolled()
                && "COMPLETED".equalsIgnoreCase(enrollment.status());
        if (enrollmentResult.unavailable()) {
            missing.add(new MissingRequirementDto(
                    "COURSE_COMPLETION_UNAVAILABLE",
                    "Chưa kiểm tra được hoàn thành khóa",
                    "Certificate service chưa lấy được trạng thái enrollment/completion."));
        } else if (!completionEligible) {
            missing.add(new MissingRequirementDto(
                    "COURSE_COMPLETION",
                    "Hoàn thành khóa học",
                    "Enrollment phải ở trạng thái COMPLETED trước khi cấp chứng chỉ."));
        }
        CourseProgressResponse courseProgress = courseProgressResult.value();
        boolean requiredItemsEligible = courseProgress != null && courseProgress.completed();
        if (courseProgressResult.unavailable()) {
            missing.add(new MissingRequirementDto(
                    "COURSE_PROGRESS_UNAVAILABLE",
                    "Chưa kiểm tra được tiến độ khóa học",
                    "Certificate service chưa lấy được tiến độ published course snapshot."));
        } else if (!requiredItemsEligible) {
            int missingCount = courseProgress == null || courseProgress.missingRequirements() == null
                    ? 0
                    : courseProgress.missingRequirements().size();
            missing.add(new MissingRequirementDto(
                    "REQUIRED_ITEMS_INCOMPLETE",
                    "Còn thiếu mục bắt buộc",
                    missingCount > 0
                            ? "Learner còn " + missingCount + " mục bắt buộc chưa hoàn thành."
                            : "Learner chưa hoàn thành mọi mục bắt buộc của khóa học."));
        }

        FinalGradeResponse finalGrade = finalGradeResult.value();
        boolean gradeFinalized = finalGrade != null && "FINALIZED".equalsIgnoreCase(finalGrade.status());
        boolean gradeEligible = gradeFinalized && finalGrade.passed();
        if (finalGradeResult.unavailable()) {
            missing.add(new MissingRequirementDto(
                    "FINAL_GRADE_UNAVAILABLE",
                    "Chưa kiểm tra được điểm cuối khóa",
                    "Certificate service chưa lấy được final grade từ gradebook."));
        } else if (!gradeFinalized) {
            missing.add(new MissingRequirementDto(
                    "FINAL_GRADE_NOT_FINALIZED",
                    "Chưa chốt điểm cuối khóa",
                    "Instructor cần finalize final grade trước khi cấp chứng chỉ."));
        } else if (!finalGrade.passed()) {
            missing.add(new MissingRequirementDto(
                    "GRADE_THRESHOLD_NOT_MET",
                    "Chưa đạt ngưỡng điểm",
                    "Final grade chưa đạt ngưỡng pass của khóa học."));
        }

        boolean eligible = completionEligible && requiredItemsEligible && gradeEligible && !dependencyUnavailable;
        return new CertificateEligibilityDto(
                generatedAt,
                courseId.toString(),
                studentId,
                eligible,
                eligibilityStatus(eligible, completionEligible, requiredItemsEligible, gradeFinalized, gradeEligible,
                        dependencyUnavailable),
                completionEligible,
                gradeEligible,
                requiredItemsEligible,
                false,
                finalGrade == null ? null : finalGrade.finalScore(),
                finalGrade == null ? null : finalGrade.passThreshold(),
                finalGrade == null ? null : finalGrade.status(),
                null,
                null,
                null,
                missing);
    }

    private CourseAccessResponse fetchEnrollment(String studentId, UUID courseId) {
        DependencyResult<CourseAccessResponse> result = readEnrollment(studentId, courseId);
        if (result.unavailable()) {
            throw new BadRequestException("Unable to verify completed enrollment for certificate");
        }
        return result.value();
    }

    private FinalGradeResponse fetchFinalGrade(String studentId, UUID courseId) {
        DependencyResult<FinalGradeResponse> result = readFinalGrade(studentId, courseId);
        if (result.unavailable()) {
            throw new BadRequestException("Unable to verify finalized grade for certificate");
        }
        return result.value();
    }

    private CourseProgressResponse fetchCourseProgress(String studentId, UUID courseId) {
        DependencyResult<CourseProgressResponse> result = readCourseProgress(studentId, courseId);
        if (result.unavailable()) {
            throw new BadRequestException("Unable to verify course progress for certificate");
        }
        return result.value();
    }

    private DependencyResult<CourseAccessResponse> readEnrollment(String studentId, UUID courseId) {
        try {
            return new DependencyResult<>(enrollmentClient.get()
                    .uri(uri -> uri.path("/internal/enrollments/access")
                            .queryParam("courseId", courseId)
                            .queryParam("studentId", studentId)
                            .build())
                    .headers(internalJwt::applyServiceToken)
                    .retrieve()
                    .body(CourseAccessResponse.class), false);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                return new DependencyResult<>(null, false);
            }
            return new DependencyResult<>(null, true);
        } catch (RestClientException ex) {
            return new DependencyResult<>(null, true);
        }
    }

    private DependencyResult<FinalGradeResponse> readFinalGrade(String studentId, UUID courseId) {
        try {
            return new DependencyResult<>(gradebookClient.get()
                    .uri("/internal/gradebook/courses/{courseId}/students/{studentId}/final-grade/internal",
                            courseId, studentId)
                    .headers(internalJwt::applyServiceToken)
                    .retrieve()
                    .body(FinalGradeResponse.class), false);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                return new DependencyResult<>(null, false);
            }
            return new DependencyResult<>(null, true);
        } catch (RestClientException ex) {
            return new DependencyResult<>(null, true);
        }
    }

    private DependencyResult<CourseProgressResponse> readCourseProgress(String studentId, UUID courseId) {
        try {
            return new DependencyResult<>(courseClient.get()
                    .uri(uri -> uri.path("/internal/courses/{courseId}/modules/progress/internal")
                            .queryParam("studentId", studentId)
                            .build(courseId))
                    .headers(internalJwt::applyServiceToken)
                    .retrieve()
                    .body(CourseProgressResponse.class), false);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                return new DependencyResult<>(null, false);
            }
            return new DependencyResult<>(null, true);
        } catch (RestClientException ex) {
            return new DependencyResult<>(null, true);
        }
    }

    private String eligibilityStatus(boolean eligible, boolean completionEligible, boolean requiredItemsEligible,
                                     boolean gradeFinalized, boolean gradeEligible, boolean dependencyUnavailable) {
        if (dependencyUnavailable) {
            return "ELIGIBILITY_UNAVAILABLE";
        }
        if (eligible) {
            return "ELIGIBLE";
        }
        if (!requiredItemsEligible) {
            return "REQUIRED_ITEMS_INCOMPLETE";
        }
        if (!completionEligible) {
            return "COURSE_NOT_COMPLETED";
        }
        if (!gradeFinalized) {
            return "FINAL_GRADE_NOT_FINALIZED";
        }
        if (!gradeEligible) {
            return "GRADE_THRESHOLD_NOT_MET";
        }
        return "NOT_ELIGIBLE";
    }

    private CertificateEligibilityDto unavailable(Instant generatedAt, String studentId, UUID courseId, String detail) {
        return new CertificateEligibilityDto(
                generatedAt,
                courseId.toString(),
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
                List.of(new MissingRequirementDto(
                        "CERTIFICATE_ELIGIBILITY_UNAVAILABLE",
                        "Chưa kiểm tra được điều kiện chứng chỉ",
                        detail)));
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
            BigDecimal passThreshold,
            String status,
            String finalizedBy,
            java.time.Instant finalizedAt
    ) {
    }

    public record CourseProgressResponse(
            String courseId,
            String studentId,
            int totalRequiredItems,
            int completedRequiredItems,
            int percentComplete,
            boolean completed,
            List<CourseProgressMissingRequirementDto> missingRequirements
    ) {
    }

    public record CourseProgressMissingRequirementDto(
            String itemId,
            String moduleId,
            String itemType,
            String title
    ) {
    }

    private record DependencyResult<T>(T value, boolean unavailable) {
    }
}
