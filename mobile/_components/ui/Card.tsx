import { View, ViewStyle, StyleProp, Pressable } from 'react-native';
import { useTheme } from './context';

interface CardProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  variant?: 'default' | 'elevated' | 'outlined';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({ children, style, variant = 'default', padding = 'md' }: CardProps) {
  const theme = useTheme();

  const paddingMap = {
    none: 0,
    sm: theme.spacing.sm,
    md: theme.spacing.md,
    lg: theme.spacing.lg,
  };

  return (
    <View
      style={[
        {
          borderRadius: theme.radius.lg,
          padding: paddingMap[padding],
        },
        variant === 'default' && { backgroundColor: theme.colors.card },
        variant === 'elevated' && {
          backgroundColor: theme.colors.card,
          ...theme.shadow.lg,
        },
        variant === 'outlined' && {
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderColor: theme.colors.border,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

interface CardBodyProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function CardBody({ children, style }: CardBodyProps) {
  return <View style={style}>{children}</View>;
}

interface CardPressableProps {
  children: React.ReactNode;
  onPress?: () => void;
  onPressIn?: () => void;
  onPressOut?: () => void;
  activeOpacity?: number;
  style?: StyleProp<ViewStyle>;
}

export function CardPressable({
  children,
  onPress,
  onPressIn,
  onPressOut,
  activeOpacity = 0.8,
  style,
  ...props
}: CardPressableProps) {
  const theme = useTheme();

  return (
    <Pressable
      onPress={onPress}
      onPressIn={onPressIn}
      onPressOut={onPressOut}
      style={({ pressed }) => [
        {
          borderRadius: theme.radius.lg,
          opacity: pressed ? activeOpacity : 1,
        },
        { backgroundColor: theme.colors.card },
        theme.shadow.sm,
        style,
      ]}
      {...props}
    >
      {children}
    </Pressable>
  );
}

export default Card;
