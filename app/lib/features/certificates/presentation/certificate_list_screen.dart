import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/certificate_repository.dart';
import '../domain/certificate_models.dart';

class CertificateListScreen extends ConsumerWidget {
  const CertificateListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final certificates = ref.watch(myCertificatesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Certificates')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(myCertificatesProvider.future),
        child: AsyncValueView<List<Certificate>>(
          value: certificates,
          onRetry: () => ref.invalidate(myCertificatesProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'Complete a course to earn a certificate.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) =>
                _CertificateCard(certificate: items[index]),
          ),
        ),
      ),
    );
  }
}

class _CertificateCard extends StatelessWidget {
  const _CertificateCard({required this.certificate});

  final Certificate certificate;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.workspace_premium_outlined,
                size: 40, color: theme.colorScheme.primary),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(certificate.courseTitle,
                      style: theme.textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(
                    'Code: ${certificate.verificationCode}',
                    style: theme.textTheme.bodySmall
                        ?.copyWith(color: theme.colorScheme.outline),
                  ),
                  if (certificate.issuedAt != null)
                    Text(
                      'Issued ${certificate.issuedAt!.label}',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: theme.colorScheme.outline),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
