package edu.courseflow.announcement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class AnnouncementServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AnnouncementServiceApplication.class, args);
    }
}
