import { useCallback, useEffect, useRef, useState } from 'react';
import { View, ViewStyle, StyleProp, ScrollView, ScrollViewProps, ActivityIndicator } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { Button } from './Button';

interface PaginationOptions<T> {
  initialPage?: number;
  pageSize?: number;
  initialData?: T[];
}

interface PaginationState<T> {
  data: T[];
  page: number;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  error: Error | null;
  totalCount: number;
}

interface UsePaginationOptions<T> extends PaginationOptions<T> {
  fetchFn: (page: number, pageSize: number) => Promise<{ data: T[]; total: number }>;
  initialData?: T[];
}

export function usePagination<T>({
  initialPage = 1,
  pageSize = 20,
  fetchFn,
}: UsePaginationOptions<T>) {
  const [state, setState] = useState<PaginationState<T>>({
    data: [],
    page: initialPage,
    loading: false,
    loadingMore: false,
    hasMore: true,
    error: null,
    totalCount: 0,
  });

  const fetchData = useCallback(async (page: number, isLoadMore = false) => {
    if (isLoadMore && !state.hasMore) return;

    setState(prev => ({
      ...prev,
      [isLoadMore ? 'loadingMore' : 'loading']: true,
      error: null,
    }));

    try {
      const result = await fetchFn(page, pageSize);
      setState(prev => ({
        ...prev,
        data: isLoadMore ? [...prev.data, ...result.data] : result.data,
        page,
        loading: false,
        loadingMore: false,
        hasMore: prev.data.length + result.data.length < result.total,
        totalCount: result.total,
        error: null,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        loadingMore: false,
        error: error instanceof Error ? error : new Error('Failed to fetch data'),
      }));
    }
  }, [fetchFn, pageSize, state.hasMore]);

  const loadMore = useCallback(() => {
    if (!state.loadingMore && state.hasMore) {
      fetchData(state.page + 1, true);
    }
  }, [fetchData, state.page, state.loadingMore, state.hasMore]);

  const refresh = useCallback(() => {
    fetchData(initialPage, false);
  }, [fetchData, initialPage]);

  const reset = useCallback(() => {
    setState({
      data: [],
      page: initialPage,
      loading: false,
      loadingMore: false,
      hasMore: true,
      error: null,
      totalCount: 0,
    });
    fetchData(initialPage, false);
  }, [fetchData, initialPage]);

  useEffect(() => {
    fetchData(initialPage, false);
  }, [fetchData, initialPage]);

  return {
    ...state,
    loadMore,
    refresh,
    reset,
    canLoadMore: state.hasMore && !state.loadingMore && !state.loading,
  };
}

interface PaginationControlsProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  style?: StyleProp<ViewStyle>;
}

export function PaginationControls({
  page,
  totalPages,
  onPageChange,
  style,
}: PaginationControlsProps) {
  const theme = useTheme();

  if (totalPages <= 1) return null;

  const pages = getPageNumbers(page, totalPages);

  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: theme.spacing.md, gap: theme.spacing.xs }, style]}>
      <Button
        variant="secondary"
        size="sm"
        disabled={page <= 1}
        onPress={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      {pages.map((p, index) =>
        p === '...' ? (
          <Text key={`ellipsis-${index}`} color="muted" style={{ paddingHorizontal: theme.spacing.xs }}>
            ...
          </Text>
        ) : (
          <Button
            key={p}
            variant={page === p ? 'primary' : 'secondary'}
            size="sm"
            onPress={() => onPageChange(p)}
          >
            {p}
          </Button>
        )
      )}
      <Button
        variant="secondary"
        size="sm"
        disabled={page >= totalPages}
        onPress={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </View>
  );
}

function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | '...')[] = [];

  if (current <= 3) {
    pages.push(1, 2, 3, 4, '...', total);
  } else if (current >= total - 2) {
    pages.push(1, '...', total - 3, total - 2, total - 1, total);
  } else {
    pages.push(1, '...', current - 1, current, current + 1, '...', total);
  }

  return pages;
}

interface InfiniteScrollProps<T> {
  data: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  keyExtractor: (item: T, index: number) => string;
  onLoadMore: () => void;
  loadingMore: boolean;
  hasMore: boolean;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  loadingSkeleton?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  contentContainerStyle?: StyleProp<ViewStyle>;
  showsVerticalScrollIndicator?: boolean;
  scrollEventThrottle?: number;
  onScroll?: ScrollViewProps['onScroll'];
}

export function InfiniteScroll<T>({
  data,
  renderItem,
  keyExtractor,
  onLoadMore,
  loadingMore,
  hasMore,
  loading = false,
  error = null,
  onRetry,
  emptyTitle = 'No data',
  emptyDescription,
  emptyAction,
  loadingSkeleton,
  style,
  contentContainerStyle,
  showsVerticalScrollIndicator = true,
  scrollEventThrottle = 16,
  onScroll,
}: InfiniteScrollProps<T>) {
  const theme = useTheme();
  const scrollViewRef = useRef<ScrollView>(null);

  const handleScroll = (event: any) => {
    onScroll?.(event);

    if (loadingMore || !hasMore || loading) return;

    const { layoutMeasurement, contentOffset, contentSize } = event.nativeEvent;
    const isNearBottom = layoutMeasurement.height + contentOffset.y >= contentSize.height - 100;

    if (isNearBottom) {
      onLoadMore();
    }
  };

  if (loading) {
    return loadingSkeleton || <SkeletonList count={5} style={style} />;
  }

  if (error) {
    return (
      <View style={style}>
        <EmptyState
          icon="Alert"
          title="Failed to load data"
          description={error.message}
          action={onRetry && <Button onPress={onRetry}>Retry</Button>}
        />
      </View>
    );
  }

  if (data.length === 0) {
    return (
      <View style={style}>
        <EmptyState
          icon="Package"
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
        />
      </View>
    );
  }

  return (
    <ScrollView
      ref={scrollViewRef}
      style={style}
      contentContainerStyle={contentContainerStyle}
      showsVerticalScrollIndicator={showsVerticalScrollIndicator}
      scrollEventThrottle={scrollEventThrottle}
      onScroll={handleScroll}
      keyboardShouldPersistTaps="handled"
    >
      {data.map((item, index) => (
        <View key={keyExtractor(item, index)}>
          {renderItem(item, index)}
        </View>
      ))}
      {hasMore && (
        <View style={{ padding: theme.spacing.md, alignItems: 'center' }}>
          <ActivityIndicator size="small" color={theme.colors.foreground} />
          <Text variant="caption" color="muted" style={{ marginTop: theme.spacing.xs }}>
            Loading more...
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

interface LoadMoreTriggerProps {
  onLoadMore: () => void;
  hasMore: boolean;
  loadingMore: boolean;
  style?: StyleProp<ViewStyle>;
}

export function LoadMoreTrigger({ onLoadMore, hasMore, loadingMore, style }: LoadMoreTriggerProps) {
  const theme = useTheme();

  if (!hasMore || loadingMore) return null;

  return (
    <View style={[{ padding: theme.spacing.md, alignItems: 'center' }, style]}>
      <Button variant="secondary" onPress={onLoadMore}>
        Load More
      </Button>
    </View>
  );
}

// All exports are already named exports above
