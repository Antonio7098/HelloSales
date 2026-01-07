import { View, StyleProp, ViewStyle } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';

export type IconName = keyof typeof iconRegistry;

interface IconProps {
  name: IconName;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
  style?: StyleProp<ViewStyle>;
}

export function Icon({ name, size = 'md', color, style }: IconProps) {
  const theme = useTheme();
  const iconColor = color || theme.colors.foreground;
  const iconSize = theme.iconSize[size];

  const IconComponent = iconRegistry[name];

  if (!IconComponent) {
    return <Text>❓</Text>;
  }

  return (
    <View style={[{ width: iconSize, height: iconSize }, style]}>
      <IconComponent color={iconColor} size={iconSize} />
    </View>
  );
}

const createIcon = (glyph: string) => ({ color, size }: { color: string; size: number }) => (
  <Text style={{ color, fontSize: size, lineHeight: size, textAlign: 'center' }}>
    {glyph}
  </Text>
);

const iconRegistry = {
  Home: createIcon('🏠'),
  Users: createIcon('👥'),
  Building: createIcon('🏢'),
  Package: createIcon('📦'),
  Chart: createIcon('📊'),
  Settings: createIcon('⚙️'),
  Search: createIcon('🔍'),
  Bell: createIcon('🔔'),
  Menu: createIcon('☰'),
  Plus: createIcon('+'),
  PlusCircle: createIcon('⊕'),
  Minus: createIcon('−'),
  MinusCircle: createIcon('⊖'),
  X: createIcon('✕'),
  XCircle: createIcon('⊘'),
  Check: createIcon('✓'),
  CheckCircle: createIcon('⊙'),
  ChevronLeft: createIcon('‹'),
  ChevronRight: createIcon('›'),
  ChevronDown: createIcon('˅'),
  ChevronUp: createIcon('˄'),
  ArrowLeft: createIcon('←'),
  ArrowRight: createIcon('→'),
  ArrowUp: createIcon('↑'),
  ArrowDown: createIcon('↓'),
  Dollar: createIcon('$'),
  CreditCard: createIcon('💳'),
  Cart: createIcon('🛒'),
  Tag: createIcon('🏷️'),
  TrendingUp: createIcon('📈'),
  TrendingDown: createIcon('📉'),
  Percent: createIcon('%'),
  Receipt: createIcon('🧾'),
  Mail: createIcon('✉'),
  Phone: createIcon('📞'),
  Message: createIcon('💬'),
  Calendar: createIcon('📅'),
  Clock: createIcon('🕐'),
  Edit: createIcon('✎'),
  Trash: createIcon('🗑'),
  Copy: createIcon('📋'),
  Download: createIcon('⬇'),
  Upload: createIcon('⬆'),
  Refresh: createIcon('↻'),
  More: createIcon('⋯'),
  MoreVertical: createIcon('⋮'),
  Star: createIcon('★'),
  StarOutline: createIcon('☆'),
  Heart: createIcon('♥'),
  HeartOutline: createIcon('♡'),
  Eye: createIcon('👁'),
  EyeOff: createIcon('⦸'),
  Lock: createIcon('🔒'),
  Unlock: createIcon('🔓'),
  Shield: createIcon('🛡'),
  Alert: createIcon('⚠'),
  Info: createIcon('ℹ'),
  Help: createIcon('?'),
  User: createIcon('👤'),
  Store: createIcon('🏪'),
  Location: createIcon('📍'),
  Map: createIcon('🗺'),
  Briefcase: createIcon('💼'),
  Target: createIcon('🎯'),
  Award: createIcon('🏆'),
  Zap: createIcon('⚡'),
  Image: createIcon('🖼'),
  Camera: createIcon('📷'),
  Video: createIcon('🎬'),
  Music: createIcon('🎵'),
  File: createIcon('📄'),
  Folder: createIcon('📁'),
  Document: createIcon('📃'),
  Globe: createIcon('🌐'),
  Link: createIcon('🔗'),
  Book: createIcon('📖'),
  Coffee: createIcon('☕'),
  Sun: createIcon('☀'),
  Moon: createIcon('☾'),
  Cloud: createIcon('☁'),
  Umbrella: createIcon('☂'),
  Fire: createIcon('🔥'),
  Lightbulb: createIcon('💡'),
  Wrench: createIcon('🔧'),
  Hammer: createIcon('🔨'),
} as const;

export function getIconNames(): (keyof typeof iconRegistry)[] {
  return Object.keys(iconRegistry) as (keyof typeof iconRegistry)[];
}

export default Icon;
