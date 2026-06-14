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

    @Test
    void routesDefaultToDiscoveryBackedUris() {
        Map<String, Object> root = loadGatewayApplicationYaml();
        List<Map<String, Object>> routes = routes(root);

        routes.forEach(route -> {
            String uri = String.valueOf(route.get("uri"));
            assertThat(uri)
                    .as("route %s should not hard-code an internal host port", route.get("id"))
                    .doesNotContain("localhost")
                    .doesNotContain(":808")
                    .doesNotContain(":809")
                    .doesNotContain(":810");
            assertThat(uri)
                    .as("route %s should default through service discovery", route.get("id"))
                    .contains("lb:");
        });
    }

    @Test
    void promotionRoutesUseGenericIncentivePaths() {
        Map<String, Object> root = loadGatewayApplicationYaml();
        List<Map<String, Object>> routes = routes(root);

        assertRoute(routes, "promotion-admin", "lb://promotion-service",
                "/api/admin/v1/incentives,/api/admin/v1/incentives/**");
        assertThat(routes).noneSatisfy(route -> assertThat(route.get("id")).isEqualTo("promotion-user"));
        List<String> allPredicates = routes.stream()
                .flatMap(route -> {
                    @SuppressWarnings("unchecked")
                    List<String> predicates = (List<String>) route.get("predicates");
                    return predicates.stream();
                })
                .toList();
        assertThat(allPredicates).noneMatch(predicate -> predicate.contains("/api/v1/incentives/evaluate"));
        assertThat(allPredicates).noneMatch(predicate -> predicate.contains("/api/v1/incentives/reservations"));
    }

    @Test
    void outboxAdminRouteUsesGenericOutboxPath() {
        Map<String, Object> root = loadGatewayApplicationYaml();
        List<Map<String, Object>> routes = routes(root);

        assertRoute(routes, "outbox-admin", "lb://outbox-relay",
                "/api/admin/v1/outbox,/api/admin/v1/outbox/**");
    }

    @Test
    void loyaltyAdminRouteUsesGenericLoyaltyPath() {
        Map<String, Object> root = loadGatewayApplicationYaml();
        List<Map<String, Object>> routes = routes(root);

        assertRoute(routes, "loyalty-admin", "lb://loyalty-service",
                "/api/admin/v1/loyalty,/api/admin/v1/loyalty/**");
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

    private static void assertRoute(List<Map<String, Object>> routes, String id, String uri, String path) {
        Map<String, Object> route = routes.stream()
                .filter(candidate -> id.equals(candidate.get("id")))
                .findFirst()
                .orElseThrow();
        assertThat(String.valueOf(route.get("uri"))).contains(uri);

        @SuppressWarnings("unchecked")
        List<String> predicates = (List<String>) route.get("predicates");
        @SuppressWarnings("unchecked")
        List<String> filters = (List<String>) route.get("filters");

        assertThat(predicates).anySatisfy(predicate -> assertThat(predicate).contains("Path=").contains(path));
        assertThat(filters).anySatisfy(filter -> assertThat(filter)
                .contains("RewritePath=/api")
                .contains("/internal/$\\{segment}"));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        assertThat(value).isInstanceOf(Map.class);
        return (Map<String, Object>) value;
    }
}
