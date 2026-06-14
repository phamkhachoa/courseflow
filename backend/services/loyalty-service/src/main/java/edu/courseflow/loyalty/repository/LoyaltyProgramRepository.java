package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyProgram;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyProgramRepository extends JpaRepository<LoyaltyProgram, UUID> {
    Optional<LoyaltyProgram> findByTenantIdAndApplicationIdAndProgramId(
            String tenantId, String applicationId, String programId);

    boolean existsByTenantIdAndApplicationIdAndProgramId(String tenantId, String applicationId, String programId);

    @Query("""
            select program
            from LoyaltyProgram program
            where (:tenantId is null or program.tenantId = :tenantId)
              and (:applicationId is null or program.applicationId = :applicationId)
              and (:programId is null or program.programId = :programId)
              and (:status is null or program.status = :status)
            order by program.createdAt desc
            """)
    List<LoyaltyProgram> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("status") String status,
            Pageable pageable);
}
