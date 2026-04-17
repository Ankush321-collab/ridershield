import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Dimensions, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Animated, { FadeInDown, FadeInUp, ZoomIn } from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';

import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

const { width } = Dimensions.get('window');

const currentCoverageWeek = () => {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
  const diff = Math.floor((now.getTime() - start.getTime()) / 86400000);
  return `${now.getUTCFullYear()}-W${String(Math.ceil((diff + start.getUTCDay() + 1) / 7)).padStart(2, '0')}`;
};

export default function PaymentScreen() {
  const params = useLocalSearchParams<{
    tier: string;
    price: string;
    coverage_pct: string;
    max_payout: string;
    slots_covered: string;
    coverage_week: string;
    zone_name: string;
  }>();
  const { rider, refreshProfile } = useAuth();

  const [processing, setProcessing] = useState(false);
  const [success, setSuccess] = useState(false);
  const [displayUpi, setDisplayUpi] = useState('demo@oksbi');

  useEffect(() => {
    AsyncStorage.getItem('rider_upi_id')
      .then((value) => setDisplayUpi(value || rider?.upi_id || 'demo@oksbi'))
      .catch(() => setDisplayUpi(rider?.upi_id || 'demo@oksbi'));
  }, [rider?.upi_id]);

  const handlePay = async () => {
    setProcessing(true);
    try {
      let slots: string[] = ['18:00-21:00'];
      const storedSlots = await AsyncStorage.getItem('rider_slots');
      if (storedSlots) {
        const parsed = JSON.parse(storedSlots) as string[];
        if (parsed.length > 0) slots = parsed;
      }

      await api.policies.create({
        plan_tier: params.tier || 'balanced',
        payment_method: 'upi',
        upi_id: displayUpi,
        slots,
      });

      setSuccess(true);
      await refreshProfile();
      setTimeout(() => {
        router.replace('/(tabs)');
      }, 2000);
    } catch (error) {
      Alert.alert('Payment failed', error instanceof Error ? error.message : 'Unable to activate policy.');
    } finally {
      setProcessing(false);
    }
  };

  if (success) {
    return (
      <View style={[styles.container, styles.center]}>
        <Animated.View entering={ZoomIn.duration(800).springify()} style={styles.successIcon}>
           <Ionicons name="shield-checkmark" size={64} color="#10b981" />
        </Animated.View>
        <Animated.View entering={FadeInUp.delay(300)}>
          <Text style={styles.successTitle}>Shield Activated</Text>
        </Animated.View>
        <Animated.View entering={FadeInUp.delay(500)}>
          <Text style={styles.successText}>Your parametric coverage is now live.</Text>
        </Animated.View>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Animated.View entering={FadeInUp.duration(600).springify()}>
          <Text style={styles.title}>Confirm Protocol</Text>
          <Text style={styles.subtitle}>Finalize your weekly parametric protection commitment.</Text>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(200).springify()} style={styles.glassCard}>
           <View style={styles.headerRow}>
              <View>
                 <Text style={styles.tierName}>{(params.tier || 'balanced').replace('_', ' ').toUpperCase()}</Text>
                 <Text style={styles.tierSub}>ACTIVE TIER</Text>
              </View>
              <View style={styles.priceContainer}>
                 <Text style={styles.currency}>₹</Text>
                 <Text style={styles.price}>{params.price || '180'}</Text>
              </View>
           </View>

           <View style={styles.divider} />

           <View style={styles.infoGrid}>
              <View style={styles.infoItem}>
                 <Text style={styles.infoLabel}>PERIOD</Text>
                 <Text style={styles.infoValue}>{currentCoverageWeek()}</Text>
              </View>
              <View style={styles.infoItem}>
                 <Text style={styles.infoLabel}>ZONE</Text>
                 <Text style={styles.infoValue}>{params.zone_name || rider?.zone || 'Primary'}</Text>
              </View>
              <View style={styles.infoItem}>
                 <Text style={styles.infoLabel}>SYNERGY</Text>
                 <Text style={styles.infoValue}>{params.coverage_pct || '80'}%</Text>
              </View>
              <View style={styles.infoItem}>
                 <Text style={styles.infoLabel}>CAP</Text>
                 <Text style={styles.infoValue}>₹{params.max_payout || '2500'}</Text>
              </View>
           </View>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(400).springify()} style={styles.upiContainer}>
           <Text style={styles.sectionTitle}>FUNDING BRIDGE</Text>
           <View style={styles.upiCard}>
              <View style={styles.upiIcon}>
                 <Ionicons name="card" size={20} color="#f8fafc" />
              </View>
              <View style={{ flex: 1 }}>
                 <Text style={styles.upiLabel}>Linked UPI Identifier</Text>
                 <Text style={styles.upiValue}>{displayUpi}</Text>
              </View>
              <Ionicons name="checkmark-circle" size={20} color="#10b981" />
           </View>
        </Animated.View>

        <TouchableOpacity 
          style={[styles.payButton, processing && styles.payButtonDisabled]} 
          onPress={handlePay} 
          disabled={processing}
        >
          {processing ? (
            <ActivityIndicator color="#050507" />
          ) : (
            <>
              <Ionicons name="lock-closed" size={18} color="#050507" style={{ marginRight: 8 }} />
              <Text style={styles.payText}>Authorize Payment</Text>
            </>
          )}
        </TouchableOpacity>
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  center: { justifyContent: 'center', alignItems: 'center', padding: 40 },
  scroll: { padding: 24, gap: 24 },
  title: { fontSize: 32, fontWeight: '900', color: '#f8fafc', letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#8b8aa0', lineHeight: 22, fontWeight: '700' },
  glassCard: { backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 32, padding: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  tierName: { fontSize: 22, fontWeight: '900', color: '#f8fafc', letterSpacing: 1 },
  tierSub: { fontSize: 9, color: '#8b8aa0', fontWeight: '800', letterSpacing: 1, marginTop: 2 },
  priceContainer: { flexDirection: 'row', alignItems: 'baseline' },
  currency: { color: '#8b8aa0', fontSize: 14, fontWeight: '900', marginRight: 2 },
  price: { color: '#f8fafc', fontSize: 36, fontWeight: '900' },
  divider: { height: 1, backgroundColor: 'rgba(255,255,255,0.06)', marginBottom: 24 },
  infoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 20 },
  infoItem: { width: '45%' },
  infoLabel: { fontSize: 9, color: '#8b8aa0', fontWeight: '800', letterSpacing: 1, marginBottom: 4 },
  infoValue: { fontSize: 16, color: '#f8fafc', fontWeight: '700' },
  upiContainer: { gap: 12 },
  sectionTitle: { color: '#6f6e80', fontSize: 10, fontWeight: '900', letterSpacing: 1.5, marginLeft: 4 },
  upiCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: 24, padding: 16, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  upiIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: 'rgba(255, 255, 255, 0.08)', alignItems: 'center', justifyContent: 'center', marginRight: 16 },
  upiLabel: { color: '#8b8aa0', fontSize: 11, fontWeight: '700', marginBottom: 2 },
  upiValue: { color: '#f8fafc', fontSize: 16, fontWeight: '800' },
  payButton: { backgroundColor: '#f8fafc', borderRadius: 24, paddingVertical: 20, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', shadowColor: '#ffffff', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.1, shadowRadius: 20, elevation: 10 },
  payButtonDisabled: { opacity: 0.5 },
  payText: { color: '#050507', fontSize: 17, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 1 },
  successIcon: { width: 120, height: 120, borderRadius: 60, backgroundColor: 'rgba(16, 185, 129, 0.1)', alignItems: 'center', justifyContent: 'center', marginBottom: 32 },
  successTitle: { fontSize: 32, fontWeight: '900', color: '#10b981', marginBottom: 16, textAlign: 'center' },
  successText: { fontSize: 16, color: '#b8b7c7', textAlign: 'center', fontWeight: '600' },
});
