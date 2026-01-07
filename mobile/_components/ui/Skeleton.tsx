import { View, ViewStyle, StyleProp, Animated } from 'react-native';
import { useEffect, useRef } from 'react';
import { useTheme } from './context';

interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  borderRadius?: number;
  style?: StyleProp<ViewStyle>;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  width = '100%',
  height = 20,
  borderRadius = 4,
  style,
  animation = 'pulse',
}: SkeletonProps) {
  const theme = useTheme();
  const animatedValue = useRef(new Animated.Value(0));

  useEffect(() => {
    if (animation === 'none') return;

    const animationType = animation === 'pulse' ? 1000 : 1500;

    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(animatedValue.current, {
          toValue: 1,
          duration: animationType,
          useNativeDriver: true,
        }),
        Animated.timing(animatedValue.current, {
          toValue: 0,
          duration: animationType,
          useNativeDriver: true,
        }),
      ])
    );

    loop.start();

    return () => {
      loop.stop();
    };
  }, [animation]);

  const opacity = animatedValue.current.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.7],
  });

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius,
          backgroundColor: theme.colors.muted,
        },
        animation !== 'none' && { opacity },
        style,
      ]}
    />
  );
}

interface SkeletonTextProps {
  lines?: number;
  lineHeight?: number;
  lastLineWidth?: number | string;
  style?: StyleProp<ViewStyle>;
  animation?: 'pulse' | 'wave' | 'none';
}

export function SkeletonText({
  lines = 3,
  lineHeight = 16,
  lastLineWidth = '60%',
  style,
  animation = 'pulse',
}: SkeletonTextProps) {
  const theme = useTheme();

  return (
    <View style={style}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          width={index === lines - 1 ? lastLineWidth : '100%'}
          height={lineHeight}
          style={{ marginBottom: index < lines - 1 ? 8 : 0 }}
          animation={animation}
        />
      ))}
    </View>
  );
}

interface SkeletonCardProps {
  showAvatar?: boolean;
  showTitle?: boolean;
  showSubtitle?: boolean;
  showDescription?: boolean;
  lines?: number;
  style?: StyleProp<ViewStyle>;
}

export function SkeletonCard({
  showAvatar = true,
  showTitle = true,
  showSubtitle = true,
  showDescription = true,
  lines = 2,
  style,
}: SkeletonCardProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          padding: theme.spacing.md,
          backgroundColor: theme.colors.card,
          borderRadius: theme.radius.lg,
        },
        style,
      ]}
    >
      <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
        {showAvatar && (
          <Skeleton
            width={40}
            height={40}
            borderRadius={20}
            style={{ marginRight: theme.spacing.md, flexShrink: 0 }}
          />
        )}
        <View style={{ flex: 1 }}>
          {showTitle && (
            <Skeleton width="60%" height={16} style={{ marginBottom: theme.spacing.xs }} />
          )}
          {showSubtitle && (
            <Skeleton width="40%" height={12} style={{ marginBottom: theme.spacing.xs }} />
          )}
        </View>
      </View>
      {showDescription && (
        <View style={{ marginTop: theme.spacing.md }}>
          <SkeletonText lines={lines} />
        </View>
      )}
    </View>
  );
}

interface SkeletonListProps {
  count?: number;
  showAvatar?: boolean;
  showTitle?: boolean;
  showSubtitle?: boolean;
  itemStyle?: StyleProp<ViewStyle>;
}

export function SkeletonList({
  count = 5,
  showAvatar = true,
  showTitle = true,
  showSubtitle = true,
  itemStyle,
}: SkeletonListProps) {
  const theme = useTheme();

  return (
    <View style={{ gap: theme.spacing.sm }}>
      {Array.from({ length: count }).map((_, index) => (
        <View
          key={index}
          style={[
            {
              flexDirection: 'row',
              alignItems: 'center',
              padding: theme.spacing.md,
              backgroundColor: theme.colors.card,
              borderRadius: theme.radius.lg,
            },
            itemStyle,
          ]}
        >
          {showAvatar && (
            <Skeleton
              width={40}
              height={40}
              borderRadius={20}
              style={{ marginRight: theme.spacing.md, flexShrink: 0 }}
            />
          )}
          <View style={{ flex: 1 }}>
            {showTitle && (
              <Skeleton width="70%" height={16} style={{ marginBottom: theme.spacing.xs }} />
            )}
            {showSubtitle && (
              <Skeleton width="50%" height={12} />
            )}
          </View>
        </View>
      ))}
    </View>
  );
}

interface SkeletonStatsProps {
  count?: number;
  style?: StyleProp<ViewStyle>;
}

export function SkeletonStats({ count = 3, style }: SkeletonStatsProps) {
  const theme = useTheme();

  return (
    <View style={[{ flexDirection: 'row', gap: theme.spacing.sm }, style]}>
      {Array.from({ length: count }).map((_, index) => (
        <View
          key={index}
          style={{
            flex: 1,
            padding: theme.spacing.md,
            backgroundColor: theme.colors.card,
            borderRadius: theme.radius.lg,
          }}
        >
          <Skeleton width="40%" height={12} style={{ marginBottom: theme.spacing.xs }} />
          <Skeleton width="60%" height={24} />
        </View>
      ))}
    </View>
  );
}

export default Skeleton;
