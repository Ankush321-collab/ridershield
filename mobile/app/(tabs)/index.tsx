import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import Animated, { FadeInUp, FadeInRight } from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';

import { useAuth } from '../../contexts/AuthContext';
import { api, type PolicyResponse, type TriggerStatus, type PayoutListItem, type RiderIntelligenceResponse } from '../../services/api';
import { formatApiDateTime } from '../../utils/datetime';

const triggerEmoji = (type: string) => {
  switch (type) {
    case 'heavy_rain': return '🌧️';
    case 'traffic_congestion': return '🚗';
    case 'store_closure': return '🏪';
    case 'platform_outage': return '📱';
    case 'regulatory_curfew': return '🚫';
    case 'gps_shadowban': return '📍';
    case 'dark_store_queue': return '🛒';
    case 'algorithmic_shock': return '⚡';
    case 'community_signal': return '📣';
    default: return '⚠️';
  }
};

function AnimatedCard({ children, delay = 0, style, isGlass = true }: { children: React.ReactNode, delay?: number, style?: any, isGlass?: boolean }) {
  return (
    <Animated.View
      entering={FadeInUp.delay(delay).duration(600).springify()}
      style={[styles.card, style]}
    >
      {isGlass && (
        <BlurView tint="dark" intensity={30} style={StyleSheet.absoluteFill} />
      )}
      <View style={styles.cardContent}>
        {children}
      </View>
    </Animated.View>
  );
}

export default function DashboardScreen() {
  const { rider } = useAuth();
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [triggers, setTriggers] = useState<TriggerStatus | null>(null);
  const [payouts, setPayouts] = useState<PayoutListItem[]>([]);
  const [zoneRisk, setZoneRisk] = useState<{ weather: number; traffic: number; store: number } | null>(null);
  const [intelligence, setIntelligence] = useState<RiderIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    let slots = '18:00-21:00,21:00-23:00';
    try {
      const stored = await AsyncStorage.getItem('rider_slots');
      if (stored) {
        const parsed: string[] = JSON.parse(stored);
        if (parsed.length > 0) slots = parsed.join(',');
      }
    } catch {}

    const [policyData, triggerData, payoutData, quoteData, intelligenceData] = await Promise.all([
      api.policies.getActive().catch(() => null),
      api.triggers.getStatus().catch(() => null),
      api.payouts.list().catch(() => ({ payouts: [] })),
      api.policies.getQuote(slots, rider?.city ?? '').catch(() => null),
      api.riders.getIntelligence(7).catch(() => null),
    ]);

    setPolicy(policyData);
    setTriggers(triggerData);
    setPayouts(payoutData.payouts || []);
    setZoneRisk(quoteData?.quotes?.[0]?.risk_breakdown ?? null);
    setIntelligence(intelligenceData);
    setLastUpdated(new Date());
    setRefreshError(null);
  };

  useEffect(() => {
    loadDashboardData()
      .catch((error) => setRefreshError(error instanceof Error ? error.message : 'Unable to load dashboard.'))
      .finally(() => setLoading(false));
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadDashboardData();
    } catch (error) {
      setRefreshError(error instanceof Error ? error.message : 'Unable to refresh dashboard right now.');
    } finally {
      setRefreshing(false);
    }
  }, []);

  const hasActivePolicy = policy?.status === 'active';
  const zoneAlerts = useMemo(
    () => (triggers?.active_triggers || []).filter((trigger) => !rider?.zone || trigger.zone === rider.zone),
    [rider?.zone, triggers?.active_triggers]
  );

  if (loading && !refreshing) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color="#f8fafc" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <LinearGradient
        colors={['#09090b', '#000000', '#000000']}
        style={StyleSheet.absoluteFill}
      />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#f8fafc" />}
      >
        <View style={styles.header}>
          <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <Image
              source={require('../../assets/images/Zylo.png')}
              style={{ width: 40, height: 40 }}
              resizeMode="contain"
            />
            <View>
              <Animated.Text entering={FadeInRight.duration(600)} style={styles.greeting}>
                Hey, {rider?.name || 'Rider'} 👋
              </Animated.Text>
              <View style={styles.statusIndicator}>
                <View style={[styles.dot, { backgroundColor: hasActivePolicy ? '#22c55e' : '#f59e0b' }]} />
                <Text style={[styles.subtext, { color: hasActivePolicy ? '#22c55e' : '#f59e0b' }]}>
                  {hasActivePolicy ? 'Coverage Shield Active' : 'Shield Offline'}
                </Text>
              </View>
            </View>
          </View>
          <TouchableOpacity
            style={styles.profileIcon}
            onPress={() => router.push('/(tabs)/profile')}
          >
             <Ionicons name="person-circle-outline" size={32} color="#b8b7c7" />
          </TouchableOpacity>
        </View>

        {rider?.zone && zoneRisk && (
          <Animated.View entering={FadeInUp.delay(50).springify()} style={styles.zoneHealthBar}>
            <BlurView tint="dark" intensity={40} style={StyleSheet.absoluteFill} />
            <View style={styles.zoneHealthItem}>
               <Text style={styles.zoneHealthIcon}>🌧️</Text>
               <Text style={styles.zoneHealthValue}>{zoneRisk.weather}%</Text>
            </View>
            <View style={styles.zoneHealthDivider} />
            <View style={styles.zoneHealthItem}>
               <Text style={styles.zoneHealthIcon}>🚗</Text>
               <Text style={styles.zoneHealthValue}>{zoneRisk.traffic}%</Text>
            </View>
            <View style={styles.zoneHealthDivider} />
            <View style={styles.zoneHealthItem}>
               <Text style={styles.zoneHealthIcon}>🏪</Text>
               <Text style={styles.zoneHealthValue}>{zoneRisk.store}%</Text>
            </View>
          </Animated.View>
        )}

        {refreshError ? (
          <View style={styles.errorAlert}>
            <Text style={styles.errorText}>{refreshError}</Text>
          </View>
        ) : null}

        {hasActivePolicy && policy ? (
          <AnimatedCard delay={100} style={styles.activePolicyCard}>
            <View style={styles.cardHeader}>
              <View style={styles.cardTitleRow}>
                <ShieldCheckIcon size={20} color="#f8fafc" />
                <Text style={styles.cardTitle}>Live Policy</Text>
              </View>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{policy.plan_tier.replace('_', ' ').toUpperCase()}</Text>
              </View>
            </View>

            <View style={styles.statsContainer}>
              <View style={styles.statBox}>
                <Text style={styles.statLabel}>LIMIT</Text>
                <Text style={styles.statValue}>₹{policy.coverage_limit}</Text>
              </View>
              <View style={styles.divider} />
              <View style={styles.statBox}>
                <Text style={styles.statLabel}>TIME LEFT</Text>
                <Text style={styles.statValue}>{policy.hours_remaining ?? 0}H</Text>
              </View>
              <View style={styles.divider} />
              <View style={styles.statBox}>
                <Text style={styles.statLabel}>CLAIMED</Text>
                <Text style={styles.statValue}>₹{policy.coverage_used ?? 0}</Text>
              </View>
            </View>

            <View style={styles.policyFooter}>
               <Ionicons name="time-outline" size={14} color="#8b8aa0" />
               <Text style={styles.cardFooterText}>
                  Week {policy.coverage_week} • Exp. {policy.expires_at ? formatApiDateTime(policy.expires_at) : 'End of period'}
               </Text>
            </View>
          </AnimatedCard>
        ) : (
          <AnimatedCard delay={100} style={styles.unprotectedCard}>
             <Ionicons name="warning" size={32} color="#f59e0b" style={{ marginBottom: 8 }} />
             <Text style={styles.cardTitleLarge}>Protect your income</Text>
             <Text style={styles.cardBody}>Unforeseen disruptions can hurt your earnings. Get covered today.</Text>
             <TouchableOpacity style={styles.ctaButton} onPress={() => router.push('/policy/select')}>
                <Text style={styles.ctaText}>Get Protected Now</Text>
             </TouchableOpacity>
          </AnimatedCard>
        )}

        <AnimatedCard delay={200} style={[zoneAlerts.length > 0 && styles.alertCard]}>
           <View style={styles.cardHeader}>
             <View style={styles.cardTitleRow}>
                <Ionicons name="flash" size={18} color="#f59e0b" />
                <Text style={styles.cardTitle}>Zone Disruptions</Text>
             </View>
             {zoneAlerts.length > 0 && (
                <View style={[styles.badge, { backgroundColor: '#7f1d1d' }]}>
                   <Text style={[styles.badgeText, { color: '#fca5a5' }]}>LIVE</Text>
                </View>
             )}
           </View>

          {zoneAlerts.length > 0 ? (
            zoneAlerts.map((alert) => (
              <View key={alert.trigger_id} style={styles.alertRow}>
                <View style={styles.alertIconBg}>
                   <Text style={{ fontSize: 20 }}>{triggerEmoji(alert.type)}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.alertText}>{alert.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</Text>
                  <Text style={styles.alertMeta}>{alert.zone} • {alert.severity} Intensity</Text>
                </View>
              </View>
            ))
          ) : (
            <View style={styles.emptyState}>
               <Ionicons name="checkmark-circle" size={24} color="#22c55e" />
               <Text style={styles.mutedText}>All systems normal in your zone.</Text>
            </View>
          )}
        </AnimatedCard>

        <AnimatedCard delay={300}>
          <View style={[styles.cardHeader, { marginBottom: 16 }]}>
             <View style={styles.cardTitleRow}>
                <Ionicons name="wallet" size={18} color="#10b981" />
                <Text style={styles.cardTitle}>Recent Payouts</Text>
             </View>
          </View>

          {payouts.length > 0 ? (
            payouts.slice(0, 3).map((payout) => (
              <View key={payout.payout_id} style={styles.payoutRow}>
                <View style={styles.payoutIcon}>
                   <Ionicons name="arrow-down-circle" size={20} color="#f8fafc" />
                </View>
                <View style={{ flex: 1, marginHorizontal: 12 }}>
                  <Text style={styles.payoutLabel}>Income Supplement</Text>
                  <Text style={styles.payoutDate}>{formatApiDateTime(payout.created_at)}</Text>
                </View>
                <Text style={styles.payoutAmount}>₹{payout.amount}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.mutedText}>No payout activity this week.</Text>
          )}
        </AnimatedCard>

        <AnimatedCard delay={360}>
          <View style={[styles.cardHeader, { marginBottom: 14 }]}>
            <View style={styles.cardTitleRow}>
              <Ionicons name="analytics" size={18} color="#a78bfa" />
              <Text style={styles.cardTitle}>Next-Week Forecast</Text>
            </View>
          </View>
          {intelligence?.next_week_forecast?.length ? (
            intelligence.next_week_forecast.slice(0, 3).map((day) => (
              <View key={day.date} style={styles.forecastRow}>
                <View>
                  <Text style={styles.forecastDate}>{day.date}</Text>
                  <Text style={styles.forecastMeta}>{day.risk_band.toUpperCase()} risk</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={styles.forecastRisk}>{Math.round(day.predicted_disruption_probability * 100)}%</Text>
                  <Text style={styles.forecastMeta}>earnings x{day.expected_earnings_multiplier}</Text>
                </View>
              </View>
            ))
          ) : (
            <Text style={styles.mutedText}>Forecast is calibrating from recent rider activity.</Text>
          )}
        </AnimatedCard>

        <AnimatedCard delay={420}>
          <View style={[styles.cardHeader, { marginBottom: 14 }]}>
            <View style={styles.cardTitleRow}>
              <Ionicons name="notifications" size={18} color="#f59e0b" />
              <Text style={styles.cardTitle}>Forward Alerts</Text>
            </View>
          </View>
          {intelligence?.forward_alerts?.length ? (
            intelligence.forward_alerts.map((alert, idx) => (
              <View key={`${alert.type}-${idx}`} style={styles.alertSignalRow}>
                <Text style={styles.alertSignalTitle}>{alert.message}</Text>
                <Text style={styles.alertSignalMeta}>{alert.severity.toUpperCase()}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.mutedText}>No predictive alerts right now.</Text>
          )}
        </AnimatedCard>

        <View style={styles.actionButtons}>
          <TouchableOpacity style={[styles.ctaSecondary, styles.flexOne]} onPress={() => router.push('/policy/select')}>
            <Ionicons name="shield-outline" size={18} color="#f8fafc" style={{ marginRight: 8 }} />
            <Text style={styles.ctaSecondaryText}>{hasActivePolicy ? 'My Policy' : 'Buy Policy'}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.ctaDanger, styles.flexOne]} onPress={() => router.push('/manual-claim')}>
            <Ionicons name="camera-outline" size={18} color="#fecaca" style={{ marginRight: 8 }} />
            <Text style={styles.ctaDangerText}>Report Issue</Text>
          </TouchableOpacity>
        </View>
        <View style={{ height: 100 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function ShieldCheckIcon({ size, color }: { size: number, color: string }) {
   return <Ionicons name="shield-checkmark" size={size} color={color} />;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, gap: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 },
  greeting: { fontSize: 28, fontWeight: '800', color: '#f8fafc', letterSpacing: -0.5 },
  statusIndicator: { flexDirection: 'row', alignItems: 'center', marginTop: 6, gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  subtext: { fontSize: 13, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1 },
  refreshMeta: { fontSize: 11, color: '#8b8aa0', marginTop: 4, fontWeight: '600' },
  profileIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#121218', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  zoneHealthBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'rgba(18, 18, 24, 0.72)', paddingHorizontal: 20, paddingVertical: 14, borderRadius: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
  zoneHealthItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  zoneHealthIcon: { fontSize: 16 },
  zoneHealthValue: { color: '#f8fafc', fontSize: 14, fontWeight: '900' },
  zoneHealthDivider: { width: 1, height: 16, backgroundColor: 'rgba(255,255,255,0.1)' },
  card: { backgroundColor: 'rgba(18, 18, 24, 0.72)', borderRadius: 32, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', overflow: 'hidden', position: 'relative' },
  cardContent: { padding: 20 },
  activePolicyCard: { borderColor: 'rgba(255, 255, 255, 0.2)', borderWidth: 1.5 },
  unprotectedCard: { backgroundColor: 'rgba(18, 18, 24, 0.55)', alignItems: 'center', textAlign: 'center', paddingVertical: 32 },
  alertCard: { borderColor: '#f59e0b', borderWidth: 1.5, shadowColor: '#f59e0b', shadowOpacity: 0.2, shadowRadius: 10, shadowOffset: { height: 0, width: 0 }, elevation: 10 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  cardTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardTitle: { fontSize: 15, fontWeight: '800', color: '#b8b7c7', textTransform: 'uppercase', letterSpacing: 1 },
  cardTitleLarge: { fontSize: 22, fontWeight: '800', color: '#f8fafc', marginBottom: 8 },
  cardBody: { color: '#b8b7c7', fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 20 },
  badge: { backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  badgeText: { color: '#f8fafc', fontSize: 11, fontWeight: '800' },
  statsContainer: { flexDirection: 'row', alignItems: 'center', marginVertical: 10 },
  statBox: { flex: 1, alignItems: 'center' },
  statLabel: { fontSize: 10, fontWeight: '700', color: '#8b8aa0', marginBottom: 4, letterSpacing: 0.5 },
  statValue: { fontSize: 20, fontWeight: '800', color: '#f8fafc' },
  divider: { width: 1, height: 30, backgroundColor: 'rgba(255,255,255,0.08)' },
  policyFooter: { flexDirection: 'row', alignItems: 'center', marginTop: 20, gap: 6 },
  cardFooterText: { fontSize: 12, color: '#8b8aa0', fontWeight: '500' },
  alertRow: { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 16 },
  alertIconBg: { width: 44, height: 44, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.08)', alignItems: 'center', justifyContent: 'center' },
  alertText: { color: '#f8fafc', fontSize: 16, fontWeight: '700' },
  alertMeta: { color: '#8b8aa0', fontSize: 12, marginTop: 2 },
  emptyState: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 },
  mutedText: { color: '#8b8aa0', fontSize: 14, fontWeight: '500' },
  payoutRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  payoutIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255, 255, 255, 0.08)', alignItems: 'center', justifyContent: 'center' },
  payoutLabel: { fontSize: 14, fontWeight: '700', color: '#f8fafc' },
  payoutDate: { fontSize: 12, color: '#8b8aa0', marginTop: 2 },
  payoutAmount: { fontSize: 18, fontWeight: '800', color: '#f8fafc' },
  forecastRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)' },
  forecastDate: { color: '#f8fafc', fontWeight: '700', fontSize: 14 },
  forecastRisk: { color: '#a78bfa', fontWeight: '800', fontSize: 16 },
  forecastMeta: { color: '#8b8aa0', fontSize: 11, marginTop: 2 },
  alertSignalRow: { paddingVertical: 10, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)' },
  alertSignalTitle: { color: '#f8fafc', fontSize: 13, fontWeight: '600' },
  alertSignalMeta: { color: '#f59e0b', fontSize: 10, marginTop: 3, fontWeight: '700', letterSpacing: 0.6 },
  actionButtons: { flexDirection: 'row', gap: 12, marginTop: 4 },
  flexOne: { flex: 1 },
  ctaButton: { backgroundColor: '#f8fafc', borderRadius: 16, paddingHorizontal: 24, paddingVertical: 16, width: '100%', shadowColor: '#ffffff', shadowOpacity: 0.1, shadowRadius: 10 },
  ctaText: { color: '#09090b', fontSize: 16, fontWeight: '800', textAlign: 'center' },
  ctaSecondary: { backgroundColor: '#121218', borderRadius: 18, padding: 16, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  ctaSecondaryText: { color: '#f8fafc', fontSize: 15, fontWeight: '700' },
  ctaDanger: { backgroundColor: '#450a0a', borderRadius: 18, padding: 16, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', borderWidth: 1, borderColor: '#7f1d1d' },
  ctaDangerText: { color: '#fecaca', fontSize: 15, fontWeight: '700' },
  errorAlert: { backgroundColor: '#450a0a20', padding: 12, borderRadius: 12, borderWidth: 1, borderColor: '#ef444440' },
  errorText: { color: '#fca5a5', fontSize: 12, textAlign: 'center', fontWeight: '600' },
});
