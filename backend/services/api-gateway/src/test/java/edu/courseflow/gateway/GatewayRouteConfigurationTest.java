package edu.courseflow.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.InputStream;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;

class GatewayRouteConfigurationTest {

    @Test
    void adminUserAssignmentsRouteIncludesExportActionPath() {
        Map<String, Object> root = loadGatewayApplicationYaml();
        List<Map<String, Object>> routes = routes(root);
        Map<String, Object> route = routes.stream()
                .filter(candidate -> "access-control-admin-user-assignments".equals(candidate.get("id")))
                .findFirst()
                .orElseThrow();

        @SuppressWarnings("unchecked")
        List<String> predicates = (List<String>) route.get("predicates");
        @SuppressWarnings("unchecked")
        List<String> filters = (List<String>) route.get("filters");

        assertThat(predicates).anySatisfy(predicate -> assertThat(predicate)
                .contains("Path=")
                .contains("/api/admin/v1/users/*/assignments")
                .contains("/api/admin/v1/users/*/assignments/**")
                .contains("/api/admin/v1/users/*/assignments:export"));
        assertThat(filters).anySatisfy(filter -> assertThat(filter)
                .contains("RewritePath=/api/admin/v1/(?<segment>users/.+), /internal/$\\{segment}"));
    }

    private static Map<String, Object> loadGatewayApplicationYaml() {
        InputStream input = GatewayRouteConfigurationTest.class.getClassLoader()
                .getResourceAsStream("application.yml");
        assertThat(input).as("api-gateway application.yml test resource").isNotNull();
        @SuppressWarnings("unchecked")
        Map<String, Object> root = new Yaml().load(input);
        return root;
    }

    private static List<Map<String, Object>> routes(Map<String, Object> root) {
        Map<String, Object> spring = map(root.get("spring"));
        Map<String, Object> cloud = map(spring.get("cloud"));
        Map<String, Object> gateway = map(cloud.get("gateway"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> routes = (List<Map<String, Object>>) gateway.get("routes");
        assertThat(routes).isNotEmpty();
        return routes;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        assertThat(value).isInstanceOf(Map.class);
        return (Map<String, Object>) value;
    }
}
