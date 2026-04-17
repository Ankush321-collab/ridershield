import { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Animated, { FadeInDown, FadeInUp, Layout } from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';

import { useAuth } from '../../contexts/AuthContext';
import { api, type PolicyQuoteResponse, type PolicyResponse } from '../../services/api';

const tierLabel = (tier: string) => tier.replace('_', ' ').toUpperCase();

const tierIcon = (tier: string) => {
  if (tier === 'essential') return 'shield-outline';
  if (tier === 'balanced') return 'shield-half';
  return 'shield-checkmark';
};

const tierColor = (tier: string) => {
  if (tier === 'essential') return '#b8b7c7';
  if (tier === 'balanced') return '#f8fafc';
  return '#10b981';
};

export default function PolicySelectScreen() {
  const { rider } = useAuth();
  const [quote, setQuote] = useState<PolicyQuoteResponse | null>(null);
  const [activePolicy, setActivePolicy] = useState<PolicyResponse | null>(null);
  const [selectedTier, setSelectedTier] = useState('balanced');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<'renew' | 'cancel' | null>(null);

  const fetchPolicyData = useCallback(async () => {
    let slots = '18:00-21:00,21:00-23:00';
    try {
      const stored = await AsyncStorage.getItem('rider_slots');
      if (stored) {
        const parsed: string[] = JSON.parse(stored);
        if (parsed.length > 0) slots = parsed.join(',');
      }
    } catch {}

    try {
      const [quoteData, activePolicyData] = await Promise.all([
        api.policies.getQuote(slots, rider?.city ?? ''),
        api.policies.getActive().catch(() => null),
      ]);
      setQuote(quoteData);
      setActivePolicy(activePolicyData);
      if (activePolicyData?.plan_tier) {
        setSelectedTier(activePolicyData.plan_tier);
      }
    } catch (error) {
      console.error('Error fetching policy state:', error);
    } finally {
      setLoading(false);
    }
  }, [rider?.city]);

  useEffect(() => {
    fetchPolicyData().catch(console.error);
  }, [fetchPolicyData]);

  useFocusEffect(
    useCallback(() => {
      fetchPolicyData().catch(console.error);
    }, [fetchPolicyData])
  );

  const selectedQuote = quote?.quotes.find((entry) => entry.tier === selectedTier) ?? quote?.quotes[0];

  const handleContinue = () => {
    if (!selectedQuote || !quote || activePolicy) return;

    router.push({
      pathname: '/policy/payment',
      params: {
        tier: selectedQuote.tier,
        price: String(selectedQuote.weekly_premium),
        coverage_pct: String(selectedQuote.coverage_pct),
        max_payout: String(selectedQuote.coverage_limit),
        slots_covered: String(selectedQuote.slots_covered),
        coverage_week: new Date().toISOString().slice(0, 10),
        zone_name: quote.zone_name,
      },
    });
  };

  const handleRenew = async () => {
    if (!activePolicy) return;
    setActionLoading('renew');
    try {
      console.log('Renewing with tier:', selectedTier, 'Policy ID:', activePolicy.policy_id);
      const response = await api.policies.renew(activePolicy.policy_id, selectedTier);
      console.log('Renewal response:', response);
      Alert.alert('Renewal scheduled', `Next week will use the ${tierLabel(selectedTier)} plan.`);
      await fetchPolicyData();
    } catch (error) {
      console.error('Renewal error:', error);
      const errorMsg = error instanceof Error ? error.message : JSON.stringify(error);
      Alert.alert('Renewal failed', errorMsg);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = () => {
    if (!activePolicy) return;
    Alert.alert(
      'Cancel current policy',
      'This will deactivate your current weekly policy immediately.',
      [
        { text: 'Keep Policy', style: 'cancel' },
        {
          text: 'Cancel Policy',
          style: 'destructive',
          onPress: async () => {
            setActionLoading('cancel');
            try {
              await api.policies.cancel(activePolicy.policy_id);
              setActivePolicy(null);
              Alert.alert('Policy cancelled', 'Your active weekly cover has been cancelled.');
              await fetchPolicyData();
            } catch (error) {
              Alert.alert('Cancellation failed', error instanceof Error ? error.message : 'Unable to cancel policy.');
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color="#f8fafc" />
        <Text style={styles.loadingText}>Calibrating parametric yield...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <LinearGradient 
        colors={['#09090b', '#000000', '#000000']} 
        style={StyleSheet.absoluteFill} 
      />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Animated.View entering={FadeInUp.duration(600).springify()}>
          <Text style={styles.title}>Secure Your Income</Text>
          <Text style={styles.subtitle}>Precision parametric coverage for your active perimeters.</Text>
        </Animated.View>

        {quote ? (
          <>
            {activePolicy ? (
              <Animated.View entering={FadeInDown.delay(100).springify()} style={styles.activePolicyCard}>
                <View style={styles.activePolicyHeader}>
                  <Text style={styles.activePolicyTitle}>Active Weekly Policy</Text>
                  <Text style={styles.activePolicyBadge}>{activePolicy.plan_tier.replace('_', ' ').toUpperCase()}</Text>
                </View>
                <Text style={styles.activePolicyMeta}>
                  Current premium: ₹{activePolicy.premium} • Claimed: ₹{activePolicy.coverage_used ?? 0} / ₹{activePolicy.coverage_limit}
                </Text>
                <Text style={styles.activePolicyMeta}>
                  Hours remaining: {activePolicy.hours_remaining ?? 0} • Week {activePolicy.coverage_week}
                </Text>
                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={[styles.secondaryActionBtn, actionLoading !== null && styles.actionDisabled]}
                    onPress={handleRenew}
                    disabled={actionLoading !== null}
                  >
                    <Text style={styles.secondaryActionText}>
                      {actionLoading === 'renew' ? 'Scheduling…' : `Renew Next Week (${tierLabel(selectedTier)})`}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.dangerActionBtn, actionLoading !== null && styles.actionDisabled]}
                    onPress={handleCancel}
                    disabled={actionLoading !== null}
                  >
                    <Text style={styles.dangerActionText}>
                      {actionLoading === 'cancel' ? 'Cancelling…' : 'Cancel Current'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </Animated.View>
            ) : null}

            <Animated.View entering={FadeInDown.delay(200).springify()} style={styles.riskCard}>
              <View style={styles.riskHeader}>
                <Ionicons name="location" size={16} color="#f59e0b" />
                <Text style={styles.riskTitle}>{quote.zone_name || rider?.zone || 'Selected Zone'} Alert</Text>
              </View>
              <Text style={styles.riskText}>Hazard Index: {quote.zone_risk_score}/100</Text>
              {quote.explanation ? <Text style={styles.riskSubtext}>{quote.explanation}</Text> : null}
            </Animated.View>

            <View style={styles.tierContainer}>
              {quote.quotes.map((tier, index) => {
                const color = tierColor(tier.tier);
                const isSelected = selectedTier === tier.tier;
                return (
                  <Animated.View key={tier.tier} entering={FadeInDown.delay(400 + index * 100).springify()} layout={Layout.springify()}>
                    <TouchableOpacity
                      activeOpacity={0.9}
                      style={[
                        styles.tierCard,
                        isSelected && { borderColor: color, backgroundColor: 'rgba(255,255,255,0.03)' },
                        tier.tier === 'balanced' && !isSelected && styles.recommendedBorder,
                      ]}
                      onPress={() => setSelectedTier(tier.tier)}
                    >
                      <BlurView tint="dark" intensity={isSelected ? 50 : 20} style={StyleSheet.absoluteFill} />
                      <View style={styles.tierContent}>
                        <View style={styles.tierHeader}>
                          <View style={[styles.iconFrame, { backgroundColor: `${color}20` }]}>
                          <Ionicons name={tierIcon(tier.tier) as any} size={24} color={color} />
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.tierName, { color }]}>{tierLabel(tier.tier)}</Text>
                          <Text style={styles.tierSub}>WEEKLY PROTECTION</Text>
                        </View>
                        <View style={styles.priceContainer}>
                          <Text style={styles.currency}>₹</Text>
                          <Text style={styles.price}>{tier.weekly_premium}</Text>
                        </View>
                      </View>

                      <View style={styles.divider} />

                      <View style={styles.featureRow}>
                        <Ionicons name="checkmark-circle" size={14} color="#10b981" />
                        <Text style={styles.featureText}>{tier.coverage_pct}% Yield Recovery</Text>
                      </View>
                      <View style={styles.featureRow}>
                        <Ionicons name="checkmark-circle" size={14} color="#10b981" />
                        <Text style={styles.featureText}>Max Recovery ₹{tier.coverage_limit}</Text>
                      </View>

                      {tier.tier === 'balanced' && (
                        <View style={styles.recBadge}>
                          <Text style={styles.recBadgeText}>PEER CHOICE</Text>
                        </View>
                      )}
                      </View>
                    </TouchableOpacity>
                  </Animated.View>
                );
              })}
            </View>

            <TouchableOpacity style={[styles.continueBtn, activePolicy && styles.actionDisabled]} onPress={handleContinue} disabled={!selectedQuote || !!activePolicy}>
              <Text style={styles.continueText}>{activePolicy ? 'Current Week Already Protected' : 'Initiate Protocol →'}</Text>
            </TouchableOpacity>
          </>
        ) : (
          <View style={styles.errorCard}>
            <Ionicons name="alert-circle" size={32} color="#f43f5e" />
            <Text style={styles.errorText}>Parametric link unstable. Retrying telemetry...</Text>
          </View>
        )}
        <View style={{ height: 120 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  center: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: '#8b8aa0', marginTop: 16, fontSize: 13, fontWeight: '700', letterSpacing: 1, textTransform: 'uppercase' },
  scroll: { padding: 24, gap: 24 },
  title: { fontSize: 32, fontWeight: '900', color: '#f8fafc', letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#8b8aa0', lineHeight: 22, fontWeight: '700' },
  activePolicyCard: { backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: 24, padding: 20, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  activePolicyHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  activePolicyTitle: { color: '#f8fafc', fontSize: 15, fontWeight: '900', letterSpacing: 0.8, textTransform: 'uppercase' },
  activePolicyBadge: { color: '#f8fafc', fontSize: 11, fontWeight: '900' },
  activePolicyMeta: { color: '#b8b7c7', fontSize: 13, lineHeight: 20, fontWeight: '600' },
  actionRow: { gap: 12, marginTop: 18 },
  secondaryActionBtn: { backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: 18, paddingVertical: 14, paddingHorizontal: 16, alignItems: 'center' },
  secondaryActionText: { color: '#f8fafc', fontSize: 13, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 0.7 },
  dangerActionBtn: { backgroundColor: 'rgba(244, 63, 94, 0.14)', borderRadius: 18, paddingVertical: 14, paddingHorizontal: 16, alignItems: 'center' },
  dangerActionText: { color: '#fecdd3', fontSize: 13, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 0.7 },
  actionDisabled: { opacity: 0.6 },
  riskCard: { backgroundColor: 'rgba(245, 158, 11, 0.05)', borderRadius: 24, padding: 20, borderWidth: 1, borderColor: 'rgba(245, 158, 11, 0.15)' },
  riskHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  riskTitle: { color: '#f59e0b', fontSize: 12, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 1 },
  riskText: { color: '#f8fafc', fontSize: 18, fontWeight: '800', marginBottom: 6 },
  riskSubtext: { color: '#b8b7c7', fontSize: 13, lineHeight: 18, fontWeight: '500' },
  tierContainer: { gap: 16 },
  tierCard: { backgroundColor: 'rgba(18, 18, 24, 0.72)', borderRadius: 32, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', position: 'relative', overflow: 'hidden' },
  tierContent: { padding: 24 },
  recommendedBorder: { borderColor: 'rgba(255, 255, 255, 0.2)', borderWidth: 1.5 },
  tierHeader: { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 20 },
  iconFrame: { width: 48, height: 48, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  tierName: { fontSize: 18, fontWeight: '900', letterSpacing: 0.5 },
  tierSub: { fontSize: 9, color: '#8b8aa0', fontWeight: '800', letterSpacing: 1, marginTop: 2 },
  priceContainer: { flexDirection: 'row', alignItems: 'baseline' },
  currency: { color: '#8b8aa0', fontSize: 14, fontWeight: '900', marginRight: 2 },
  price: { color: '#f8fafc', fontSize: 28, fontWeight: '900' },
  divider: { height: 1, backgroundColor: 'rgba(255,255,255,0.06)', marginBottom: 20 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  featureText: { color: '#b8b7c7', fontSize: 13, fontWeight: '700' },
  recBadge: { position: 'absolute', top: 0, right: 0, backgroundColor: 'rgba(255,255,255,0.08)', paddingHorizontal: 12, paddingVertical: 6, borderBottomLeftRadius: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  recBadgeText: { color: '#f8fafc', fontSize: 8, fontWeight: '900', letterSpacing: 1 },
  continueBtn: { backgroundColor: '#f8fafc', paddingVertical: 20, borderRadius: 24, alignItems: 'center', shadowColor: '#ffffff', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.1, shadowRadius: 20, elevation: 10 },
  continueText: { color: '#09090b', fontSize: 17, fontWeight: '900', letterSpacing: 1, textTransform: 'uppercase' },
  errorCard: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40, gap: 16 },
  errorText: { color: '#fca5a5', fontSize: 14, fontWeight: '700', textAlign: 'center' },
});
