import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../../courses/domain/course_models.dart';
import '../../courses/presentation/course_list_screen.dart';
import '../data/search_repository.dart';

/// Course search with a debounced query box. Results reuse [CourseCard].
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();
  Timer? _debounce;
  String _query = '';

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      if (mounted) setState(() => _query = value);
    });
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(courseSearchProvider(_query));
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          textInputAction: TextInputAction.search,
          onChanged: _onChanged,
          decoration: const InputDecoration(
            hintText: 'Search courses',
            border: InputBorder.none,
            prefixIcon: Icon(Icons.search),
          ),
        ),
      ),
      body: _query.trim().isEmpty
          ? const Center(child: Text('Type to search the catalog.'))
          : AsyncValueView<List<CourseSummary>>(
              value: results,
              onRetry: () => ref.invalidate(courseSearchProvider(_query)),
              isEmpty: (items) => items.isEmpty,
              emptyMessage: 'No courses match "$_query".',
              data: (items) => ListView.separated(
                padding: const EdgeInsets.all(AppTheme.pagePadding),
                itemCount: items.length,
                separatorBuilder: (_, __) =>
                    const SizedBox(height: AppTheme.gap),
                itemBuilder: (context, index) =>
                    CourseCard(course: items[index]),
              ),
            ),
    );
  }
}
