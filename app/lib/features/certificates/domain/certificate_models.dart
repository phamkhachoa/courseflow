/// Issued certificate, from the learner's certificate list.
class Certificate {
  const Certificate({
    required this.id,
    required this.courseTitle,
    required this.verificationCode,
    required this.issuedAt,
  });

  final String id;
  final String courseTitle;
  final String verificationCode;
  final DateTime? issuedAt;

  factory Certificate.fromJson(Map<String, dynamic> json) => Certificate(
        id: json['id'] as String? ?? json['certificateId'] as String? ?? '',
        courseTitle: json['courseTitle'] as String? ??
            json['courseName'] as String? ??
            _courseFallback(json['courseId'] as String?),
        verificationCode: json['verificationCode'] as String? ??
            json['code'] as String? ??
            '',
        issuedAt: json['issuedAt'] is String
            ? DateTime.tryParse(json['issuedAt'] as String)
            : null,
      );

  static String _courseFallback(String? courseId) =>
      courseId == null || courseId.isEmpty ? '' : 'Course $courseId';
}

/// Public verification result from `GET /v1/certificates/verify/{code}`.
///
/// Mirrors certificate-service `PublicCertificateVerificationDto`: the public
/// endpoint is PII-free, so it carries no holder name or final grade — only
/// enough to confirm a certificate is genuine and current.
class CertificateVerification {
  const CertificateVerification({
    required this.valid,
    required this.verificationCode,
    required this.courseId,
    required this.status,
    required this.issuedAt,
  });

  final bool valid;
  final String verificationCode;
  final String courseId;
  final String status;
  final DateTime? issuedAt;

  factory CertificateVerification.fromJson(Map<String, dynamic> json) =>
      CertificateVerification(
        valid: json['valid'] as bool? ?? false,
        verificationCode: json['verificationCode'] as String? ?? '',
        courseId: json['courseId'] as String? ?? '',
        status: json['status'] as String? ?? '',
        issuedAt: json['issuedAt'] is String
            ? DateTime.tryParse(json['issuedAt'] as String)
            : null,
      );
}
