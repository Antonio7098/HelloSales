import { Component, ErrorInfo, ReactNode } from 'react';
import { View, ViewStyle, StyleProp } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { Button } from './Button';
import { Icon } from './Icons';
import { Card } from './Card';
import { EmptyState } from './List';
import { SkeletonList } from './Skeleton';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  style?: StyleProp<ViewStyle>;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <DefaultErrorFallback
          error={this.state.error}
          onReset={() => this.setState({ hasError: false, error: undefined })}
          style={this.props.style}
        />
      );
    }

    return this.props.children;
  }
}

interface DefaultErrorFallbackProps {
  error?: Error;
  onReset: () => void;
  style?: StyleProp<ViewStyle>;
  title?: string;
  message?: string;
}

export function DefaultErrorFallback({
  error,
  onReset,
  style,
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
}: DefaultErrorFallbackProps) {
  const theme = useTheme();

  return (
    <View style={[{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: theme.spacing.xl }, style]}>
      <Icon
        name="Alert"
        size="xl"
        color={theme.colors.destructive}
        style={{ marginBottom: theme.spacing.md }}
      />
      <Text variant="h4" weight="semibold" style={{ marginBottom: theme.spacing.xs }}>
        {title}
      </Text>
      <Text variant="body" color="secondary" style={{ textAlign: 'center', marginBottom: theme.spacing.md }}>
        {message}
      </Text>
      {error && __DEV__ && (
        <Card style={{ width: '100%', marginBottom: theme.spacing.md }} variant="outlined">
          <Text variant="caption" color="error" style={{ marginBottom: theme.spacing.xs }}>
            {error.message}
          </Text>
        </Card>
      )}
      <Button onPress={onReset}>
        Try Again
      </Button>
    </View>
  );
}

interface AsyncErrorProps {
  error: Error | null;
  isLoading: boolean;
  children: ReactNode;
  onRetry?: () => void;
  loadingMessage?: string;
  style?: StyleProp<ViewStyle>;
}

export function AsyncErrorBoundary({
  error,
  isLoading,
  children,
  onRetry,
  loadingMessage = 'Loading...',
  style,
}: AsyncErrorProps) {
  const theme = useTheme();

  if (isLoading) {
    return (
      <View style={[{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: theme.spacing.xl }, style]}>
        <Text variant="body" color="secondary">{loadingMessage}</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: theme.spacing.xl }, style]}>
        <Icon
          name="Alert"
          size="xl"
          color={theme.colors.destructive}
          style={{ marginBottom: theme.spacing.md }}
        />
        <Text variant="h4" weight="semibold" style={{ marginBottom: theme.spacing.xs }}>
          Failed to load
        </Text>
        <Text variant="body" color="secondary" style={{ textAlign: 'center', marginBottom: theme.spacing.md }}>
          {error.message}
        </Text>
        {onRetry && (
          <Button onPress={onRetry}>
            Retry
          </Button>
        )}
      </View>
    );
  }

  return <>{children}</>;
}

interface DataListProps<T> {
  data: T[];
  isLoading: boolean;
  error: Error | null;
  onRetry?: () => void;
  renderItem: (item: T, index: number) => ReactNode;
  keyExtractor: (item: T, index: number) => string;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  loadingSkeleton?: ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function DataList<T>({
  data,
  isLoading,
  error,
  onRetry,
  renderItem,
  keyExtractor,
  emptyTitle = 'No data',
  emptyDescription,
  emptyAction,
  loadingSkeleton,
  style,
}: DataListProps<T>) {
  if (isLoading) {
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
    <View style={style}>
      {data.map((item, index) => (
        <View key={keyExtractor(item, index)}>
          {renderItem(item, index)}
        </View>
      ))}
    </View>
  );
}

export default ErrorBoundary;
