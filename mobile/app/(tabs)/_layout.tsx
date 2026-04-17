import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Redirect, Tabs } from 'expo-router';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';

import Colors from '../../constants/Colors';
import { useAuth } from '../../contexts/AuthContext';
import { useClientOnlyValue } from '../../components/useClientOnlyValue';

function TabBarIcon(props: {
  name: React.ComponentProps<typeof Ionicons>['name'];
  color: string;
}) {
  return <Ionicons size={24} style={{ marginBottom: -3 }} {...props} />;
}

export default function TabLayout() {
  const { isAuthenticated, isReady } = useAuth();
  const headerShown = useClientOnlyValue(false, true);

  if (!isReady) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#050507' }}>
        <ActivityIndicator color="#f8fafc" size="large" />
      </View>
    );
  }

  if (!isAuthenticated) {
    return <Redirect href="/" />;
  }

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#f8fafc',
        tabBarInactiveTintColor: '#8b8aa0',
        headerShown: false,
        headerStyle: { backgroundColor: 'transparent' },
        headerTransparent: true, 
        headerTitleStyle: { fontWeight: '900', color: '#f8fafc', fontSize: 28, letterSpacing: -1 },
        headerShadowVisible: false,
        tabBarStyle: {
          position: 'absolute',
          bottom: 30,
          left: 30,
          right: 30,
          elevation: 0,
          backgroundColor: 'transparent',
          borderRadius: 40,
          height: 70,
          borderTopWidth: 0,
          borderWidth: 1,
          borderColor: 'rgba(255, 255, 255, 0.1)',
          overflow: 'hidden',
        },
        tabBarBackground: () => (
          <BlurView tint="dark" intensity={80} style={StyleSheet.absoluteFill} />
        ),
        tabBarShowLabel: false,
        tabBarItemStyle: {
          paddingVertical: 10,
        }
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Guardian',
          tabBarIcon: ({ color }) => <TabBarIcon name="home-outline" color={color} />,
        }}
      />
      <Tabs.Screen
        name="claims"
        options={{
          title: 'History',
          tabBarIcon: ({ color }) => <TabBarIcon name="time-outline" color={color} />,
        }}
      />
      <Tabs.Screen
        name="manual-claim"
        options={{
          title: 'Report',
          tabBarIcon: ({ color }) => <TabBarIcon name="camera-outline" color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Node',
          tabBarIcon: ({ color }) => <TabBarIcon name="person-outline" color={color} />,
        }}
      />
      <Tabs.Screen
        name="two"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
