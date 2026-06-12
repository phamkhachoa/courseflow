class LiveSession {
  const LiveSession({
    required this.id,
    required this.courseId,
    required this.title,
    required this.hostId,
    required this.scheduledStart,
    required this.status,
    this.description,
    this.scheduledEnd,
    this.capacity,
  });

  final String id;
  final String courseId;
  final String title;
  final String hostId;
  final String scheduledStart;
  final String status;
  final String? description;
  final String? scheduledEnd;
  final int? capacity;

  factory LiveSession.fromJson(Map<String, dynamic> json) => LiveSession(
        id: json['id'] as String? ?? '',
        courseId: json['courseId'] as String? ?? '',
        title: json['title'] as String? ?? '',
        hostId: json['hostId'] as String? ?? '',
        scheduledStart: json['scheduledStart'] as String? ?? '',
        status: json['status'] as String? ?? '',
        description: json['description'] as String?,
        scheduledEnd: json['scheduledEnd'] as String?,
        capacity: json['capacity'] as int?,
      );
}

class JoinInfo {
  const JoinInfo({
    required this.sessionId,
    required this.userId,
    required this.joinUrl,
    required this.status,
  });

  final String sessionId;
  final String userId;
  final String joinUrl;
  final String status;

  factory JoinInfo.fromJson(Map<String, dynamic> json) => JoinInfo(
        sessionId: json['sessionId'] as String? ?? '',
        userId: json['userId'] as String? ?? '',
        joinUrl: json['joinUrl'] as String? ?? '',
        status: json['status'] as String? ?? '',
      );
}

class Registration {
  const Registration({
    required this.id,
    required this.sessionId,
    required this.userId,
    required this.attended,
  });

  final String id;
  final String sessionId;
  final String userId;
  final bool attended;

  factory Registration.fromJson(Map<String, dynamic> json) => Registration(
        id: json['id'] as String? ?? '',
        sessionId: json['sessionId'] as String? ?? '',
        userId: json['userId'] as String? ?? '',
        attended: json['attended'] as bool? ?? false,
      );
}
