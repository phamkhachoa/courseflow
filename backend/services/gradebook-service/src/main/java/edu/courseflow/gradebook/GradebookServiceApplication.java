package edu.courseflow.gradebook;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class GradebookServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(GradebookServiceApplication.class, args);
    }
}
