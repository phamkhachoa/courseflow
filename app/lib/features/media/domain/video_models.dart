class VideoAsset {
  const VideoAsset({
    required this.id,
    required this.title,
    required this.status,
    required this.renditions,
    required this.captions,
  });

  final String id;
  final String title;
  final String status;
  final List<VideoRendition> renditions;
  final List<VideoCaption> captions;

  factory VideoAsset.fromJson(Map<String, dynamic> json) => VideoAsset(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        status: json['status'] as String? ?? '',
        renditions: (json['renditions'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(VideoRendition.fromJson)
            .toList(growable: false),
        captions: (json['captions'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(VideoCaption.fromJson)
            .toList(growable: false),
      );
}

class VideoRendition {
  const VideoRendition({
    required this.id,
    required this.protocol,
    required this.label,
    required this.storageKey,
  });

  final String id;
  final String protocol;
  final String label;
  final String storageKey;

  factory VideoRendition.fromJson(Map<String, dynamic> json) => VideoRendition(
        id: json['id'] as String? ?? '',
        protocol: json['protocol'] as String? ?? '',
        label: json['label'] as String? ?? '',
        storageKey: json['storageKey'] as String? ?? '',
      );
}

class VideoCaption {
  const VideoCaption({
    required this.id,
    required this.language,
    required this.kind,
    required this.storageKey,
  });

  final String id;
  final String language;
  final String kind;
  final String storageKey;

  factory VideoCaption.fromJson(Map<String, dynamic> json) => VideoCaption(
        id: json['id'] as String? ?? '',
        language: json['language'] as String? ?? '',
        kind: json['kind'] as String? ?? '',
        storageKey: json['storageKey'] as String? ?? '',
      );
}

class PlaybackUrl {
  const PlaybackUrl({required this.videoId, required this.url, required this.expiresAt});

  final String videoId;
  final String url;
  final String expiresAt;

  factory PlaybackUrl.fromJson(Map<String, dynamic> json) => PlaybackUrl(
        videoId: json['videoId'] as String? ?? '',
        url: json['url'] as String? ?? '',
        expiresAt: json['expiresAt'] as String? ?? '',
      );
}

class VideoProgress {
  const VideoProgress({
    required this.videoId,
    required this.userId,
    required this.positionSeconds,
    required this.completed,
    this.durationSeconds,
  });

  final String videoId;
  final String userId;
  final int positionSeconds;
  final bool completed;
  final int? durationSeconds;

  factory VideoProgress.fromJson(Map<String, dynamic> json) => VideoProgress(
        videoId: json['videoId'] as String? ?? '',
        userId: json['userId'] as String? ?? '',
        positionSeconds: json['positionSeconds'] as int? ?? 0,
        completed: json['completed'] as bool? ?? false,
        durationSeconds: json['durationSeconds'] as int?,
      );
}
