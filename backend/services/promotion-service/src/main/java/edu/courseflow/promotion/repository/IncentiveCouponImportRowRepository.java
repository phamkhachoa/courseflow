package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCouponImportRow;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncentiveCouponImportRowRepository extends JpaRepository<IncentiveCouponImportRow, UUID> {

    long countByBatchId(UUID batchId);

    long countByBatchIdAndRowStatus(UUID batchId, String rowStatus);

    List<IncentiveCouponImportRow> findByBatchIdOrderByRowNumber(UUID batchId);

    List<IncentiveCouponImportRow> findByBatchIdAndRowStatusOrderByRowNumber(UUID batchId, String rowStatus);
}
