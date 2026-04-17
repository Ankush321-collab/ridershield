import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import Animated, { FadeInUp, FadeInDown, Layout } from 'react-native-reanimated';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { api } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import Colors from '../../constants/Colors';

const TIME_SLOTS = [
  { id: '06:00-09:00', label: 'Sunrise', time: '06:00 - 09:00', icon: '🌅' },
  { id: '09:00-12:00', label: 'Morning', time: '09:00 - 12:00', icon: '☀️' },
  { id: '12:00-15:00', label: 'Afternoon', time: '12:00 - 15:00', icon: '🌤️' },
  { id: '15:00-18:00', label: 'Evening', time: '15:00 - 18:00', icon: '🌇' },
  { id: '18:00-21:00', label: 'Night Peak', time: '18:00 - 21:00', icon: '🌙' },
  { id: '21:00-23:00', label: 'Late Night', time: '21:00 - 23:00', icon: '🌃' }
];

export default function SlotSelectScreen() {
  const params = useLocalSearchParams();
  const { login, setTempToken } = useAuth();
  const [selectedSlots, setSelectedSlots] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const toggleSlot = (id: string) => {
    setSelectedSlots(prev => {
      if (prev.includes(id)) return prev.filter(s => s !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  const handleComplete = async () => {
    console.log("🚀 Initializing Shield Protocol with slots:", selectedSlots);
    setLoading(true);
    try {
      const tempToken = await AsyncStorage.getItem('temp_token');
      console.log("🔑 Temp Token Status:", tempToken ? "PRESENT" : "MISSING");
      
      if (!tempToken) throw new Error('Session restoration failed. Please restart local node.');

      const city = params.city as string;
      if (!city) throw new Error('City parameter missing. Please re-select your zone.');

      await AsyncStorage.setItem('rider_slots', JSON.stringify(selectedSlots));

      const regResult = await api.riders.register({
         name: params.name as string,
         platform: params.platform as string,
         city,
         zone_id: params.zoneId as string,
         slots: selectedSlots,
         upi_id: params.upiId as string
      }, tempToken);
      
      console.log("✅ Registration Successful:", regResult.rider_id);
      const token = regResult.jwt_token; 
      if (token) {
        await login(token);
        await setTempToken(null); // Clear registration session
        console.log("🔓 Login successful, routing to dash...");
        router.replace('/(tabs)');
      } else {
        throw new Error("Activation sequence failed: No token returned.");
      }
    } catch (err: any) {
      console.error("❌ Initialization Error:", err);
      Alert.alert('Protocol Error', err.message || 'Onboarding sequence interrupted.');
    } finally {
      setLoading(false);
    }
  };

  const isCompleteReady = selectedSlots.length > 0;

  return (
    <View style={styles.container}>
      <SafeAreaView style={{ flex: 1 }}>
        <Animated.View entering={FadeInUp.delay(200).springify()} style={styles.header}>
           <Text style={styles.title}>Operational Slots</Text>
           <Text style={styles.subtitle}>Select your active duty windows (max 4 perimeters).</Text>
        </Animated.View>

        <ScrollView contentContainerStyle={styles.grid} showsVerticalScrollIndicator={false}>
          {TIME_SLOTS.map((slot, index) => {
            const isSelected = selectedSlots.includes(slot.id);
            const isDisabled = !isSelected && selectedSlots.length >= 4;

            return (
              <Animated.View 
                key={slot.id} 
                entering={FadeInDown.delay(400 + index * 50).springify()}
                style={styles.cardWrapper}
              >
                <TouchableOpacity
                  style={[
                    styles.card, 
                    isSelected && styles.cardActive,
                    isDisabled && styles.cardDisabled
                  ]}
                  onPress={() => toggleSlot(slot.id)}
                  disabled={isDisabled}
                  activeOpacity={0.8}
                >
                  <Text style={styles.icon}>{slot.icon}</Text>
                  <Text style={[styles.label, isSelected && { color: Colors.dark.tint }]}>{slot.label}</Text>
                  <Text style={styles.time}>{slot.time}</Text>
                </TouchableOpacity>
              </Animated.View>
            );
          })}
        </ScrollView>
      </SafeAreaView>

      <View style={styles.footer}>
        <TouchableOpacity 
          style={[styles.button, !isCompleteReady && styles.buttonDisabled]} 
          disabled={!isCompleteReady || loading}
          onPress={handleComplete}
        >
          {loading ? (
             <ActivityIndicator color="#fff" />
          ) : (
             <Text style={styles.buttonText}>INITIALIZE SHIELD →</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  header: { padding: 32, paddingBottom: 16 },
  title: { fontSize: 32, fontWeight: '900', color: '#f8fafc', letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#8b8aa0', lineHeight: 22, fontWeight: '600', marginTop: 8 },
  grid: { paddingHorizontal: 32, paddingBottom: 140, flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  cardWrapper: { width: '48%', marginBottom: 16 },
  card: { backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 28, padding: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', alignItems: 'center' },
  cardActive: { borderColor: Colors.dark.tint, backgroundColor: 'rgba(56, 189, 248, 0.05)' },
  cardDisabled: { opacity: 0.1 },
  icon: { fontSize: 32, marginBottom: 12 },
  label: { fontSize: 14, fontWeight: '900', color: '#f8fafc', textAlign: 'center', marginBottom: 4 },
  time: { fontSize: 11, color: '#8b8aa0', textAlign: 'center', fontWeight: '700' },
  footer: { 
    position: 'absolute', 
    bottom: 0, 
    left: 0, 
    right: 0, 
    padding: 32, 
    paddingBottom: 40, 
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    zIndex: 1000, // Ensure it's on top in Web mode
    elevation: 10
  },
  button: { backgroundColor: Colors.dark.tint, paddingVertical: 22, borderRadius: 24, alignItems: 'center', shadowColor: Colors.dark.tint, shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.3, shadowRadius: 20, elevation: 10 },
  buttonDisabled: { opacity: 0.2, shadowOpacity: 0 },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '900', letterSpacing: 1 }
});
