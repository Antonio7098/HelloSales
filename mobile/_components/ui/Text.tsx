import { Text as RNText, TextStyle, StyleProp } from 'react-native';
import { useTheme } from './context';

type TextVariant = 'display' | 'h1' | 'h2' | 'h3' | 'h4' | 'body' | 'bodySm' | 'caption' | 'badge';
type TextColor = 'primary' | 'secondary' | 'muted' | 'success' | 'warning' | 'error' | 'info';
type TextWeight = 'normal' | 'medium' | 'semibold' | 'bold';

interface TextProps {
  children: React.ReactNode;
  variant?: TextVariant;
  color?: TextColor;
  weight?: TextWeight;
  align?: 'left' | 'center' | 'right';
  truncate?: boolean;
  numberOfLines?: number;
  style?: StyleProp<TextStyle>;
  testID?: string;
}

const variantStyles: Record<TextVariant, TextStyle> = {
  display: { fontSize: 40, lineHeight: 48, letterSpacing: -0.5 },
  h1: { fontSize: 32, lineHeight: 40, letterSpacing: -0.25 },
  h2: { fontSize: 24, lineHeight: 32 },
  h3: { fontSize: 20, lineHeight: 28 },
  h4: { fontSize: 18, lineHeight: 24 },
  body: { fontSize: 16, lineHeight: 24 },
  bodySm: { fontSize: 14, lineHeight: 20 },
  caption: { fontSize: 12, lineHeight: 16 },
  badge: { fontSize: 11, lineHeight: 16, letterSpacing: 0.5, textTransform: 'uppercase' as const },
};

const colorStyles: Record<TextColor, TextStyle> = {
  primary: { color: '#F8FAFC' },
  secondary: { color: '#CBD5E1' },
  muted: { color: '#64748B' },
  success: { color: '#34D399' },
  warning: { color: '#FBBF24' },
  error: { color: '#F87171' },
  info: { color: '#38BDF8' },
};

export function Text({
  children,
  variant = 'body',
  color = 'primary',
  weight = 'normal',
  align = 'left',
  truncate,
  numberOfLines,
  style,
  testID,
}: TextProps) {
  const theme = useTheme();

  return (
    <RNText
      testID={testID}
      style={[
        variantStyles[variant],
        colorStyles[color],
        { fontWeight: weight, textAlign: align },
        truncate && { overflow: 'hidden' },
        style,
      ]}
      numberOfLines={truncate ? 1 : numberOfLines}
    >
      {children}
    </RNText>
  );
}

interface HeadingProps {
  children: React.ReactNode;
  level?: 1 | 2 | 3 | 4;
  color?: TextColor;
  align?: 'left' | 'center' | 'right';
  style?: StyleProp<TextStyle>;
}

export function Heading({ children, level = 1, color = 'primary', align = 'left', style }: HeadingProps) {
  const variantMap: Record<number, TextVariant> = { 1: 'h1', 2: 'h2', 3: 'h3', 4: 'h4' };

  return (
    <Text variant={variantMap[level]} color={color} weight="semibold" align={align} style={style}>
      {children}
    </Text>
  );
}

interface CaptionProps {
  children: React.ReactNode;
  color?: TextColor;
  align?: 'left' | 'center' | 'right';
  style?: StyleProp<TextStyle>;
}

export function Caption({ children, color = 'muted', align = 'left', style }: CaptionProps) {
  return (
    <Text variant="caption" color={color} align={align} style={style}>
      {children}
    </Text>
  );
}

interface BadgeProps {
  children: React.ReactNode;
  color?: TextColor;
  variant?: 'solid' | 'outline' | 'soft';
  style?: StyleProp<TextStyle>;
}

export function Badge({ children, color = 'primary', variant = 'solid', style }: BadgeProps) {
  const theme = useTheme();

  return (
    <Text
      variant="badge"
      color={color}
      weight="semibold"
      style={[
        {
          paddingHorizontal: theme.spacing.sm,
          paddingVertical: theme.spacing.xs,
          borderRadius: theme.radius.full,
          textAlign: 'center',
        },
        variant === 'solid' && { backgroundColor: theme.colors[color], color: theme.colors.foreground },
        variant === 'outline' && { borderWidth: 1, borderColor: theme.colors[color] },
        variant === 'soft' && { backgroundColor: `${theme.colors[color]}20` },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export default Text;
