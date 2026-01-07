import { Pressable, PressableProps, StyleProp, ViewStyle, ActivityIndicator } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { ColorValue } from 'react-native';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends Omit<PressableProps, 'style'> {
  children: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<ViewStyle>;
}

const sizeStyles: Record<ButtonSize, ViewStyle> = {
  sm: { paddingHorizontal: 12, paddingVertical: 8, minHeight: 36 },
  md: { paddingHorizontal: 16, paddingVertical: 12, minHeight: 44 },
  lg: { paddingHorizontal: 24, paddingVertical: 16, minHeight: 56 },
};

const textSizeMap: Record<ButtonSize, 'caption' | 'bodySm' | 'body'> = {
  sm: 'caption',
  md: 'bodySm',
  lg: 'body',
};

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth,
  loading,
  disabled,
  style,
  textStyle,
  ...props
}: ButtonProps) {
  const theme = useTheme();
  const colors = theme.colors;

  const variantColors: Record<ButtonVariant, { background: ColorValue; foreground: ColorValue }> = {
    primary: { background: colors.primary, foreground: colors.primaryForeground },
    secondary: { background: colors.secondary, foreground: colors.secondaryForeground },
    ghost: { background: 'transparent', foreground: colors.foreground },
    danger: { background: colors.destructive, foreground: colors.destructiveForeground },
    success: { background: colors.success, foreground: colors.successForeground },
  };

  const { background, foreground } = variantColors[variant];

  return (
    <Pressable
      style={[
        {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: theme.spacing.sm,
          borderRadius: theme.radius.md,
          opacity: disabled || loading ? theme.opacity.disabled : 1,
          width: fullWidth ? '100%' : 'auto',
        },
        sizeStyles[size],
        { backgroundColor: background },
        style,
      ]}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={foreground} size="small" />
      ) : typeof children === 'string' ? (
        <Text
          variant={textSizeMap[size]}
          weight="semibold"
          style={[{ color: foreground }, textStyle]}
        >
          {children}
        </Text>
      ) : (
        children
      )}
    </Pressable>
  );
}

interface IconButtonProps extends Omit<PressableProps, 'style'> {
  icon: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function IconButton({ icon, variant = 'ghost', size = 'md', disabled, style, ...props }: IconButtonProps) {
  const theme = useTheme();
  const colors = theme.colors;

  const variantColors: Record<ButtonVariant, { background: ColorValue; foreground: ColorValue }> = {
    primary: { background: colors.primary, foreground: colors.primaryForeground },
    secondary: { background: colors.secondary, foreground: colors.secondaryForeground },
    ghost: { background: 'transparent', foreground: colors.foreground },
    danger: { background: colors.destructive, foreground: colors.destructiveForeground },
    success: { background: colors.success, foreground: colors.successForeground },
  };

  const { background, foreground } = variantColors[variant];

  const iconSizeMap: Record<ButtonSize, number> = {
    sm: theme.iconSize.sm,
    md: theme.iconSize.md,
    lg: theme.iconSize.lg,
  };

  return (
    <Pressable
      style={[
        {
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: theme.radius.md,
          opacity: disabled ? theme.opacity.disabled : 1,
        },
        { width: iconSizeMap[size] + theme.spacing.md, height: iconSizeMap[size] + theme.spacing.md },
        { backgroundColor: background },
        style,
      ]}
      disabled={disabled}
      {...props}
    >
      {icon}
    </Pressable>
  );
}

export default Button;
