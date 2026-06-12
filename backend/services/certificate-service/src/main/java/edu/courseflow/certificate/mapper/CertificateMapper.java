package edu.courseflow.certificate.mapper;

import edu.courseflow.certificate.dto.CertificateVerificationDto;
import edu.courseflow.certificate.dto.PublicCertificateVerificationDto;
import edu.courseflow.certificate.model.Certificate;
import edu.courseflow.certificate.model.CertificateVerification;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface CertificateMapper {

    @Mapping(target = "certificateId", source = "certificate.id")
    @Mapping(target = "verificationCode", source = "verification.verificationCode")
    @Mapping(target = "publicSlug", source = "verification.publicSlug")
    @Mapping(target = "studentId", source = "certificate.studentId")
    @Mapping(target = "courseId", source = "certificate.courseId")
    @Mapping(target = "finalGrade", source = "certificate.finalGrade")
    @Mapping(target = "status", source = "certificate.status")
    @Mapping(target = "issuedAt", source = "certificate.issuedAt")
    CertificateVerificationDto toDto(Certificate certificate, CertificateVerification verification);

    @Mapping(target = "valid", source = "valid")
    PublicCertificateVerificationDto toPublicDto(CertificateVerificationDto dto, boolean valid);
}
