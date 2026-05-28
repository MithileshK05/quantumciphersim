import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

/**
 * useQKDMetrics — Live polling hook for the QuantumCipherSim backend.
 *
 * Unified Patch v2 Changes:
 * - Removed `notifyOnChangeProps` restriction: was silently swallowing re-renders
 *   when backend returned data that appeared structurally identical.
 * - Added `structuralSharing: false`: forces React Query to treat every poll
 *   response as a new object, guaranteeing a re-render on every tick.
 *   This is the frontend complement to the backend thermal noise injection.
 * - Poll interval kept at 1000ms.
 */
export const useQKDMetrics = (
  noiseLevel = 0.05,
  attackProbability = 0.0,
  activeModel = 'gradient_boosting',
  autoMitigate = false,
  activeProtocol = 'BB84'
) => {
  return useQuery({
    queryKey: ['qkdMetrics', noiseLevel, attackProbability, activeModel, autoMitigate, activeProtocol],
    queryFn: async () => {
      const response = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/metrics`, {
        params: {
          noise_level: noiseLevel,
          attack_probability: attackProbability,
          model_type: activeModel,
          auto_mitigate: autoMitigate,
          active_protocol: activeProtocol
        }
      });
      return response.data;
    },
    refetchInterval: 1000,
    staleTime: 0,              // Always consider data stale → always re-fetch
    structuralSharing: false,  // Never deduplicate: treat every response as new
  });
};
