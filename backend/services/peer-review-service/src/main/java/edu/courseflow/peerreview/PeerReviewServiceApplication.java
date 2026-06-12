package edu.courseflow.peerreview;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class PeerReviewServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(PeerReviewServiceApplication.class, args);
    }
}
