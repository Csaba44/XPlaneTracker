<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";
import FlightMap from "../components/FlightMap.vue";

const router = useRouter();
const authStore = useAuthStore();

const flights = ref([]);
const selectedFlightId = ref(null);
const currentFlightData = ref(null);
const generatedApiKey = ref(null);

const searchQuery = ref("");
const selectedAirline = ref("");

const altitudeTiers = [
  { alt: 0, label: "0 - 1k", color: "#ef4444" },
  { alt: 1000, label: "1k - 5k", color: "#f97316" },
  { alt: 5000, label: "5k - 15k", color: "#eab308" },
  { alt: 15000, label: "15k - 25k", color: "#22c55e" },
  { alt: 25000, label: "25k - 35k", color: "#06b6d4" },
  { alt: 35000, label: "35k+", color: "#3b82f6" },
];

const availableAirlines = computed(() => {
  const airlines = flights.value.map((f) => f.airline).filter(Boolean);
  return [...new Set(airlines)].sort();
});

const filteredFlights = computed(() => {
  return flights.value.filter((flight) => {
    const matchesSearch = !searchQuery.value || flight.callsign.toLowerCase().includes(searchQuery.value.toLowerCase()) || flight.flight_number.toLowerCase().includes(searchQuery.value.toLowerCase()) || flight.airline.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesAirline = !selectedAirline.value || flight.airline === selectedAirline.value;
    return matchesSearch && matchesAirline;
  });
});

const clearFilters = () => {
  searchQuery.value = "";
  selectedAirline.value = "";
};

const fetchFlights = async () => {
  try {
    const response = await api.get("/api/flights");
    flights.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const viewFlight = async (id) => {
  selectedFlightId.value = id;
  try {
    const response = await api.get(`/api/flights/${id}`);
    currentFlightData.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const handleLogout = async () => {
  try {
    await authStore.logout();
    router.push("/login");
  } catch (error) {
    console.error(error);
  }
};

const generateApiKey = async () => {
  try {
    const response = await api.post("/api/tokens/create");
    generatedApiKey.value = response.data.token;
  } catch (error) {
    console.error(error);
  }
};

const shareFlight = async (id) => {
  const url = `${window.location.origin}/flight/${id}`;

  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Vágólapra másolva.");
    } catch (err) {
      prompt("Másold ki:", url);
    }
  } else {
    const textArea = document.createElement("textarea");
    textArea.value = url;

    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand("copy");
      toast.success("Vágólapra másolva.");
    } catch (err) {
      prompt("Másold ki:", url);
    } finally {
      textArea.remove();
    }
  }
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
  await fetchFlights();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8 pb-4">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">X-TRACKER</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <div class="flex flex-col space-y-2 mb-4">
          <div class="flex items-center justify-between bg-flight-card border border-flight-border p-3 rounded-lg">
            <div class="flex flex-col">
              <span class="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Szia testvér!</span>
              <span class="text-xs text-white font-bold truncate max-w-[120px]">
                {{ authStore.user?.email || "Pilot" }}
              </span>
            </div>
            <button @click="handleLogout" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Logout">
              <i class="fa-solid fa-right-from-bracket text-xs"></i>
            </button>
          </div>

          <button @click="generateApiKey" class="w-full bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">Generate API Key</button>

          <div v-if="generatedApiKey" class="bg-black/50 p-3 rounded-lg border border-flight-border mt-2">
            <p class="text-[10px] text-red-400 font-bold uppercase mb-1">Vigyázz rá testvérem, el ne lopják a cigányok!</p>
            <code class="text-[10px] text-flight-accent break-all select-all">{{ generatedApiKey }}</code>
          </div>
        </div>
      </div>

      <div class="px-4 pb-4">
        <div class="bg-flight-card border border-flight-border rounded-xl p-3 space-y-3 shadow-lg">
          <div class="relative">
            <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500 text-xs"></i>
            <input v-model="searchQuery" type="text" placeholder="Keresés..." class="w-full bg-flight-bg border border-flight-border rounded-lg pl-8 pr-3 py-2 text-xs text-white focus:outline-none focus:border-flight-accent transition-colors placeholder-slate-600" />
          </div>

          <div class="flex space-x-2">
            <select v-model="selectedAirline" class="flex-grow bg-flight-bg border border-flight-border rounded-lg px-2 py-2 text-xs text-slate-300 focus:outline-none focus:border-flight-accent transition-colors cursor-pointer">
              <option value="">Összes</option>
              <option v-for="airline in availableAirlines" :key="airline" :value="airline">{{ airline }}</option>
            </select>

            <button v-if="searchQuery || selectedAirline" @click="clearFilters" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/20 px-3 rounded-lg text-xs transition-colors flex items-center justify-center cursor-pointer" title="Clear Filters">
              <i class="fa-solid fa-filter-circle-xmark"></i>
            </button>
          </div>

          <div class="flex justify-between items-center text-[9px] text-slate-500 font-bold uppercase tracking-widest pt-1 border-t border-flight-border/50">
            <span
              >Találat: <span class="text-flight-accent">{{ filteredFlights.length }}</span></span
            >
            <span v-if="flights.length > 0">Összesen: {{ flights.length }}</span>
          </div>
        </div>
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
        <div v-if="flights.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center">
          <i class="fa-solid fa-satellite-dish text-2xl mb-3 opacity-50"></i>
          <p class="text-sm italic">Keresem tesó, várj egy picit...</p>
        </div>

        <div v-else-if="filteredFlights.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center bg-flight-card/50 rounded-xl border border-flight-border border-dashed">
          <i class="fa-solid fa-plane-slash text-2xl mb-3 opacity-50 text-flight-accent"></i>
          <p class="text-sm font-bold text-slate-400">Nincs itt semmi.</p>
          <p class="text-[10px] uppercase tracking-widest mt-1">Nem találtam ilyet muro phral</p>
        </div>

        <div v-for="flight in filteredFlights" :key="flight.id" @click="viewFlight(flight.id)" :class="['p-5 rounded-xl cursor-pointer transition-all duration-300 border group', selectedFlightId === flight.id ? 'bg-flight-card border-flight-accent shadow-[0_0_20px_rgba(56,189,248,0.1)]' : 'bg-transparent border-transparent hover:bg-flight-card-hover']">
          <div class="flex justify-between items-center mb-3">
            <span :class="['text-xl font-bold transition-colors', selectedFlightId === flight.id ? 'text-flight-accent' : 'text-white group-hover:text-flight-accent']">
              {{ flight.callsign }}
            </span>
            <span class="text-[10px] bg-flight-bg text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono">
              {{ flight.flight_number }}
            </span>
          </div>
          <div class="flex justify-between items-end text-xs text-slate-500">
            <div class="flex flex-col">
              <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
              <span class="text-[10px]">{{ new Date(flight.start_time).toLocaleDateString() }}</span>
            </div>

            <div class="flex items-center space-x-3">
              <button v-if="selectedFlightId === flight.id" @click.stop="shareFlight(flight.id)" class="text-flight-accent hover:text-white transition-colors bg-flight-accent/10 hover:bg-flight-accent p-1.5 rounded-md cursor-pointer" title="Share Flight">
                <i class="fa-solid fa-share-nodes"></i>
              </button>
              <i class="fa-solid fa-chevron-right text-slate-700 group-hover:text-flight-accent transition-colors"></i>
            </div>
          </div>
        </div>
      </div>

      <div class="p-6 bg-black/40 border-t border-flight-border">
        <h4 class="text-[10px] font-bold text-slate-500 mb-4 uppercase tracking-widest flex items-center"><i class="fa-solid fa-layer-group mr-2 text-flight-accent"></i> Altitude MSL (FT)</h4>
        <div class="grid grid-cols-2 gap-x-4 gap-y-2">
          <div v-for="tier in altitudeTiers" :key="tier.alt" class="flex items-center space-x-3">
            <div class="w-2.5 h-2.5 rounded-sm" :style="{ backgroundColor: tier.color }"></div>
            <span class="text-[11px] text-slate-400 font-medium">{{ tier.label }}</span>
          </div>
        </div>
      </div>
    </aside>

    <FlightMap :flightData="currentFlightData" />
  </div>
</template>
