import { View, ViewStyle, StyleProp } from 'react-native';
import { useTheme } from './context';

interface BoxProps {
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}

export function Box({ children, style, testID }: BoxProps) {
  return (
    <View style={style} testID={testID}>
      {children}
    </View>
  );
}

interface FlexProps extends BoxProps {
  direction?: 'row' | 'column' | 'row-reverse' | 'column-reverse';
  align?: 'flex-start' | 'center' | 'flex-end' | 'stretch' | 'space-between' | 'space-around' | 'space-evenly';
  justify?: 'flex-start' | 'center' | 'flex-end' | 'space-between' | 'space-around' | 'space-evenly';
  wrap?: 'nowrap' | 'wrap' | 'wrap-reverse';
  gap?: number;
}

export function Flex({ children, style, direction = 'column', align, justify, wrap, gap }: FlexProps) {
  return (
    <View
      style={[
        { flexDirection: direction, alignItems: align, justifyContent: justify, flexWrap: wrap, gap },
        style,
      ]}
    >
      {children}
    </View>
  );
}

interface VStackProps extends Omit<FlexProps, 'direction'> {
  spacing?: number;
}

export function VStack({ children, spacing, ...props }: VStackProps) {
  return (
    <Flex direction="column" gap={spacing} {...props}>
      {children}
    </Flex>
  );
}

interface HStackProps extends Omit<FlexProps, 'direction'> {
  spacing?: number;
}

export function HStack({ children, spacing, ...props }: HStackProps) {
  return (
    <Flex direction="row" gap={spacing} {...props}>
      {children}
    </Flex>
  );
}

interface ZStackProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  alignment?: 'center' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

export function ZStack({ children, style, alignment = 'center' }: ZStackProps) {
  const alignmentMap = {
    'center': 'center',
    'top-left': 'flex-start',
    'top-right': 'flex-end',
    'bottom-left': 'flex-end',
    'bottom-right': 'flex-end',
  } as const;

  return (
    <View style={[style, { position: 'relative' }]}>
      {React.Children.map(children, (child, index) => (
        <View
          key={index}
          style={[
            { position: 'absolute' },
            alignment === 'center' && { top: 0, left: 0, right: 0, bottom: 0 },
            alignment.startsWith('top') && { top: 0 },
            alignment.startsWith('bottom') && { bottom: 0 },
            alignment.endsWith('left') && { left: 0 },
            alignment.endsWith('right') && { right: 0 },
          ]}
        >
          {child}
        </View>
      ))}
    </View>
  );
}

import React from 'react';

export default Box;
