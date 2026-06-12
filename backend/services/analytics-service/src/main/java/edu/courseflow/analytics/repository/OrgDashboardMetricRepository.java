package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.OrgDashboardMetric;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrgDashboardMetricRepository extends JpaRepository<OrgDashboardMetric, String> {
}
