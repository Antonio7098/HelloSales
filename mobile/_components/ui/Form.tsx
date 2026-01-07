import { useState, useCallback } from 'react';
import { View, ViewStyle, StyleProp, Pressable } from 'react-native';
import { Input, InputProps } from './Input';
import { Text } from './Text';
import { useTheme } from './context';

type ValidationRule<T> = {
  test: (value: T) => boolean;
  message: string;
};

type Validator<T> = string | ValidationRule<T> | ((value: T) => string | undefined);

interface FieldConfig<T> {
  validators: Validator<T>[];
  value: T;
  error?: string;
  touched: boolean;
}

interface UseFormOptions<T> {
  initialValues: T;
  validators?: Partial<Record<keyof T, Validator<T>[]>>;
}

export function useForm<T extends Record<string, any>>({ initialValues, validators = {} }: UseFormOptions<T>) {
  const [values, setValues] = useState<T>(initialValues);
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateField = useCallback((name: keyof T, value: any): string | undefined => {
    const fieldValidators = validators[name];
    if (!fieldValidators) return undefined;

    for (const validator of fieldValidators) {
      if (typeof validator === 'string') {
        if (!value || (typeof value === 'string' && !value.trim())) {
          return validator;
        }
      } else if (typeof validator === 'function') {
        const error = validator(value);
        if (error) return error;
      } else {
        if (!validator.test(value)) {
          return validator.message;
        }
      }
    }
    return undefined;
  }, [validators]);

  const setFieldValue = useCallback((name: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }));
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors(prev => ({ ...prev, [name]: error }));
    }
  }, [touched, validateField]);

  const handleBlur = useCallback((name: keyof T) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    const error = validateField(name, values[name]);
    setErrors(prev => ({ ...prev, [name]: error }));
  }, [values, validateField]);

  const handleChange = useCallback((name: keyof T) => (value: any) => {
    setFieldValue(name, value);
  }, [setFieldValue]);

  const setFieldTouched = useCallback((name: keyof T) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    const error = validateField(name, values[name]);
    setErrors(prev => ({ ...prev, [name]: error }));
  }, [values, validateField]);

  const validateAll = useCallback(() => {
    const newErrors: Partial<Record<keyof T, string>> = {};
    let isValid = true;

    for (const key of Object.keys(values) as (keyof T)[]) {
      const error = validateField(key, values[key]);
      if (error) {
        newErrors[key] = error;
        isValid = false;
      }
    }

    setErrors(newErrors);
    setTouched(Object.keys(values).reduce((acc, key) => ({ ...acc, [key]: true }), {} as any));
    return isValid;
  }, [values, validateField]);

  const reset = useCallback(() => {
    setValues(initialValues);
    setTouched({});
    setErrors({});
    setIsSubmitting(false);
  }, [initialValues]);

  return {
    values,
    setValues,
    setFieldValue,
    handleChange,
    handleBlur,
    setFieldTouched,
    touched,
    errors,
    setErrors,
    validateAll,
    validateField,
    isSubmitting,
    setIsSubmitting,
    reset,
    isValid: Object.keys(errors).length === 0 && Object.keys(touched).length > 0,
  };
}

interface FormFieldProps extends Omit<InputProps, 'error'> {
  name: string;
  label?: string;
  error?: string;
  required?: boolean;
  style?: StyleProp<ViewStyle>;
  labelStyle?: StyleProp<ViewStyle>;
}

export function FormField({ name, label, error, required, style, labelStyle, ...props }: FormFieldProps) {
  const theme = useTheme();

  return (
    <View style={style}>
      {label && (
        <Text variant="bodySm" weight="medium" style={[labelStyle, { marginBottom: theme.spacing.xs }]}>
          {required ? `${label} *` : label}
        </Text>
      )}
      <Input error={error} {...props} />
    </View>
  );
}

interface FormProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  onSubmit?: () => void;
}

export function Form({ children, style, onSubmit }: FormProps) {
  return (
    <View style={style}>
      {children}
    </View>
  );
}

interface FormSectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function FormSection({ title, description, children, style }: FormSectionProps) {
  const theme = useTheme();

  return (
    <View style={style}>
      {(title || description) && (
        <View style={{ marginBottom: theme.spacing.md }}>
          {title && (
            <Text variant="h4" weight="semibold" style={{ marginBottom: theme.spacing.xs }}>
              {title}
            </Text>
          )}
          {description && (
            <Text variant="body" color="secondary">
              {description}
            </Text>
          )}
        </View>
      )}
      <View>{children}</View>
    </View>
  );
}

interface FormActionsProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function FormActions({ children, style }: FormActionsProps) {
  const theme = useTheme();

  return (
    <View style={[{ flexDirection: 'row', gap: theme.spacing.sm, marginTop: theme.spacing.lg }, style]}>
      {children}
    </View>
  );
}

interface FormErrorProps {
  message: string;
  style?: StyleProp<ViewStyle>;
}

export function FormError({ message, style }: FormErrorProps) {
  const theme = useTheme();

  return (
    <View style={[{ padding: theme.spacing.md, backgroundColor: `${theme.colors.destructive}20`, borderRadius: theme.radius.md, marginBottom: theme.spacing.md }, style]}>
      <Text color="error">{message}</Text>
    </View>
  );
}

interface FormSuccessProps {
  message: string;
  style?: StyleProp<ViewStyle>;
}

export function FormSuccess({ message, style }: FormSuccessProps) {
  const theme = useTheme();

  return (
    <View style={[{ padding: theme.spacing.md, backgroundColor: `${theme.colors.success}20`, borderRadius: theme.radius.md, marginBottom: theme.spacing.md }, style]}>
      <Text color="success">{message}</Text>
    </View>
  );
}

export default Form;
