import { useState } from 'react';
import { TextInput, TextInputProps, StyleProp, ViewStyle, Pressable, View } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { Icon } from './Icons';

type InputSize = 'sm' | 'md' | 'lg';

interface InputProps extends Omit<TextInputProps, 'placeholderTextColor'> {
  placeholder?: string;
  value?: string;
  onChangeText?: (text: string) => void;
  size?: InputSize;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  inputStyle?: StyleProp<ViewStyle>;
}

export function Input({
  placeholder,
  value,
  onChangeText,
  size = 'md',
  error,
  leftIcon,
  rightIcon,
  style,
  inputStyle,
  ...props
}: InputProps) {
  const theme = useTheme();
  const [focused, setFocused] = useState(false);

  const sizeStyles: Record<InputSize, ViewStyle> = {
    sm: { paddingHorizontal: 12, paddingVertical: 8, minHeight: 36 },
    md: { paddingHorizontal: 16, paddingVertical: 12, minHeight: 44 },
    lg: { paddingHorizontal: 20, paddingVertical: 16, minHeight: 56 },
  };

  const textSizeMap: Record<InputSize, 'caption' | 'bodySm' | 'body'> = {
    sm: 'caption',
    md: 'bodySm',
    lg: 'body',
  };

  return (
    <View style={style}>
      <View
        style={[
          {
            flexDirection: 'row',
            alignItems: 'center',
            borderRadius: theme.radius.md,
            backgroundColor: theme.colors.input,
            borderWidth: 1,
            borderColor: error
              ? theme.colors.destructive
              : focused
              ? theme.colors.ring
              : 'transparent',
          },
          sizeStyles[size],
        ]}
      >
        {leftIcon && <View style={{ marginRight: theme.spacing.sm }}>{leftIcon}</View>}
        <TextInput
          placeholder={placeholder}
          placeholderTextColor={theme.colors.mutedForeground}
          value={value}
          onChangeText={onChangeText}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={[
            {
              flex: 1,
              color: theme.colors.foreground,
              fontSize: theme.fontSize[textSizeMap[size]],
              padding: 0,
              outlineStyle: 'none',
            },
            inputStyle,
          ]}
          {...props}
        />
        {rightIcon && <View style={{ marginLeft: theme.spacing.sm }}>{rightIcon}</View>}
      </View>
      {error && (
        <Text variant="caption" color="error" style={{ marginTop: theme.spacing.xs }}>
          {error}
        </Text>
      )}
    </View>
  );
}

interface SearchInputProps extends Omit<InputProps, 'leftIcon' | 'rightIcon'> {
  onClear?: () => void;
}

export function SearchInput({ onClear, value, onChangeText, ...props }: SearchInputProps) {
  const theme = useTheme();

  return (
    <Input
      {...props}
      value={value}
      onChangeText={onChangeText}
      leftIcon={
        <Icon name="Search" size="sm" color={theme.colors.mutedForeground} />
      }
      rightIcon={
        value ? (
          <Pressable onPress={onClear || (() => onChangeText?.(''))}>
            <Icon name="X" size="sm" color={theme.colors.mutedForeground} />
          </Pressable>
        ) : null
      }
    />
  );
}

export default Input;
