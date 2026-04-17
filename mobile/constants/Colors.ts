const adminTheme = {
  background: '#050507',
  backgroundDeep: '#000000',
  surface: 'rgba(18, 18, 24, 0.94)',
  surfaceSoft: 'rgba(255, 255, 255, 0.03)',
  border: 'rgba(255, 255, 255, 0.08)',
  borderStrong: 'rgba(255, 255, 255, 0.14)',
  text: '#f8fafc',
  muted: '#8b8aa0',
  mutedStrong: '#b8b7c7',
  purple: '#a78bfa',
  purpleStrong: '#8b5cf6',
  amber: '#f59e0b',
  emerald: '#10b981',
  rose: '#f43f5e',
  cyan: '#38bdf8',
};

const tintColorLight = adminTheme.purpleStrong;
const tintColorDark = adminTheme.purple;

export const AdminTheme = adminTheme;

export default {
  light: {
    text: adminTheme.text,
    background: adminTheme.background,
    tint: tintColorLight,
    tabIconDefault: adminTheme.muted,
    tabIconSelected: tintColorLight,
    card: adminTheme.surface,
    border: adminTheme.border,
    notification: adminTheme.rose,
  },
  dark: {
    text: adminTheme.text,
    background: adminTheme.background,
    tint: tintColorDark,
    tabIconDefault: adminTheme.muted,
    tabIconSelected: tintColorDark,
    card: adminTheme.surface,
    border: adminTheme.border,
    notification: adminTheme.rose,
  },
};
