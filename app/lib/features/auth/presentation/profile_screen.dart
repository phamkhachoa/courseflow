import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../application/auth_controller.dart';

/// Profile / account tab: shows the signed-in user and links to feature areas
/// that don't warrant their own bottom-nav tab.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(AppTheme.pagePadding),
        children: [
          if (user != null) ...[
            CircleAvatar(
              radius: 36,
              backgroundImage: user.avatarUrl == null || user.avatarUrl!.isEmpty
                  ? null
                  : NetworkImage(user.avatarUrl!),
              child: user.avatarUrl == null || user.avatarUrl!.isEmpty
                  ? Text(
                      user.fullName.isNotEmpty
                          ? user.fullName[0].toUpperCase()
                          : '?',
                      style: theme.textTheme.headlineMedium,
                    )
                  : null,
            ),
            const SizedBox(height: AppTheme.gap),
            Center(
                child: Text(user.fullName,
                    style: theme.textTheme.titleLarge)),
            Center(
              child: Text(user.email,
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline)),
            ),
            Center(child: Chip(label: Text(user.role))),
            const SizedBox(height: 24),
          ],
          const Divider(),
          _NavTile(
            icon: Icons.campaign_outlined,
            label: 'Announcements',
            onTap: () => context.push('/announcements'),
          ),
          _NavTile(
            icon: Icons.event_outlined,
            label: 'Upcoming deadlines',
            onTap: () => context.push('/deadlines'),
          ),
          _NavTile(
            icon: Icons.forum_outlined,
            label: 'Discussions',
            onTap: () => context.push('/discussions'),
          ),
          _NavTile(
            icon: Icons.rate_review_outlined,
            label: 'Peer review',
            onTap: () => context.push('/peer-review'),
          ),
          _NavTile(
            icon: Icons.workspace_premium_outlined,
            label: 'Certificates',
            onTap: () => context.push('/certificates'),
          ),
          _NavTile(
            icon: Icons.collections_bookmark_outlined,
            label: 'Portfolio',
            onTap: () => context.push('/portfolio'),
          ),
          const Divider(),
          _NavTile(
            icon: Icons.logout,
            label: 'Sign out',
            destructive: true,
            onTap: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.destructive = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final color =
        destructive ? Theme.of(context).colorScheme.error : null;
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(label, style: TextStyle(color: color)),
      trailing: destructive ? null : const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
