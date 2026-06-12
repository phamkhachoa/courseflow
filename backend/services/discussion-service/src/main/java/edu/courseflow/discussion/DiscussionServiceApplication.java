package edu.courseflow.discussion;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class DiscussionServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DiscussionServiceApplication.class, args);
    }
}
