package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class EnrollmentMembershipClientTest {

    private static final CurrentUser LEARNER_WITH_STAFF_ROLE = new CurrentUser(
            4L,
            "learner@courseflow.local",
            "INSTRUCTOR",
            Set.of("INSTRUCTOR", "STUDENT"));

    private RestClient.Builder restClientBuilder;
    private MockRestServiceServer enrollmentServer;

    @BeforeEach
    void setUp() {
        restClientBuilder = RestClient.builder();
        enrollmentServer = MockRestServiceServer.bindTo(restClientBuilder).build();
    }

    @Test
    void listLearnerEnrollmentsUsesDedicatedMembershipEndpoint() {
        EnrollmentMembershipClient client = new EnrollmentMembershipClient(
                restClientBuilder.baseUrl("http://enrollment.test").build(),
                internalJwt());
        enrollmentServer.expect(requestTo("http://enrollment.test/internal/learner-memberships?studentId=4"))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header(HttpHeaders.AUTHORIZATION, startsWith("Bearer ")))
                .andExpect(header(GatewayHeaders.INTERNAL_AUTHORIZATION, startsWith("Bearer ")))
                .andExpect(header(GatewayHeaders.USER_ID, "4"))
                .andRespond(withSuccess("""
                        [
                          {"id":"1","studentId":"4","courseId":"30000000-0000-0000-0000-000000000001","status":"ACTIVE"},
                          {"id":"2","studentId":"4","courseId":"30000000-0000-0000-0000-000000000002","status":"DROPPED"},
                          {"id":"3","studentId":"4","courseId":"30000000-0000-0000-0000-000000000003","status":"COMPLETED"}
                        ]
                        """, MediaType.APPLICATION_JSON));

        var rows = client.listLearnerEnrollments(LEARNER_WITH_STAFF_ROLE, 1);

        assertThat(rows).extracting(EnrollmentMembershipClient.EnrollmentSummary::courseId)
                .containsExactly("30000000-0000-0000-0000-000000000001");
        enrollmentServer.verify();
    }

    @Test
    void listLearnerEnrollmentsWrapsEnrollmentLookupFailure() {
        EnrollmentMembershipClient client = new EnrollmentMembershipClient(
                restClientBuilder.baseUrl("http://enrollment.test").build(),
                internalJwt());
        enrollmentServer.expect(requestTo("http://enrollment.test/internal/learner-memberships?studentId=4"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withServerError());

        assertThatThrownBy(() -> client.listLearnerEnrollments(LEARNER_WITH_STAFF_ROLE, 8))
                .isInstanceOf(EnrollmentMembershipClient.EnrollmentMembershipUnavailableException.class)
                .hasMessageContaining("membership lookup is unavailable");

        enrollmentServer.verify();
    }

    private InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                "internal-jwt-secret-that-is-at-least-32-bytes",
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "course-service"));
    }
}
