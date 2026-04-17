import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import Animated, { FadeInDown, FadeInUp } from 'react-native-reanimated';

import { api } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

export default function OtpScreen() {
  const { phone, devOtp } = useLocalSearchParams<{ phone: string; devOtp?: string }>();
  const { login, setTempToken } = useAuth();
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [latestDevOtp, setLatestDevOtp] = useState(devOtp || '');
  const [timer, setTimer] = useState(30);

  useEffect(() => {
    if (timer > 0) {
      const interval = setInterval(() => setTimer((t) => t - 1), 1000);
      return () => clearInterval(interval);
    }
  }, [timer]);

  const handleVerify = async () => {
    if (otp.length !== 6) {
      Alert.alert('Incomplete Signal', 'Please enter the 6-digit verification sequence.');
      return;
    }

    setErrorMsg('');
    setLoading(true);
    try {
      const result = await api.riders.verifyOtp(phone!, otp);
      if (result.valid) {
        if (result.is_registered && result.jwt_token) {
          await setTempToken(null);
          await login(result.jwt_token);
          router.replace('/(tabs)');
          return;
        }

        if (result.temp_token) {
          await setTempToken(result.temp_token);
          router.push({ pathname: '/(auth)/register', params: { phone } });
          return;
        }

        Alert.alert('System Mismatch', 'Unable to continue. Please retry transmission.');
      } else {
        setErrorMsg('Invalid OTP. Please try again.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (timer > 0) return;
    try {
      const response = await api.riders.sendOtp(phone!);
      setLatestDevOtp(response.dev_otp || '');
      setTimer(30);
      setErrorMsg('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to resend OTP.');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Animated.View entering={FadeInUp.delay(200).springify()}>
          <Text style={styles.title}>Secure Node Verification</Text>
          <Text style={styles.subtitle}>Sequence sent to {phone}. Enter the 6-digit decryption key below.</Text>
          {latestDevOtp ? (
            <Text style={styles.hint}>Demo OTP: {latestDevOtp}</Text>
          ) : (
            <Text style={styles.hint}>Dev OTP is available in backend logs when `DEBUG=true`.</Text>
          )}
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(400).springify()} style={styles.inputContainer}>
          <TextInput
            style={[styles.input, errorMsg ? styles.inputError : null]}
            value={otp}
            onChangeText={(value) => {
              setOtp(value.replace(/\D/g, ''));
              setErrorMsg('');
            }}
            keyboardType="number-pad"
            maxLength={6}
            placeholder="000 000"
            placeholderTextColor="#6f6e80"
            autoFocus
          />
          {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}
          <TouchableOpacity
            style={[styles.btn, (loading || otp.length !== 6) && styles.btnDisabled]}
            onPress={handleVerify}
            disabled={loading || otp.length !== 6}
          >
            {loading ? <ActivityIndicator color="#09090b" /> : <Text style={styles.btnText}>VALIDATE SIGNAL</Text>}
          </TouchableOpacity>
          <TouchableOpacity style={styles.resendContainer} onPress={handleResend} disabled={timer > 0}>
            <Text style={[styles.resendText, timer > 0 && styles.resendTextDisabled]}>
              {timer > 0 ? `Resend OTP in ${timer}s` : 'Resend OTP'}
            </Text>
          </TouchableOpacity>
        </Animated.View>

        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backText}>Cancel Protocol</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050507' },
  content: { flex: 1, padding: 32, justifyContent: 'center' },
  title: { fontSize: 32, fontWeight: '900', color: '#f8fafc', marginBottom: 12, letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#8b8aa0', lineHeight: 22, fontWeight: '600' },
  hint: { marginTop: 12, fontSize: 13, color: '#fbbf24', fontWeight: '700' },
  inputContainer: { marginTop: 40, gap: 20 },
  input: { backgroundColor: 'rgba(255,255,255,0.03)', color: '#f8fafc', borderRadius: 24, padding: 24, fontSize: 32, textAlign: 'center', fontWeight: '900', letterSpacing: 8, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  inputError: { borderColor: '#ef4444' },
  errorText: { color: '#fca5a5', fontSize: 13, textAlign: 'center', marginTop: -8 },
  btn: { backgroundColor: '#f8fafc', paddingVertical: 20, borderRadius: 20, shadowColor: '#ffffff', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.1, shadowRadius: 20, elevation: 10 },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#09090b', fontSize: 16, fontWeight: '900', textAlign: 'center', letterSpacing: 1 },
  resendContainer: { marginTop: 4, alignItems: 'center' },
  resendText: { color: '#f8fafc', fontSize: 15, fontWeight: '700' },
  resendTextDisabled: { color: '#8b8aa0' },
  backBtn: { marginTop: 24 },
  backText: { color: '#8b8aa0', textAlign: 'center', fontWeight: '800', textTransform: 'uppercase', fontSize: 12, letterSpacing: 1 },
});
