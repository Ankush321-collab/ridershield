import { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Keyboard, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import Animated, { FadeInUp, FadeInDown } from 'react-native-reanimated';

import { api } from '../../services/api';
import Colors from '../../constants/Colors';

interface Platform {
  id: string;
  name: string;
  icon: string;
}

export default function RegisterScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [name, setName] = useState('');
  const [platform, setPlatform] = useState('');
  const [upiId, setUpiId] = useState('');
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loadingConfig, setLoadingConfig] = useState(true);

  // DPDP Act 2023 — Explicit consent tracking
  const [consentGps, setConsentGps] = useState(false);
  const [consentUpi, setConsentUpi] = useState(false);
  const [consentPlatform, setConsentPlatform] = useState(false);

  // Fetch platforms from backend — single source of truth
  useEffect(() => {
    api.config.get()
      .then(cfg => setPlatforms(cfg.platforms))
      .catch(() => {
        // Falling back to hardcoded only if backend is unreachable
        setPlatforms([
          { id: 'zepto', name: 'Zepto', icon: '⚡' },
          { id: 'blinkit', name: 'Blinkit', icon: '📦' },
          { id: 'swiggy', name: 'Swiggy', icon: '🛵' },
        ]);
      })
      .finally(() => setLoadingConfig(false));
  }, []);

  const isUpiValid = upiId.length > 3 && /^[\w.-]+@[\w.-]+$/.test(upiId);
  const allConsentsGranted = consentGps && consentUpi && consentPlatform;
  const isValid = name.trim().length > 0 && platform !== '' && isUpiValid && allConsentsGranted;

  const handleNext = () => {
    router.push({
      pathname: '/(auth)/zone-select',
      params: { phone, name, platform, upiId },
    });
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          onScrollBeginDrag={Keyboard.dismiss}
          showsVerticalScrollIndicator={false}
        >
          <Animated.View entering={FadeInUp.delay(200).springify()}>
            <Text style={styles.title}>Identity Setup</Text>
            <Text style={styles.subtitle}>Initialize your rider profile to enable parametric security.</Text>
          </Animated.View>

          <View style={styles.form}>
            <Animated.View entering={FadeInDown.delay(400).springify()}>
              <Text style={styles.label}>OPERATOR NAME</Text>
              <TextInput
                style={styles.input}
                value={name}
                onChangeText={setName}
                placeholder="Enter full name"
                placeholderTextColor="#6f6e80"
              />
            </Animated.View>

            <Animated.View entering={FadeInDown.delay(600).springify()}>
              <Text style={styles.label}>FLEET PLATFORM</Text>
              {loadingConfig ? (
                <ActivityIndicator color={Colors.dark.tint} style={{ marginTop: 12 }} />
              ) : (
                <View style={styles.chips}>
                  {platforms.map((p) => (
                    <TouchableOpacity
                      key={p.id}
                      style={[styles.chip, platform === p.id && styles.chipActive]}
                      onPress={() => setPlatform(p.id)}
                      activeOpacity={0.7}
                    >
                      <Text style={styles.chipIcon}>{p.icon}</Text>
                      <Text style={[styles.chipText, platform === p.id && styles.chipTextActive]}>{p.name}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </Animated.View>

            <Animated.View entering={FadeInDown.delay(800).springify()}>
              <Text style={styles.label}>REDISTRIBUTION UPI ID</Text>
              <TextInput
                style={styles.input}
                value={upiId}
                onChangeText={setUpiId}
                placeholder="rider@okaxis"
                placeholderTextColor="#6f6e80"
                autoCapitalize="none"
              />
              {upiId.length > 0 && !isUpiValid && (
                 <Text style={styles.errorHint}>Invalid UPI format (e.g. name@bank)</Text>
              )}
            </Animated.View>

            {/* ── DPDP Act, 2023 — Data Consent ──────────────────── */}
            <Animated.View entering={FadeInDown.delay(950).springify()}>
              <Text style={styles.label}>DATA CONSENT (DPDP ACT, 2023)</Text>
              <Text style={styles.consentSubtitle}>
                Your data is processed only for claim verification and payout disbursement.
              </Text>

              <TouchableOpacity
                style={styles.consentRow}
                onPress={() => setConsentGps(!consentGps)}
                activeOpacity={0.7}
              >
                <View style={[styles.checkbox, consentGps && styles.checkboxChecked]}>
                  {consentGps && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <Text style={styles.consentText}>
                  I consent to GPS location collection to verify my presence in the delivery zone for claim processing.
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.consentRow}
                onPress={() => setConsentUpi(!consentUpi)}
                activeOpacity={0.7}
              >
                <View style={[styles.checkbox, consentUpi && styles.checkboxChecked]}>
                  {consentUpi && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <Text style={styles.consentText}>
                  I consent to UPI/bank account data processing for automatic payout disbursement.
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.consentRow}
                onPress={() => setConsentPlatform(!consentPlatform)}
                activeOpacity={0.7}
              >
                <View style={[styles.checkbox, consentPlatform && styles.checkboxChecked]}>
                  {consentPlatform && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <Text style={styles.consentText}>
                  I consent to platform activity data sharing to confirm active delivery days and earnings baseline.
                </Text>
              </TouchableOpacity>
            </Animated.View>

            <Animated.View entering={FadeInDown.delay(1100).springify()} style={{ marginTop: 24 }}>
              <TouchableOpacity
                style={[styles.button, !isValid && styles.buttonDisabled]}
                onPress={handleNext}
                disabled={!isValid}
              >
                <Text style={styles.buttonText}>ESTABLISH PERIMETERS →</Text>
              </TouchableOpacity>
              {!allConsentsGranted && name.trim().length > 0 && (
                <Text style={styles.consentHint}>All data consents are required to proceed</Text>
              )}
            </Animated.View>
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  scroll: { padding: 32, paddingBottom: 60 },
  title: { fontSize: 32, fontWeight: '900', color: '#f8fafc', letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#8b8aa0', lineHeight: 22, fontWeight: '600', marginTop: 8 },
  form: { marginTop: 40, gap: 24 },
  label: { color: Colors.dark.tint, fontSize: 10, fontWeight: '900', letterSpacing: 2, marginBottom: 8 },
  input: { backgroundColor: 'rgba(255,255,255,0.03)', color: '#f8fafc', borderRadius: 20, padding: 18, fontSize: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', fontWeight: '700' },
  errorHint: { color: '#f43f5e', fontSize: 10, fontWeight: '800', marginTop: 8, letterSpacing: 0.5 },
  chips: { flexDirection: 'row', gap: 10, flexWrap: 'wrap' },
  chip: { flexDirection: 'row', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 16, paddingVertical: 14, paddingHorizontal: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', alignItems: 'center', gap: 8 },
  chipActive: { backgroundColor: 'rgba(255, 255, 255, 0.1)', borderColor: 'rgba(255, 255, 255, 0.3)' },
  chipIcon: { fontSize: 16 },
  chipText: { color: '#8b8aa0', fontWeight: '800', fontSize: 13 },
  chipTextActive: { color: '#f8fafc' },
  button: { backgroundColor: '#f8fafc', borderRadius: 24, paddingVertical: 22, alignItems: 'center', shadowColor: '#ffffff', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.1, shadowRadius: 20, elevation: 10 },
  buttonDisabled: { opacity: 0.2, shadowOpacity: 0 },
  buttonText: { color: '#09090b', fontSize: 15, fontWeight: '900', letterSpacing: 1 },
  // DPDP Act 2023 Consent styles
  consentSubtitle: { color: '#6f6e80', fontSize: 11, lineHeight: 16, marginBottom: 16, fontWeight: '500' },
  consentRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginBottom: 16, paddingRight: 8 },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.15)', backgroundColor: 'rgba(255,255,255,0.03)', alignItems: 'center', justifyContent: 'center', marginTop: 1 },
  checkboxChecked: { backgroundColor: 'rgba(16,185,129,0.2)', borderColor: '#10b981' },
  checkmark: { color: '#10b981', fontSize: 13, fontWeight: '900' },
  consentText: { flex: 1, color: '#a1a0b4', fontSize: 12, lineHeight: 18, fontWeight: '600' },
  consentHint: { color: '#f59e0b', fontSize: 10, fontWeight: '700', textAlign: 'center', marginTop: 12, letterSpacing: 0.3 },
});
