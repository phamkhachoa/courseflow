package edu.courseflow.outboxrelay;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@ConfigurationPropertiesScan
@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class OutboxRelayApplication {
    public static void main(String[] args) {
        SpringApplication.run(OutboxRelayApplication.class, args);
    }
}
