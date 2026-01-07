import { createContext, useContext, ReactNode } from 'react';
import { theme, Theme } from '../../theme/index';

type ThemeContextValue = Theme;

const ThemeContext = createContext<ThemeContextValue | null>(null);

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): Theme {
  const context = useContext(ThemeContext);
  if (!context) {
    return theme;
  }
  return context;
}

export default ThemeProvider;
