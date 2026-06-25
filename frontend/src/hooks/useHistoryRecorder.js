import { useEffect } from 'react';
import axios from 'axios';

/**
 * useHistoryRecorder — Persists simulation snapshots to PostgreSQL every 10 seconds.
 * Authoritative write path complementing the live metrics stream.
 */
export const useHistoryRecorder = (metrics, noiseLevel, attackProbability, modelUsed = 'gradient_boosting') => {
  useEffect(() => {
    if (!metrics) return;

    const interval = setInterval(async () => {
      try {
        const payload = {
          noise_level: noiseLevel,
          attack_probability: attackProbability,
          final_qber: metrics.qber,
          sifted_key_length: metrics.sifted_key_length != null ? metrics.sifted_key_length : Math.floor(1000 * (1 - metrics.qber)),
          eve_qber_contribution: metrics.eve_qber_contribution != null ? metrics.eve_qber_contribution : Math.max(0, metrics.qber - ((2.0/3.0) * noiseLevel)),
          ml_prediction: metrics.threat_level || 'LOW',
          confidence_score: metrics.confidence_score || 0.99,
          model_used: modelUsed,
          actual_attack_status: attackProbability > 0
        };

        await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/history/record`, payload);
      } catch (err) {
        console.error('[useHistoryRecorder] Failed to record snapshot:', err);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [metrics, noiseLevel, attackProbability, modelUsed]);
};
