package edu.courseflow.course.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.LearningDtos.LearnerNextActionDto;
import edu.courseflow.course.service.LearnerNextActionService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LearnerNextActionController {

    private final LearnerNextActionService nextActions;

    public LearnerNextActionController(LearnerNextActionService nextActions) {
        this.nextActions = nextActions;
    }

    @GetMapping("/internal/learning/next-action")
    public LearnerNextActionDto nextAction(CurrentUser user) {
        return nextActions.nextAction(user);
    }
}
