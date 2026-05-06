import { ref } from 'vue';
import api from '../config/api';

const mappings = ref({}); // { simulator: { aircraft_icao: { index: label } } }

export function useFlapMappings() {
  const fetchMappings = async (simulator, aircraft_icao) => {
    try {
      if (!simulator || !aircraft_icao || aircraft_icao === 'unknown' || aircraft_icao.length !== 4) {
        return;
      }
      
      const response = await api.get('/api/flap-mappings', { 
        params: { simulator, aircraft_icao } 
      });
      
      if (!mappings.value[simulator]) {
        mappings.value[simulator] = {};
      }
      
      if (!mappings.value[simulator][aircraft_icao]) {
        mappings.value[simulator][aircraft_icao] = {};
      }
      
      response.data.forEach(m => {
        mappings.value[simulator][aircraft_icao][m.flap_index] = m.label;
      });
    } catch (error) {
      console.error('Failed to fetch flap mappings:', error);
    }
  };

  const getLabel = (simulator, aircraft_icao, index) => {
    if (!simulator || !aircraft_icao || aircraft_icao === 'unknown' || aircraft_icao.length !== 4 || index == null) {
      return null;
    }
    
    return mappings.value[simulator]?.[aircraft_icao]?.[String(index)] || null;
  };

  return {
    fetchMappings,
    getLabel,
    mappings,
  };
}
