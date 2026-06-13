package edu.courseflow.accesscontrol.repository;

import edu.courseflow.accesscontrol.model.ExternalIdentityLink;
import java.util.Optional;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ExternalIdentityLinkRepository extends JpaRepository<ExternalIdentityLink, Long> {

    @EntityGraph(attributePaths = "user")
    @Query("""
            select link from ExternalIdentityLink link
            where link.issuer = :issuer
              and link.subject = :subject
              and link.status = 'ACTIVE'
            """)
    Optional<ExternalIdentityLink> findActiveByIssuerAndSubject(@Param("issuer") String issuer,
            @Param("subject") String subject);

    @EntityGraph(attributePaths = "user")
    Optional<ExternalIdentityLink> findByIssuerAndSubject(String issuer, String subject);

    @EntityGraph(attributePaths = "user")
    Optional<ExternalIdentityLink> findFirstByUser_IdAndStatusOrderByIdDesc(Long userId, String status);
}
