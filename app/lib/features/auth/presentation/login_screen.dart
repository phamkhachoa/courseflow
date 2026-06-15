import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../application/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _submitting = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(authControllerProvider.notifier).login();
      // Router redirect handles navigation on auth state change.
    } on ApiException catch (e) {
      setState(() => _error = _friendly(e));
    } catch (_) {
      setState(() => _error = 'Unexpected error. Please try again.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _friendly(ApiException e) => switch (e.code) {
        'INVALID_CREDENTIALS' => 'Incorrect email or password.',
        'NETWORK_UNAVAILABLE' =>
          'Cannot reach CourseFlow. Check your connection.',
        _ => e.message,
      };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.school_outlined,
                      size: 56, color: theme.colorScheme.primary),
                  const SizedBox(height: AppTheme.gap),
                  Text('CourseFlow',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineSmall),
                  const SizedBox(height: 4),
                  Text(
                    'Continue with Keycloak SSO',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(color: theme.colorScheme.outline),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: AppTheme.gap),
                    Text(_error!,
                        style: TextStyle(color: theme.colorScheme.error)),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Continue with Keycloak'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
