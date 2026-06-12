/// Portfolio evidence item, from
/// `GET /v1/portfolios/students/{studentId}/evidence`.
class PortfolioEvidence {
  const PortfolioEvidence({
    required this.id,
    required this.title,
    required this.description,
    required this.tag,
    required this.createdAt,
  });

  final String id;
  final String title;
  final String description;
  final String tag;
  final DateTime? createdAt;

  factory PortfolioEvidence.fromJson(Map<String, dynamic> json) =>
      PortfolioEvidence(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        description: json['description'] as String? ?? '',
        tag: json['tag'] as String? ?? 'GENERAL',
        createdAt: json['createdAt'] is String
            ? DateTime.tryParse(json['createdAt'] as String)
            : null,
      );
}
