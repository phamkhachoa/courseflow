/// Generic media asset from `GET /v1/media/assets`.
enum MediaKind { video, document, audio, image, other }

class MediaAsset {
  const MediaAsset({
    required this.id,
    required this.title,
    required this.kind,
    required this.url,
    required this.durationSeconds,
  });

  final String id;
  final String title;
  final MediaKind kind;
  final String url;

  /// For video/audio; 0 when not applicable.
  final int durationSeconds;

  factory MediaAsset.fromJson(Map<String, dynamic> json) => MediaAsset(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        kind: _kind(json['type'] as String? ?? json['kind'] as String?),
        url: json['url'] as String? ?? '',
        durationSeconds: (json['durationSeconds'] as num?)?.toInt() ?? 0,
      );

  static MediaKind _kind(String? raw) => switch (raw?.toUpperCase()) {
        'VIDEO' => MediaKind.video,
        'DOCUMENT' || 'PDF' || 'DOC' => MediaKind.document,
        'AUDIO' => MediaKind.audio,
        'IMAGE' => MediaKind.image,
        _ => MediaKind.other,
      };
}
