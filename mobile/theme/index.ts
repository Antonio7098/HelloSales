export const colors = {
  // Semantic tokens (CSS variable names)
  background: '#0F172A',
  foreground: '#F8FAFC',
  card: '#1E293B',
  cardForeground: '#F8FAFC',
  popover: '#1E293B',
  popoverForeground: '#F8FAFC',
  primary: '#F8FAFC',
  primaryForeground: '#0F172A',
  secondary: '#334155',
  secondaryForeground: '#F8FAFC',
  muted: '#334155',
  mutedForeground: '#94A3B8',
  accent: '#334155',
  accentForeground: '#F8FAFC',
  destructive: '#7F1D1D',
  destructiveForeground: '#F8FAFC',
  border: '#334155',
  input: '#334155',
  ring: '#64748B',
  
  // Semantic aliases
  success: '#059669',
  successForeground: '#F8FAFC',
  warning: '#D97706',
  warningForeground: '#0F172A',
  info: '#0284C7',
  infoForeground: '#F8FAFC',
} as const;

export const spacing = {
  none: 0,
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
} as const;

export const radius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  display: 40,
} as const;

export const fontWeight = {
  normal: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
} as const;

export const lineHeight = {
  tight: 1.2,
  normal: 1.5,
  relaxed: 1.75,
} as const;

export const iconSize = {
  xs: 14,
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
  xxl: 40,
} as const;

export const shadow = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
} as const;

export const opacity = {
  disabled: 0.5,
  muted: 0.6,
} as const;

export const zIndex = {
  base: 0,
  dropdown: 100,
  modal: 200,
  toast: 300,
  tooltip: 400,
} as const;

export const theme = {
  colors,
  spacing,
  radius,
  fontSize,
  fontWeight,
  lineHeight,
  iconSize,
  shadow,
  opacity,
  zIndex,
} as const;

export type Theme = typeof theme;
export default theme;
