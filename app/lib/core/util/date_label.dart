/// Lightweight date formatting without pulling locale data. Good enough for
/// due dates and timestamps in lists.
extension DateLabel on DateTime {
  static const _months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  /// e.g. `7 Jun 2026, 14:05`.
  String get label {
    final h = hour.toString().padLeft(2, '0');
    final m = minute.toString().padLeft(2, '0');
    return '$day ${_months[month - 1]} $year, $h:$m';
  }

  /// Relative-ish label for due dates: `Overdue`, `Due today`, `in 3 days`.
  String dueLabel({DateTime? now}) {
    final ref = now ?? DateTime.now();
    final diff = difference(ref);
    if (diff.isNegative) return 'Overdue';
    if (diff.inHours < 24) return 'Due today';
    return 'in ${diff.inDays} day${diff.inDays == 1 ? '' : 's'}';
  }
}
