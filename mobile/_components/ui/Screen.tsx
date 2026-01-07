 import { View, ViewStyle, StyleProp, ScrollView, ScrollViewProps } from 'react-native';
 import { useTheme } from './context';
 import { Text } from './Text';
 import { SafeAreaView } from 'react-native-safe-area-context';
 import { StatusBar } from 'react-native';
 import { Button } from './Button';

interface ScreenProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  statusBar?: 'light' | 'dark';
  backgroundColor?: string;
}

export function Screen({ children, style, statusBar = 'light', backgroundColor }: ScreenProps) {
  const theme = useTheme();

  return (
    <SafeAreaView
      style={[{ flex: 1, backgroundColor: backgroundColor || theme.colors.background }, style]}
      edges={['top', 'bottom', 'left', 'right']}
    >
      <StatusBar barStyle={statusBar === 'light' ? 'light-content' : 'dark-content'} />
      {children}
    </SafeAreaView>
  );
}

interface ScrollScreenProps extends ScreenProps {
  contentContainerStyle?: StyleProp<ViewStyle>;
  showsVerticalScrollIndicator?: boolean;
  onScroll?: ScrollViewProps['onScroll'];
  scrollEventThrottle?: number;
}

export function ScrollScreen({
  children,
  contentContainerStyle,
  showsVerticalScrollIndicator = true,
  onScroll,
  scrollEventThrottle = 16,
  style,
  ...props
}: ScrollScreenProps) {
  const theme = useTheme();

  return (
    <Screen style={style} {...props}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[contentContainerStyle]}
        showsVerticalScrollIndicator={showsVerticalScrollIndicator}
        onScroll={onScroll}
        scrollEventThrottle={scrollEventThrottle}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </Screen>
  );
}

interface ScreenHeaderProps {
  title: string;
  subtitle?: string;
  leftAction?: React.ReactNode;
  rightAction?: React.ReactNode;
  onBack?: () => void;
  style?: StyleProp<ViewStyle>;
}

export function ScreenHeader({ title, subtitle, leftAction, rightAction, onBack, style }: ScreenHeaderProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingHorizontal: theme.spacing.md,
          paddingVertical: theme.spacing.md,
          borderBottomWidth: 1,
          borderBottomColor: theme.colors.border,
          minHeight: 56,
        },
        style,
      ]}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
        {onBack && (
          <Button variant="ghost" size="sm" onPress={onBack}>
            ←
          </Button>
        )}
        {leftAction && <View style={{ marginRight: theme.spacing.sm }}>{leftAction}</View>}
        <View style={{ flex: 1 }}>
          <Text variant="h4" weight="semibold">{title}</Text>
          {subtitle && (
            <Text variant="caption" color="muted">{subtitle}</Text>
          )}
        </View>
      </View>
      {rightAction && <View style={{ marginLeft: theme.spacing.sm }}>{rightAction}</View>}
    </View>
  );
}

export default Screen;
