package edu.courseflow.livesession;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class LiveSessionServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(LiveSessionServiceApplication.class, args);
    }
}
