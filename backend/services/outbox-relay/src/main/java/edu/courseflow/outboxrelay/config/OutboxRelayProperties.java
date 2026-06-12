package edu.courseflow.outboxrelay.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("courseflow.outbox")
public class OutboxRelayProperties {

    private long pollIntervalMs = 1000;
    private List<ServiceConfig> services = new ArrayList<>();

    public long getPollIntervalMs() { return pollIntervalMs; }
    public void setPollIntervalMs(long pollIntervalMs) { this.pollIntervalMs = pollIntervalMs; }

    public List<ServiceConfig> getServices() { return services; }
    public void setServices(List<ServiceConfig> services) { this.services = services; }

    public static class ServiceConfig {
        private String name;
        private String jdbcUrl;
        private String username;
        private String password;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getJdbcUrl() { return jdbcUrl; }
        public void setJdbcUrl(String jdbcUrl) { this.jdbcUrl = jdbcUrl; }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }
}
