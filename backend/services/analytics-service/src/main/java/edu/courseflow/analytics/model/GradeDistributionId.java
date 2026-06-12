package edu.courseflow.analytics.model;

import java.io.Serializable;
import java.util.Objects;
import java.util.UUID;

public class GradeDistributionId implements Serializable {
    private UUID courseId;
    private String gradeBand;

    public GradeDistributionId() {
    }

    public GradeDistributionId(UUID courseId, String gradeBand) {
        this.courseId = courseId;
        this.gradeBand = gradeBand;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof GradeDistributionId that)) return false;
        return Objects.equals(courseId, that.courseId) && Objects.equals(gradeBand, that.gradeBand);
    }

    @Override
    public int hashCode() {
        return Objects.hash(courseId, gradeBand);
    }
}
