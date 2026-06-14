package edu.courseflow.outboxrelay.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.ClassPathResource;

class OutboxRelayPropertiesTest {

    @Test
    void defaultServiceListIncludesLoyaltyOutbox() throws IOException {
        StandardEnvironment environment = new StandardEnvironment();
        environment.getPropertySources().addFirst(new YamlPropertySourceLoader()
                .load("application", new ClassPathResource("application.yml"))
                .getFirst());
        OutboxRelayProperties properties = Binder.get(environment)
                .bind("courseflow.outbox", OutboxRelayProperties.class)
                .orElseThrow(() -> new AssertionError("courseflow.outbox properties must bind"));

        Map<String, OutboxRelayProperties.ServiceConfig> services = properties.getServices().stream()
                .collect(Collectors.toMap(OutboxRelayProperties.ServiceConfig::getName, Function.identity()));

        assertThat(services).containsKey("loyalty");
        assertThat(services.get("loyalty").getJdbcUrl()).contains("cf_loyalty");
    }
}
