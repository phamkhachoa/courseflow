package edu.courseflow.deadline;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class DeadlineServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeadlineServiceApplication.class, args);
    }
}
