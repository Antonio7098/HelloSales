import { View, ViewStyle, StyleProp } from 'react-native';
import { Card, CardBody } from './Card';
import { VStack } from './Box';
import { Text } from './Text';

interface StatCardProps {
  label: string;
  value: string | number;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'muted';
  style?: StyleProp<ViewStyle>;
}

export function StatCard({ label, value, color = 'primary', style }: StatCardProps) {
  return (
    <Card style={style} variant="elevated">
      <CardBody>
        <VStack spacing="xs">
          <Text variant="caption" color="muted">{label}</Text>
          <Text variant="h3" weight="bold" color={color}>{value}</Text>
        </VStack>
      </CardBody>
    </Card>
  );
}

interface StatsCardsProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function StatsCards({ children, style }: StatsCardsProps) {
  return (
    <View style={[{ flexDirection: 'row', gap: 8 }, style]}>
      {children}
    </View>
  );
}

export default StatsCards;
