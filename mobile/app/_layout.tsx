import FontAwesome from '@expo/vector-icons/FontAwesome';
import { DarkTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { useColorScheme } from '../components/useColorScheme';
import { AuthProvider } from '../contexts/AuthContext';
import Colors from '../constants/Colors';

export {
  // Catch any errors thrown by the Layout component.
  ErrorBoundary,
} from 'expo-router';

export const prevConfig = {
  // Ensure that reloading on `/modal` keeps a back button present.
  initialRouteName: '(tabs)',
};

// Prevent the splash screen from auto-hiding before asset loading is complete.
SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
    ...FontAwesome.font,
  });

  // Expo Router uses Error Boundaries to catch errors in the navigation tree.
  useEffect(() => {
    if (error) throw error;
  }, [error]);

  useEffect(() => {
    if (loaded) {
      SplashScreen.hideAsync();
    }
  }, [loaded]);

  if (!loaded) {
    return null;
  }

  return <RootLayoutNav />;
}

function RootLayoutNav() {
  const colorScheme = useColorScheme();

  const customDarkTheme = {
    ...DarkTheme,
    colors: {
      ...DarkTheme.colors,
      primary: Colors.dark.tint,
      background: Colors.dark.background,
      card: Colors.dark.card,
      text: Colors.dark.text,
      border: Colors.dark.border,
      notification: Colors.dark.notification,
    },
  };

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <ThemeProvider value={customDarkTheme}>
          <StatusBar style="light" />
          <Stack screenOptions={{ 
              headerStyle: { backgroundColor: Colors.dark.background },
              headerTitleStyle: { fontWeight: '800', color: Colors.dark.text },
              headerTintColor: Colors.dark.tint,
              headerShadowVisible: false,
           }}>
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="(auth)/otp" options={{ title: 'Verify OTP' }} />
            <Stack.Screen name="(auth)/register" options={{ title: 'Sign Up' }} />
            <Stack.Screen name="(auth)/zone-select" options={{ title: 'Select Zone' }} />
            <Stack.Screen name="(auth)/slot-select" options={{ title: 'Select Slots' }} />

            {/* Main App (tabs) */}
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />

            {/* Dev 2: Policy Flow */}
            <Stack.Screen name="policy/select" options={{ title: 'Choose Plan' }} />
            <Stack.Screen name="policy/payment" options={{ title: 'Payment' }} />

            <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
            <Stack.Screen name="+not-found" />
          </Stack>
        </ThemeProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
