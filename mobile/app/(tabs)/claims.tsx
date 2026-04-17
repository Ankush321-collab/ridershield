import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, RefreshControl, ActivityIndicator, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown, Layout } from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { useFocusEffect } from '@react-navigation/native';

import { api, type ClaimListItem, type PayoutListItem } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { formatApiDateTime, parseApiDate } from '../../utils/datetime';
import Colors from '../../constants/Colors';

const { width } = Dimensions.get('window');

const disruptionEmoji = (type: string) => {
  switch (type) {
    case 'heavy_rain': return '🌧️';
    case 'traffic_congestion': return '🚗';
    case 'store_closure': return '🏪';
    case 'platform_outage': return '📱';
    case 'community_signal': return '📣';
    default: return '⚡';
  }
};

const statusConfig = (status: string) => {
  const value = status.toLowerCase();
  if (value === 'paid' || value === 'approved' || value === 'completed') {
    return { color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.2)' };
  }
  if (value === 'pending' || value === 'under_review') {
    return { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.2)' };
  }
  return { color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.1)', border: 'rgba(244, 63, 94, 0.2)' };
};

export default function ClaimsScreen() {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'claims' | 'payouts'>('claims');
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [payouts, setPayouts] = useState<PayoutListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token) return;
    setError(null);
    const [claimData, payoutData] = await Promise.all([
      api.claims.list(),
      api.payouts.list(),
    ]);
    setClaims(claimData.claims || []);
    setPayouts(payoutData.payouts || []);
  }, [token]);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    loadData()
      .catch((err) => {
        console.error(err);
        setError(err instanceof Error ? err.message : 'Telemetry sync failed.');
      })
      .finally(() => setLoading(false));
  }, [token, loadData]);

  useFocusEffect(
    useCallback(() => {
      if (!token) return;

      loadData().catch((err) => {
        console.error(err);
        setError(err instanceof Error ? err.message : 'Telemetry sync failed.');
      });
    }, [token, loadData])
  );

  const onRefresh = useCallback(async () => {
    if (!token) return;
    setRefreshing(true);
    try {
      await loadData();
    } catch (err) {
      setError('Telemetry sync failed.');
    } finally {
      setRefreshing(false);
    }
  }, [token, loadData]);

  const sortedClaims = useMemo(
    () =>
      [...claims].sort(
        (a, b) => (parseApiDate(b.created_at)?.getTime() || 0) - (parseApiDate(a.created_at)?.getTime() || 0)
      ),
    [claims]
  );

  if (loading && !refreshing) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color={Colors.dark.tint} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <LinearGradient 
        colors={['#09090b', '#000000', '#000000']} 
        style={StyleSheet.absoluteFill} 
      />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.dark.tint} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.toggleContainer}>
          <TouchableOpacity 
            style={[styles.toggleBtn, activeTab === 'claims' && styles.toggleBtnActive]} 
            onPress={() => setActiveTab('claims')}
          >
            <Text style={[styles.toggleText, activeTab === 'claims' && styles.toggleTextActive]}>Claims</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.toggleBtn, activeTab === 'payouts' && styles.toggleBtnActive]} 
            onPress={() => setActiveTab('payouts')}
          >
            <Text style={[styles.toggleText, activeTab === 'payouts' && styles.toggleTextActive]}>Payouts</Text>
          </TouchableOpacity>
        </View>

        {error ? <Text style={styles.errorBanner}>{error}</Text> : null}

        {activeTab === 'claims' ? (
          sortedClaims.length > 0 ? (
            sortedClaims.map((claim, index) => {
              const cfg = statusConfig(claim.status);
              return (
                <Animated.View 
                  key={claim.claim_id} 
                  entering={FadeInDown.delay(index * 100).springify()}
                  layout={Layout.springify()}
                  style={styles.cardWrapper}
                >
                  <BlurView tint="dark" intensity={30} style={StyleSheet.absoluteFill} />
                  <View style={styles.cardHeader}>
                     <View style={[styles.typeBadge, { backgroundColor: 'rgba(255,255,255,0.08)' }]}>
                        <Text style={styles.typeBadgeText}>{claim.type === 'manual' ? '📝 MANUAL' : '🤖 AUTO'}</Text>
                     </View>
                     <View style={[styles.statusBadge, { backgroundColor: cfg.bg, borderColor: cfg.border }]}>
                        <Text style={[styles.statusText, { color: cfg.color }]}>{claim.status.toUpperCase()}</Text>
                     </View>
                  </View>

                  <View style={styles.cardBody}>
                    <Text style={styles.claimTrigger}>
                       {disruptionEmoji(claim.disruption_type)} {claim.disruption_type.replace(/_/g, ' ').toUpperCase()}
                    </Text>
                    <View style={styles.amountContainer}>
                       <Text style={styles.currencySymbol}>₹</Text>
                       <Text style={styles.claimAmount}>{claim.payout_amount}</Text>
                    </View>
                  </View>

                  <View style={styles.cardFooter}>
                     <Text style={styles.footerLabel}>DATE: {formatApiDateTime(claim.created_at)}</Text>
                     <Text style={styles.footerLabel}>LOSS: ₹{claim.income_loss}</Text>
                  </View>
                </Animated.View>
              );
            })
          ) : (
            <View style={styles.emptyContainer}>
               <Text style={styles.emptyEmoji}>🛡️</Text>
               <Text style={styles.emptyTitle}>Secure Perimeters</Text>
               <Text style={styles.emptySubtitle}>No active disruptions detected. You're fully protected across all zones.</Text>
            </View>
          )
        ) : payouts.length > 0 ? (
          payouts.map((payout, index) => (
            <Animated.View 
              key={payout.payout_id} 
              entering={FadeInDown.delay(index * 100).springify()}
              style={styles.payoutCard}
            >
              <BlurView tint="dark" intensity={20} style={StyleSheet.absoluteFill} />
              <View style={styles.payoutContent}>
                <View style={styles.payoutHeader}>
                   <Text style={styles.payoutRef}>UPI/{payout.reference_id.slice(-8).toUpperCase()}</Text>
                   <Text style={styles.payoutStatus}>CREDITED</Text>
                </View>
                <View style={styles.payoutBody}>
                   <Text style={styles.payoutAmountText}>+₹{payout.amount}</Text>
                   <Text style={styles.payoutDate}>{formatApiDateTime(payout.created_at)}</Text>
                </View>
              </View>
            </Animated.View>
          ))
        ) : (
          <View style={styles.emptyContainer}>
             <Text style={styles.emptyEmoji}>🏦</Text>
             <Text style={styles.emptyTitle}>Vault Empty</Text>
             <Text style={styles.emptySubtitle}>No payout distributions recorded in this cycle.</Text>
          </View>
        )}
        <View style={{ height: 100 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20 },
  errorBanner: {
    color: '#fecaca',
    backgroundColor: 'rgba(127, 29, 29, 0.35)',
    borderColor: 'rgba(248, 113, 113, 0.25)',
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 16,
    fontSize: 13,
    fontWeight: '700',
  },
  toggleContainer: { flexDirection: 'row', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 24, padding: 6, marginBottom: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' },
  toggleBtn: { flex: 1, paddingVertical: 14, borderRadius: 20, alignItems: 'center' },
  toggleBtnActive: { backgroundColor: 'rgba(255,255,255,0.08)', shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 10, elevation: 5, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  toggleText: { color: '#71717a', fontWeight: '800', fontSize: 13, textTransform: 'uppercase', letterSpacing: 1 },
  toggleTextActive: { color: '#f8fafc', fontWeight: '900' },
  cardWrapper: { backgroundColor: 'rgba(18, 18, 24, 0.72)', borderRadius: 32, padding: 24, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  typeBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10 },
  typeBadgeText: { color: '#b8b7c7', fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  statusBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10, borderWidth: 1 },
  statusText: { fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },
  cardBody: { marginBottom: 20 },
  claimTrigger: { color: '#f8fafc', fontWeight: '900', fontSize: 18, marginBottom: 4, letterSpacing: -0.5 },
  amountContainer: { flexDirection: 'row', alignItems: 'baseline' },
  currencySymbol: { color: '#a1a1aa', fontSize: 18, fontWeight: '900', marginRight: 2 },
  claimAmount: { color: '#fff', fontSize: 40, fontWeight: '900', letterSpacing: -1 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)', paddingTop: 16 },
  footerLabel: { color: '#8b8aa0', fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  payoutCard: { backgroundColor: 'rgba(16, 185, 129, 0.05)', borderRadius: 28, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(16, 185, 129, 0.15)', overflow: 'hidden' },
  payoutContent: { padding: 24 },
  payoutHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  payoutRef: { color: '#8b8aa0', fontSize: 11, fontWeight: '900', letterSpacing: 1 },
  payoutStatus: { color: '#10b981', fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  payoutBody: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  payoutAmountText: { color: '#10b981', fontSize: 28, fontWeight: '900' },
  payoutDate: { color: '#8b8aa0', fontSize: 11, fontWeight: '700' },
  emptyContainer: { alignItems: 'center', justifyContent: 'center', paddingVertical: 60 },
  emptyEmoji: { fontSize: 48, marginBottom: 20, opacity: 0.2 },
  emptyTitle: { color: '#f8fafc', fontSize: 18, fontWeight: '900', marginBottom: 8 },
  emptySubtitle: { color: '#8b8aa0', fontSize: 14, textAlign: 'center', lineHeight: 22, maxWidth: 240 },
});
