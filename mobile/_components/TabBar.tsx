import { View, ViewStyle, StyleProp, Pressable } from 'react-native';
import { useTheme } from './ui/context';
import { Text, Icon } from './ui';
import { usePathname, useRouter } from 'expo-router';

interface TabBarProps {
  style?: StyleProp<ViewStyle>;
}

interface TabItemProps {
  route: string;
  label: string;
  iconName: string;
  isActive: boolean;
  onPress: () => void;
}

function TabItem({ route, label, iconName, isActive, onPress }: TabItemProps) {
  const theme = useTheme();

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => ({
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: theme.spacing.sm,
        opacity: pressed ? 0.7 : 1,
      })}
    >
      <View style={{ marginBottom: 2 }}>
        <Icon
          name={iconName as any}
          size="md"
          color={isActive ? theme.colors.foreground : theme.colors.mutedForeground}
        />
      </View>
      <Text
        variant="caption"
        color={isActive ? 'primary' : 'muted'}
        weight={isActive ? 'semibold' : 'normal'}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function TabBar({ style }: TabBarProps) {
  const theme = useTheme();
  const router = useRouter();
  const pathname = usePathname();

  const tabs = [
    { route: '/', label: 'Clients', iconName: 'Users' },
    { route: '/products', label: 'Products', iconName: 'Package' },
    { route: '/team', label: 'Team', iconName: 'Users' },
  ];

  return (
    <View
      style={[
        {
          flexDirection: 'row',
          backgroundColor: theme.colors.card,
          borderTopWidth: 1,
          borderTopColor: theme.colors.border,
          paddingBottom: 0,
        },
        style,
      ]}
    >
      {tabs.map((tab) => (
        <TabItem
          key={tab.route}
          route={tab.route}
          label={tab.label}
          iconName={tab.iconName}
          isActive={pathname === tab.route}
          onPress={() => router.replace(tab.route as any)}
        />
      ))}
    </View>
  );
}

interface ShellProps {
  children: React.ReactNode;
}

export function Shell({ children }: ShellProps) {
  const theme = useTheme();

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {children}
      <TabBar style={{ position: 'absolute', bottom: 0, left: 0, right: 0 }} />
    </View>
  );
}

export default TabBar;
