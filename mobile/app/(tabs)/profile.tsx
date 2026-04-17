import { useEffect, useState } from 'react';
import { StyleSheet, TouchableOpacity, ScrollView, View, Text, Image, ActivityIndicator, Alert } from 'react-native';
import Animated, { FadeInUp, FadeInDown } from 'react-native-reanimated';
import { router } from 'expo-router';

import { useAuth } from '../../contexts/AuthContext';
import { api, type RiskProfile } from '../../services/api';
import Colors from '../../constants/Colors';

export default function ProfileScreen() {
  const { rider, logout } = useAuth();
  const [riskProfile, setRiskProfile] = useState<RiskProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    api.riders
      .getRiskProfile()
      .then(setRiskProfile)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const menuItems = [
    { icon: 'shield-account', label: 'Security Protocol', sub: 'Biometric and encrypted keys' },
    { icon: 'map-marker-radius', label: 'Active Zones', sub: `${rider?.zone || 'Primary'} perimeter` },
    { icon: 'bank-transfer', label: 'Payout Nodes', sub: `UPI: ${rider?.upi_id || 'Not linked'}` },
    { icon: 'bell-ring', label: 'Signal Alerts', sub: 'Parametric push enabled' },
  ];

  const avgYield = riskProfile?.four_week_earnings
    ? Object.values(riskProfile.four_week_earnings).reduce((a, b) => a + b, 0)
    : 0;

  const handleLogout = async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);

    try {
      await logout();
    } catch (err) {
      console.error('Failed to terminate session:', err);
      Alert.alert('Session Error', 'Could not fully clear local session. Redirecting to login.');
    } finally {
      router.replace('/');
      setIsLoggingOut(false);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Animated.View entering={FadeInUp.delay(200).springify()} style={styles.profileHeader}>
          <View style={styles.avatarContainer}>
            <Image
              source={{ uri: `https://api.dicebear.com/7.x/avataaars/svg?seed=${rider?.phone || 'default'}` }}
              style={styles.avatar}
            />
            <View style={styles.statusDot} />
          </View>
          <Text style={styles.name}>{rider?.name || 'Rider Node'}</Text>
          <Text style={styles.phone}>{rider?.phone || '+91 91234 56789'}</Text>

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statVal}>{rider?.trust_score ?? 100}</Text>
              <Text style={styles.statLabel}>TRUST</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={styles.statVal}>{riskProfile?.composite_risk_score ?? '--'}</Text>
              <Text style={styles.statLabel}>RISK INDEX</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statBox}>
              <Text style={styles.statVal}>Rs {avgYield}</Text>
              <Text style={styles.statLabel}>AVG YIELD</Text>
            </View>
          </View>
        </Animated.View>

        <View style={styles.riskGrid}>
          <Text style={styles.gridTitle}>ENVIRONMENTAL TELEMETRY</Text>
          {loading ? (
            <ActivityIndicator color={Colors.dark.tint} />
          ) : (
            <View style={styles.gridRow}>
              <View style={styles.gridItem}>
                <Text style={styles.gridVal}>{riskProfile?.zone_flood_risk ?? '--'}%</Text>
                <Text style={styles.gridLabel}>FLOOD RISK</Text>
              </View>
              <View style={styles.gridItem}>
                <Text style={styles.gridVal}>{riskProfile?.zone_traffic_risk ?? '--'}%</Text>
                <Text style={styles.gridLabel}>TRAFFIC INTENSITY</Text>
              </View>
            </View>
          )}
        </View>

        <View style={styles.menuContainer}>
          {menuItems.map((item, index) => (
            <Animated.View key={item.label} entering={FadeInDown.delay(400 + index * 100).springify()}>
              <TouchableOpacity style={styles.menuItem}>
                <View style={styles.menuIconContainer}>
                  <Text style={styles.menuIcon}>{item.icon}</Text>
                </View>
                <View style={styles.menuTextContainer}>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                  <Text style={styles.menuSub}>{item.sub}</Text>
                </View>
                <Text style={styles.chevron}>{'>'}</Text>
              </TouchableOpacity>
            </Animated.View>
          ))}
        </View>

        <Animated.View entering={FadeInDown.delay(900).springify()}>
          <TouchableOpacity 
            style={styles.logoutBtn} 
            onPress={handleLogout}
            disabled={isLoggingOut}
            activeOpacity={0.8}
          >
            <Text style={styles.logoutText}>{isLoggingOut ? 'Terminating...' : 'Terminate Session'}</Text>
          </TouchableOpacity>
          <Text style={styles.versionText}>System OS v2.4.0-STITCH</Text>
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  scroll: { padding: 24, paddingBottom: 120 },
  profileHeader: { alignItems: 'center', marginBottom: 32, marginTop: 20 },
  avatarContainer: { width: 100, height: 100, borderRadius: 36, backgroundColor: 'rgba(255, 255, 255, 0.08)', padding: 4, position: 'relative', marginBottom: 20 },
  avatar: { width: '100%', height: '100%', borderRadius: 32 },
  statusDot: { position: 'absolute', bottom: 4, right: 4, width: 20, height: 20, borderRadius: 10, backgroundColor: '#10b981', borderWidth: 4, borderColor: '#050507' },
  name: { fontSize: 24, fontWeight: '900', color: '#f8fafc', marginBottom: 4, letterSpacing: -0.5 },
  phone: { fontSize: 13, color: '#8b8aa0', fontWeight: '700', letterSpacing: 1 },
  statsRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 24, paddingVertical: 20, paddingHorizontal: 10, marginTop: 32, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' },
  statBox: { flex: 1, alignItems: 'center' },
  statVal: { color: '#f8fafc', fontSize: 18, fontWeight: '900' },
  statLabel: { color: '#8b8aa0', fontSize: 9, fontWeight: '800', marginTop: 4, letterSpacing: 1 },
  statDivider: { width: 1, height: 24, backgroundColor: 'rgba(255,255,255,0.08)' },
  riskGrid: { backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 24, padding: 20, marginBottom: 24, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.08)' },
  gridTitle: { color: '#6f6e80', fontSize: 10, fontWeight: '900', letterSpacing: 1.5, marginBottom: 16 },
  gridRow: { flexDirection: 'row', gap: 12 },
  gridItem: { flex: 1, backgroundColor: 'rgba(255,255,255,0.03)', padding: 16, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)' },
  gridVal: { color: '#f8fafc', fontSize: 20, fontWeight: '900' },
  gridLabel: { color: '#8b8aa0', fontSize: 8, fontWeight: '800', marginTop: 4, letterSpacing: 0.5 },
  menuContainer: { gap: 12, marginBottom: 40 },
  menuItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 24, padding: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)' },
  menuIconContainer: { width: 44, height: 44, borderRadius: 16, backgroundColor: 'rgba(255, 255, 255, 0.08)', alignItems: 'center', justifyContent: 'center', marginRight: 16 },
  menuIcon: { color: Colors.dark.tint, fontSize: 11, fontWeight: '700', textAlign: 'center' },
  menuTextContainer: { flex: 1 },
  menuLabel: { color: '#f8fafc', fontSize: 15, fontWeight: '800' },
  menuSub: { color: '#8b8aa0', fontSize: 11, fontWeight: '600', marginTop: 2 },
  chevron: { color: '#6f6e80', fontSize: 20, fontWeight: '700' },
  logoutBtn: { backgroundColor: 'rgba(244, 63, 94, 0.05)', paddingVertical: 20, borderRadius: 24, alignItems: 'center', borderWidth: 1, borderColor: 'rgba(244, 63, 94, 0.1)' },
  logoutText: { color: '#f43f5e', fontSize: 14, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 1 },
  versionText: { textAlign: 'center', color: 'rgba(255,255,255,0.08)', fontSize: 10, fontWeight: '800', marginTop: 24, letterSpacing: 1, textTransform: 'uppercase' },
});
