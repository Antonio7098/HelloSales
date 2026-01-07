import { View, ViewStyle, StyleProp } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';

interface SectionProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  headerStyle?: StyleProp<ViewStyle>;
  action?: React.ReactNode;
}

export function Section({ title, subtitle, children, style, headerStyle, action }: SectionProps) {
  const theme = useTheme();

  return (
    <View style={style}>
      {(title || action) && (
        <View
          style={[
            {
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.sm,
              minHeight: 40,
            },
            headerStyle,
          ]}
        >
          <View>
            {title && (
              <Text variant="h4" weight="semibold">{title}</Text>
            )}
            {subtitle && (
              <Text variant="caption" color="muted">{subtitle}</Text>
            )}
          </View>
          {action}
        </View>
      )}
      <View>{children}</View>
    </View>
  );
}

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function SectionHeader({ title, subtitle, action, style }: SectionHeaderProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          minHeight: 40,
        },
        style,
      ]}
    >
      <View>
        <Text variant="caption" color="muted" weight="semibold" style={{ textTransform: 'uppercase' as const, letterSpacing: 0.5 }}>
          {title}
        </Text>
        {subtitle && (
          <Text variant="caption" color="muted">{subtitle}</Text>
        )}
      </View>
      {action}
    </View>
  );
}

interface SectionContentProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  inset?: boolean;
}

export function SectionContent({ children, style, inset = false }: SectionContentProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          backgroundColor: theme.colors.card,
          borderTopWidth: 1,
          borderBottomWidth: 1,
          borderColor: theme.colors.border,
        },
        inset && {
          marginHorizontal: theme.spacing.md,
          borderWidth: 1,
          borderRadius: theme.radius.lg,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export default Section;
