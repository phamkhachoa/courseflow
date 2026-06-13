package edu.courseflow.notification.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class EnrollmentRosterClientTest {

    private static final String COURSE_ID = "30000000-0000-0000-0000-000000000001";

    private RestClient.Builder restClientBuilder;
    private MockRestServiceServer enrollmentServer;

    @BeforeEach
    void setUp() {
        restClientBuilder = RestClient.builder();
        enrollmentServer = MockRestServiceServer.bindTo(restClientBuilder).build();
    }

    @Test
    void activeStudentIdsCallsRosterEndpointWithInternalJwt() {
        EnrollmentRosterClient client = new EnrollmentRosterClient(
                restClientBuilder, "http://enrollment.test", internalJwt());
        enrollmentServer.expect(requestTo("http://enrollment.test/internal/enrollments/roster?courseId=" + COURSE_ID))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header(HttpHeaders.AUTHORIZATION, startsWith("Bearer ")))
                .andExpect(header(GatewayHeaders.INTERNAL_AUTHORIZATION, startsWith("Bearer ")))
                .andRespond(withSuccess("""
                        [
                          {"studentId":"4","status":"ACTIVE"},
                          {"studentId":"5","status":"DROPPED"},
                          {"studentId":"4","status":"ACTIVE"}
                        ]
                        """, MediaType.APPLICATION_JSON));

        List<String> recipients = client.activeStudentIds(COURSE_ID);

        assertThat(recipients).containsExactly("4");
        enrollmentServer.verify();
    }

    private InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                "internal-jwt-secret-that-is-at-least-32-bytes",
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "notification-service"));
    }
}
