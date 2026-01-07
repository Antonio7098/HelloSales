import { View, ViewStyle, StyleProp, Animated, Pressable } from 'react-native';
import { useState } from 'react';
import { useTheme } from './context';
import { Text } from './Text';
import { Icon } from './Icons';
import { Button } from './Button';

interface ModalProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  backdropStyle?: StyleProp<ViewStyle>;
  showCloseButton?: boolean;
}

export function Modal({ visible, onClose, title, children, style, backdropStyle, showCloseButton = true }: ModalProps) {
  const theme = useTheme();
  const [opacity] = useState(() => new Animated.Value(0));

  Animated.timing(opacity, {
    toValue: visible ? 1 : 0,
    duration: 200,
    useNativeDriver: true,
  }).start();

  if (!visible && opacity.__getValue() === 0) {
    return null;
  }

  return (
    <Animated.View
      style={[
        {
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: theme.zIndex.modal,
        },
        { opacity },
      ]}
    >
      <Pressable style={[{ flex: 1, width: '100%' }, backdropStyle]} onPress={onClose} />
      <View
        style={[
          {
            width: '85%',
            maxWidth: 400,
            backgroundColor: theme.colors.popover,
            borderRadius: theme.radius.lg,
            borderWidth: 1,
            borderColor: theme.colors.border,
            overflow: 'hidden',
          },
          style,
        ]}
      >
        {(title || showCloseButton) && (
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.md,
              borderBottomWidth: 1,
              borderBottomColor: theme.colors.border,
              minHeight: 52,
            }}
          >
            {title ? (
              <Text variant="h4" weight="semibold">{title}</Text>
            ) : (
              <View />
            )}
            {showCloseButton && (
              <Pressable onPress={onClose} hitSlop={12}>
                <Icon name="X" size="lg" color={theme.colors.mutedForeground} />
              </Pressable>
            )}
          </View>
        )}
        <View style={{ padding: theme.spacing.md }}>{children}</View>
      </View>
    </Animated.View>
  );
}

interface AlertProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
  variant?: 'default' | 'destructive';
}

export function Alert({
  visible,
  onClose,
  title,
  message,
  confirmText = 'OK',
  cancelText,
  onConfirm,
  onCancel,
  variant = 'default',
}: AlertProps) {
  const theme = useTheme();

  const handleConfirm = () => {
    onConfirm?.();
    onClose();
  };

  const handleCancel = () => {
    onCancel?.();
    onClose();
  };

  return (
    <Modal visible={visible} onClose={onClose} title={title} showCloseButton={false}>
      {message && (
        <Text variant="body" color="secondary" style={{ marginBottom: theme.spacing.lg }}>
          {message}
        </Text>
      )}
      <View style={{ flexDirection: 'row', gap: theme.spacing.sm, justifyContent: 'flex-end' }}>
        {cancelText && (
          <Button variant="secondary" onPress={handleCancel} style={{ minWidth: 80 }}>
            {cancelText}
          </Button>
        )}
        <Button
          variant={variant === 'destructive' ? 'danger' : 'primary'}
          onPress={handleConfirm}
          style={{ minWidth: 80 }}
        >
          {confirmText}
        </Button>
      </View>
    </Modal>
  );
}

interface ConfirmDialogProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
  variant?: 'default' | 'destructive';
}

export function ConfirmDialog(props: ConfirmDialogProps) {
  return <Alert {...props} />;
}

interface ActionSheetItem {
  label: string;
  onPress: () => void;
  variant?: 'default' | 'destructive';
  icon?: string;
}

interface ActionSheetProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  items: ActionSheetItem[];
  cancelText?: string;
  onCancel?: () => void;
}

export function ActionSheet({ visible, onClose, title, items, cancelText = 'Cancel', onCancel }: ActionSheetProps) {
  const theme = useTheme();

  const handleCancel = () => {
    onCancel?.();
    onClose();
  };

  return (
    <Modal visible={visible} onClose={handleCancel} title={title} showCloseButton={false}>
      <View style={{ gap: theme.spacing.xs }}>
        {items.map((item, index) => (
          <Pressable
            key={index}
            onPress={() => {
              item.onPress();
              onClose();
            }}
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.md,
              minHeight: 48,
              opacity: pressed ? 0.7 : 1,
              borderRadius: theme.radius.md,
            })}
          >
            {item.icon && (
              <Icon
                name={item.icon as any}
                size="md"
                color={item.variant === 'destructive' ? theme.colors.destructive : theme.colors.foreground}
                style={{ marginRight: theme.spacing.md }}
              />
            )}
            <Text
              color={item.variant === 'destructive' ? 'error' : 'primary'}
              style={{ flex: 1 }}
            >
              {item.label}
            </Text>
          </Pressable>
        ))}
      </View>
      {cancelText && (
        <View style={{ marginTop: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: theme.spacing.sm }}>
          <Pressable
            onPress={handleCancel}
            style={({ pressed }) => ({
              paddingVertical: theme.spacing.md,
              alignItems: 'center',
              opacity: pressed ? 0.7 : 1,
            })}
          >
            <Text color="secondary">{cancelText}</Text>
          </Pressable>
        </View>
      )}
    </Modal>
  );
}

export default Modal;
