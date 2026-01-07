import { View, ViewStyle, StyleProp, Pressable, PressableProps } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { Icon } from './Icons';

interface ListProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  variant?: 'plain' | 'inset' | 'separated';
}

export function List({ children, style, variant = 'separated' }: ListProps) {
  const theme = useTheme();

  if (variant === 'inset') {
    return (
      <View
        style={[
          {
            backgroundColor: theme.colors.card,
            borderWidth: 1,
            borderColor: theme.colors.border,
            borderRadius: theme.radius.lg,
          },
          style,
        ]}
      >
        {children}
      </View>
    );
  }

  return (
    <View style={style}>
      {children}
    </View>
  );
}

interface ListItemProps extends Omit<PressableProps, 'style'> {
  title: string;
  subtitle?: string;
  description?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  rightContent?: React.ReactNode;
  badge?: string;
  badgeColor?: string;
  chevron?: boolean;
  destructive?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function ListItem({
  title,
  subtitle,
  description,
  leftIcon,
  rightIcon,
  rightContent,
  badge,
  badgeColor,
  chevron = false,
  destructive = false,
  style,
  ...props
}: ListItemProps) {
  const theme = useTheme();

  return (
    <Pressable
      style={({ pressed }) => [
        {
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.md,
          minHeight: 56,
          opacity: pressed ? 0.7 : 1,
        },
        style,
      ]}
      {...props}
    >
      {leftIcon && (
        <View style={{ marginRight: theme.spacing.md, width: 24, alignItems: 'center' }}>
          {leftIcon}
        </View>
      )}
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm }}>
          <Text
            variant="body"
            weight="medium"
            color={destructive ? 'error' : 'primary'}
            style={{ flex: 1 }}
          >
            {title}
          </Text>
          {badge && (
            <Text
              variant="caption"
              color={badgeColor || 'primary'}
              style={{
                paddingHorizontal: theme.spacing.sm,
                paddingVertical: 2,
                borderRadius: theme.radius.full,
                backgroundColor: `${badgeColor ? badgeColor : theme.colors.primary}20`,
              }}
            >
              {badge}
            </Text>
          )}
        </View>
        {subtitle && (
          <Text variant="bodySm" color="secondary">{subtitle}</Text>
        )}
        {description && (
          <Text variant="caption" color="muted" style={{ marginTop: 2 }}>
            {description}
          </Text>
        )}
      </View>
      {rightContent || (
        <View style={{ flexDirection: 'row', alignItems: 'center', marginLeft: theme.spacing.sm }}>
          {rightIcon}
          {chevron && <Icon name="ChevronRight" size="sm" color={theme.colors.mutedForeground} />}
        </View>
      )}
    </Pressable>
  );
}

interface ListRowProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function ListRow({ children, style }: ListRowProps) {
  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.md, minHeight: 56 }, style]}>
      {children}
    </View>
  );
}

interface ListActionProps extends Omit<PressableProps, 'style'> {
  icon: string;
  label: string;
  destructive?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function ListAction({ icon, label, destructive, style, ...props }: ListActionProps) {
  const theme = useTheme();

  return (
    <Pressable
      style={({ pressed }) => [
        {
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.md,
          minHeight: 48,
          opacity: pressed ? 0.7 : 1,
        },
        style,
      ]}
      {...props}
    >
      <Icon
        name={icon as any}
        size="md"
        color={destructive ? theme.colors.destructive : theme.colors.foreground}
        style={{ marginRight: theme.spacing.md }}
      />
      <Text color={destructive ? 'error' : 'primary'}>{label}</Text>
    </Pressable>
  );
}

interface ListSectionProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  headerStyle?: StyleProp<ViewStyle>;
  action?: React.ReactNode;
}

export function ListSection({ title, subtitle, children, style, headerStyle, action }: ListSectionProps) {
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
              <Text variant="caption" color="muted" weight="semibold" style={{ textTransform: 'uppercase' as const, letterSpacing: 0.5 }}>
                {title}
              </Text>
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

interface ListDividerProps {
  indent?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function ListDivider({ indent = false, style }: ListDividerProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          height: 1,
          backgroundColor: theme.colors.border,
          marginLeft: indent ? theme.spacing.md + 40 : theme.spacing.md,
        },
        style,
      ]}
    />
  );
}

interface ListHeaderProps {
  title: string;
  style?: StyleProp<ViewStyle>;
}

export function ListHeader({ title, style }: ListHeaderProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.sm,
          minHeight: 32,
          justifyContent: 'center',
        },
        style,
      ]}
    >
      <Text
        variant="caption"
        color="muted"
        weight="semibold"
        style={{ textTransform: 'uppercase' as const, letterSpacing: 0.5 }}
      >
        {title}
      </Text>
    </View>
  );
}

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function EmptyState({ icon, title, description, action, style }: EmptyStateProps) {
  const theme = useTheme();

  return (
    <View style={[{ alignItems: 'center', justifyContent: 'center', padding: theme.spacing.xxl }, style]}>
      {icon && (
        <Icon
          name={icon as any}
          size="xl"
          color={theme.colors.mutedForeground}
          style={{ marginBottom: theme.spacing.md }}
        />
      )}
      <Text variant="h4" weight="semibold" style={{ marginBottom: theme.spacing.xs }}>{title}</Text>
      {description && (
        <Text variant="body" color="secondary" style={{ textAlign: 'center', marginBottom: theme.spacing.md }}>
          {description}
        </Text>
      )}
      {action}
    </View>
  );
}

export default List;
