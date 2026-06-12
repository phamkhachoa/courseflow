package edu.courseflow.quiz;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class QuizServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(QuizServiceApplication.class, args);
    }
}
