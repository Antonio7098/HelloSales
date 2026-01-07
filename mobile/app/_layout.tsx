import { Stack } from 'expo-router';
import { ThemeProvider } from '../_components/ui';
import { StyleSheet, StatusBar } from 'react-native';
import { theme } from '../theme/index';

export default function Layout() {
  return (
    <ThemeProvider>
      <StatusBar barStyle="light-content" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: styles.content,
          animation: 'fade',
        }}
      />
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  content: {
    backgroundColor: theme.colors.background,
    flex: 1,
  },
});
