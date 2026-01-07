import { useState, useRef, useCallback, useEffect } from 'react';
import { View, ViewStyle, StyleProp, Pressable, TextInput, Animated, Dimensions } from 'react-native';
import { useTheme } from './context';
import { Text } from './Text';
import { Icon } from './Icons';
import { IconButton } from './Button';

interface Option<T> {
  value: T;
  label: string;
  disabled?: boolean;
  icon?: string;
}

interface SelectProps<T> {
  options: Option<T>[];
  value: T | null;
  onChange: (value: T) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  emptyMessage?: string;
  style?: StyleProp<ViewStyle>;
  dropdownStyle?: StyleProp<ViewStyle>;
  dropdownMaxHeight?: number;
}

export function Select<T extends string | number>({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  label,
  error,
  disabled = false,
  searchable = false,
  searchPlaceholder = 'Search...',
  emptyMessage = 'No options available',
  style,
  dropdownStyle,
  dropdownMaxHeight = 300,
}: SelectProps<T>) {
  const theme = useTheme();
  const [visible, setVisible] = useState(false);
  const [search, setSearch] = useState('');
  const [dropdownTop, setDropdownTop] = useState(0);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const buttonRef = useRef<View>(null);

  const selectedOption = options.find(opt => opt.value === value);

  const filteredOptions = searchable
    ? options.filter(opt =>
        opt.label.toLowerCase().includes(search.toLowerCase())
      )
    : options;

  const measureButton = useCallback(() => {
    buttonRef.current?.measure((_x, _y, _width, height, _pageX, pageY) => {
      setDropdownTop(pageY + height);
    });
  }, []);

  useEffect(() => {
    if (visible) {
      measureButton();
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }).start();
    }
  }, [visible, fadeAnim, measureButton]);

  const handleSelect = useCallback((option: Option<T>) => {
    onChange(option.value);
    setVisible(false);
    setSearch('');
  }, [onChange]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setSearch('');
  }, []);

  return (
    <View style={style}>
      {label && (
        <Text variant="bodySm" weight="medium" style={{ marginBottom: theme.spacing.xs }}>
          {label}
        </Text>
      )}
      <View ref={buttonRef}>
        <Pressable
          onPress={() => !disabled && setVisible(true)}
          style={({ pressed }) => [
            {
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.sm,
              minHeight: 44,
              borderRadius: theme.radius.md,
              backgroundColor: theme.colors.input,
              borderWidth: 1,
              borderColor: error ? theme.colors.destructive : visible ? theme.colors.ring : 'transparent',
              opacity: disabled ? theme.opacity.disabled : 1,
            },
            pressed && { opacity: 0.8 },
          ]}
        >
          <Text color={selectedOption ? 'primary' : 'muted'}>
            {selectedOption?.label || placeholder}
          </Text>
          <Icon
            name={visible ? 'ChevronUp' : 'ChevronDown'}
            size="sm"
            color={theme.colors.mutedForeground}
          />
        </Pressable>
      </View>
      {error && (
        <Text variant="caption" color="error" style={{ marginTop: theme.spacing.xs }}>
          {error}
        </Text>
      )}

      {visible && (
        <Animated.View
          style={[
            {
              position: 'absolute',
              top: dropdownTop,
              left: 0,
              right: 0,
              backgroundColor: theme.colors.popover,
              borderRadius: theme.radius.lg,
              borderWidth: 1,
              borderColor: theme.colors.border,
              maxHeight: dropdownMaxHeight,
              zIndex: theme.zIndex.dropdown,
              overflow: 'hidden',
            },
            dropdownStyle,
            { opacity: fadeAnim },
          ]}
        >
          {searchable && (
            <View
              style={{
                padding: theme.spacing.sm,
                borderBottomWidth: 1,
                borderBottomColor: theme.colors.border,
              }}
            >
              <View
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  backgroundColor: theme.colors.input,
                  borderRadius: theme.radius.md,
                  paddingHorizontal: theme.spacing.sm,
                }}
              >
                <Icon name="Search" size="sm" color={theme.colors.mutedForeground} />
                <TextInput
                  value={search}
                  onChangeText={setSearch}
                  placeholder={searchPlaceholder}
                  placeholderTextColor={theme.colors.mutedForeground}
                  style={{
                    flex: 1,
                    paddingVertical: theme.spacing.sm,
                    paddingHorizontal: theme.spacing.xs,
                    color: theme.colors.foreground,
                    fontSize: theme.fontSize.body,
                  }}
                  autoFocus
                />
                {search && (
                  <IconButton icon="X" size="sm" onPress={() => setSearch('')} />
                )}
              </View>
            </View>
          )}

          <View style={{ maxHeight: dropdownMaxHeight - (searchable ? 60 : 0) }}>
            {filteredOptions.length === 0 ? (
              <View style={{ padding: theme.spacing.md, alignItems: 'center' }}>
                <Text variant="body" color="muted">{emptyMessage}</Text>
              </View>
            ) : (
              filteredOptions.map((option, index) => (
                <Pressable
                  key={option.value}
                  onPress={() => !option.disabled && handleSelect(option)}
                  style={({ pressed }) => [
                    {
                      flexDirection: 'row',
                      alignItems: 'center',
                      paddingHorizontal: theme.spacing.md,
                      paddingVertical: theme.spacing.sm,
                      minHeight: 40,
                      backgroundColor: option.value === value ? `${theme.colors.primary}20` : 'transparent',
                    },
                    pressed && { opacity: 0.7 },
                    option.disabled && { opacity: 0.5 },
                  ]}
                >
                  {option.icon && (
                    <Icon
                      name={option.icon as any}
                      size="md"
                      color={theme.colors.foreground}
                      style={{ marginRight: theme.spacing.md }}
                    />
                  )}
                  <Text
                    color={option.disabled ? 'muted' : option.value === value ? 'primary' : 'primary'}
                    style={{ flex: 1 }}
                  >
                    {option.label}
                  </Text>
                  {option.value === value && (
                    <Icon name="Check" size="sm" color={theme.colors.success} />
                  )}
                </Pressable>
              ))
            )}
          </View>
        </Animated.View>
      )}

      {visible && (
        <Pressable
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: theme.zIndex.dropdown - 1,
          }}
          onPress={handleClose}
        />
      )}
    </View>
  );
}

interface MultiSelectProps<T> {
  options: Option<T>[];
  value: T[];
  onChange: (value: T[]) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  searchable?: boolean;
  maxDisplay?: number;
  style?: StyleProp<ViewStyle>;
}

export function MultiSelect<T extends string | number>({
  options,
  value,
  onChange,
  placeholder = 'Select options',
  label,
  error,
  disabled = false,
  searchable = true,
  maxDisplay = 3,
  style,
}: MultiSelectProps<T>) {
  const theme = useTheme();
  const [visible, setVisible] = useState(false);
  const [search, setSearch] = useState('');
  const [dropdownTop, setDropdownTop] = useState(0);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const buttonRef = useRef<View>(null);

  const selectedOptions = options.filter(opt => value.includes(opt.value));
  const filteredOptions = searchable
    ? options.filter(opt =>
        opt.label.toLowerCase().includes(search.toLowerCase())
      )
    : options;

  const measureButton = useCallback(() => {
    buttonRef.current?.measure((_x, _y, _width, height, _pageX, pageY) => {
      setDropdownTop(pageY + height);
    });
  }, []);

  useEffect(() => {
    if (visible) {
      measureButton();
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }).start();
    }
  }, [visible, fadeAnim, measureButton]);

  const toggleOption = useCallback((optionValue: T) => {
    if (value.includes(optionValue)) {
      onChange(value.filter(v => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  }, [value, onChange]);

  const displayText = selectedOptions.length === 0
    ? placeholder
    : selectedOptions.length <= maxDisplay
    ? selectedOptions.map(o => o.label).join(', ')
    : `${selectedOptions.length} selected`;

  return (
    <View style={style}>
      {label && (
        <Text variant="bodySm" weight="medium" style={{ marginBottom: theme.spacing.xs }}>
          {label}
        </Text>
      )}
      <View ref={buttonRef}>
        <Pressable
          onPress={() => !disabled && setVisible(true)}
          style={({ pressed }) => [
            {
              flexDirection: 'row',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: theme.spacing.xs,
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.sm,
              minHeight: 44,
              borderRadius: theme.radius.md,
              backgroundColor: theme.colors.input,
              borderWidth: 1,
              borderColor: error ? theme.colors.destructive : visible ? theme.colors.ring : 'transparent',
              opacity: disabled ? theme.opacity.disabled : 1,
            },
            pressed && { opacity: 0.8 },
          ]}
        >
          <Text color={selectedOptions.length > 0 ? 'primary' : 'muted'} style={{ flex: 1 }}>
            {displayText}
          </Text>
          <Icon
            name={visible ? 'ChevronUp' : 'ChevronDown'}
            size="sm"
            color={theme.colors.mutedForeground}
          />
        </Pressable>
      </View>
      {error && (
        <Text variant="caption" color="error" style={{ marginTop: theme.spacing.xs }}>
          {error}
        </Text>
      )}

      {visible && (
        <Animated.View
          style={[
            {
              position: 'absolute',
              top: dropdownTop,
              left: 0,
              right: 0,
              backgroundColor: theme.colors.popover,
              borderRadius: theme.radius.lg,
              borderWidth: 1,
              borderColor: theme.colors.border,
              maxHeight: 300,
              zIndex: theme.zIndex.dropdown,
              overflow: 'hidden',
            },
            { opacity: fadeAnim },
          ]}
        >
          {searchable && (
            <View
              style={{
                padding: theme.spacing.sm,
                borderBottomWidth: 1,
                borderBottomColor: theme.colors.border,
              }}
            >
              <View
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  backgroundColor: theme.colors.input,
                  borderRadius: theme.radius.md,
                  paddingHorizontal: theme.spacing.sm,
                }}
              >
                <Icon name="Search" size="sm" color={theme.colors.mutedForeground} />
                <TextInput
                  value={search}
                  onChangeText={setSearch}
                  placeholder="Search..."
                  placeholderTextColor={theme.colors.mutedForeground}
                  style={{
                    flex: 1,
                    paddingVertical: theme.spacing.sm,
                    paddingHorizontal: theme.spacing.xs,
                    color: theme.colors.foreground,
                    fontSize: theme.fontSize.body,
                  }}
                />
              </View>
            </View>
          )}

          <View style={{ maxHeight: 240 }}>
            {filteredOptions.map((option, index) => (
              <Pressable
                key={option.value}
                onPress={() => !option.disabled && toggleOption(option.value)}
                style={({ pressed }) => [
                  {
                    flexDirection: 'row',
                    alignItems: 'center',
                    paddingHorizontal: theme.spacing.md,
                    paddingVertical: theme.spacing.sm,
                    minHeight: 40,
                    backgroundColor: value.includes(option.value) ? `${theme.colors.primary}20` : 'transparent',
                  },
                  pressed && { opacity: 0.7 },
                  option.disabled && { opacity: 0.5 },
                ]}
              >
                <View
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 2,
                    borderWidth: 2,
                    borderColor: value.includes(option.value) ? theme.colors.primary : theme.colors.mutedForeground,
                    backgroundColor: value.includes(option.value) ? theme.colors.primary : 'transparent',
                    marginRight: theme.spacing.sm,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {value.includes(option.value) && (
                    <Icon name="Check" size="xs" color={theme.colors.primaryForeground} />
                  )}
                </View>
                <Text color={option.disabled ? 'muted' : 'primary'}>
                  {option.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </Animated.View>
      )}

      {visible && (
        <Pressable
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: theme.zIndex.dropdown - 1,
          }}
          onPress={() => setVisible(false)}
        />
      )}
    </View>
  );
}

interface ChipSelectProps<T> {
  options: Option<T>[];
  value: T[];
  onChange: (value: T[]) => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function ChipSelect<T extends string | number>({
  options,
  value,
  onChange,
  disabled = false,
  style,
}: ChipSelectProps<T>) {
  const theme = useTheme();

  const toggle = useCallback((optionValue: T) => {
    if (value.includes(optionValue)) {
      onChange(value.filter(v => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  }, [value, onChange]);

  return (
    <View style={[{ flexDirection: 'row', flexWrap: 'wrap', gap: theme.spacing.xs }, style]}>
      {options.map((option) => {
        const isSelected = value.includes(option.value);
        return (
          <Pressable
            key={option.value}
            onPress={() => !disabled && toggle(option.value)}
            disabled={disabled}
            style={({ pressed }) => [
              {
                paddingHorizontal: theme.spacing.sm,
                paddingVertical: theme.spacing.xs,
                borderRadius: theme.radius.full,
                borderWidth: 1,
                borderColor: isSelected ? theme.colors.primary : theme.colors.border,
                backgroundColor: isSelected ? theme.colors.primary : 'transparent',
              },
              pressed && { opacity: 0.7 },
              disabled && { opacity: 0.5 },
            ]}
          >
            <Text
              variant="caption"
              color={isSelected ? 'primaryForeground' : 'primary'}
              weight="medium"
            >
              {option.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// All exports are already named exports above
