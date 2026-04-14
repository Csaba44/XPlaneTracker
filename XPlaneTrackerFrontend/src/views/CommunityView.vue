<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";

// Laravel Echo importok
import Echo from "laravel-echo";
import Pusher from "pusher-js";
window.Pusher = Pusher;

import FlightMap from "../components/FlightMap.vue";
import UserProfilePanel from "../components/UserProfilePanel.vue";
import FlightFilters from "../components/FlightFilters.vue";
import FlightCard from "../components/FlightCard.vue";
import ProfileModal from "../components/ProfileModal.vue";

const router = useRouter();
const authStore = useAuthStore();

const flights = ref([]); // Befejezett járatok
const selectedFlightId = ref(null);
const currentFlightData = ref(null);
const generatedApiKey = ref(null);

const friendsList = ref([]); // A nevekhez

// ÁLLAPOT KAPCSOLÓ: 'completed' vagy 'live'
const viewMode = ref("completed");
const liveFlightsMap = ref(new Map());
const echoInstance = ref(null);

const liveFlightsArray = computed(() => Array.from(liveFlightsMap.value.values()));

const searchQuery = ref("");
const selectedAirline = ref("");
const selectedRegistration = ref("");
const selectedFriend = ref("");

const isProfileModalOpen = ref(false);
const isUploading = ref(false);

const availableAirlines = computed(() => {
  const airlines = flights.value.map((f) => f.airline).filter(Boolean);
  return [...new Set(airlines)].sort();
});

const availableRegistrations = computed(() => {
  const registrations = flights.value.map((f) => f.aircraft_registration).filter(Boolean);
  return [...new Set(registrations)].sort();
});

const availableFriends = computed(() => {
  const friendsMap = new Map();
  flights.value.forEach((f) => {
    if (f.user) friendsMap.set(f.user.id, f.user);
  });
  return Array.from(friendsMap.values()).sort((a, b) => a.name.localeCompare(b.name));
});

const filteredFlights = computed(() => {
  return flights.value.filter((flight) => {
    const matchesSearch = !searchQuery.value || flight.callsign.toLowerCase().includes(searchQuery.value.toLowerCase()) || flight.flight_number.toLowerCase().includes(searchQuery.value.toLowerCase()) || flight.airline.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesAirline = !selectedAirline.value || flight.airline === selectedAirline.value;
    const matchesRegistration = !selectedRegistration.value || flight.aircraft_registration === selectedRegistration.value;
    const matchesFriend = !selectedFriend.value || flight.user_id === selectedFriend.value;

    return matchesSearch && matchesAirline && matchesRegistration && matchesFriend;
  });
});

const clearFilters = () => {
  searchQuery.value = "";
  selectedAirline.value = "";
  selectedRegistration.value = "";
  selectedFriend.value = "";
};

const getFriendName = (userId) => {
  if (userId === authStore.user?.id) return authStore.user.name + " (Te)";
  const friend = friendsList.value.find((f) => f.id === userId);
  return friend ? friend.name : `Kolléga #${userId}`;
};

// --- BEFEJEZETT JÁRATOK LEKÉRÉSE ---
const fetchFlights = async () => {
  try {
    const response = await api.get("/api/flights/friends");
    flights.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const fetchFriendsList = async () => {
  try {
    const response = await api.get("/api/friends");
    friendsList.value = response.data;
  } catch (e) {
    console.error(e);
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

// --- ÉLŐ JÁRATOK LOGIKÁJA ---
const fetchLiveFlights = async () => {
  try {
    const response = await api.get("/api/flights/live");
    liveFlightsMap.value.clear();
    response.data.forEach((flight) => {
      liveFlightsMap.value.set(flight.user_id, flight);
    });
  } catch (e) {
    console.error(e);
  }
};

const initEcho = () => {
  if (echoInstance.value) return;

  echoInstance.value = new Echo({
    broadcaster: "reverb",
    key: "xtracker-key", // Hardcoded to match your backend REVERB_APP_KEY
    wsHost: window.location.hostname, // Automatically resolves to xtracker.local or localhost
    wsPort: 8081, // The port mapped to your Reverb Docker container
    wssPort: 8081,
    forceTLS: false,
    disableStats: true,
    enabledTransports: ["ws", "wss"],
    authorizer: (channel, options) => {
      return {
        authorize: (socketId, callback) => {
          api
            .post("/broadcasting/auth", {
              socket_id: socketId,
              channel_name: channel.name,
            })
            .then((response) => callback(false, response.data))
            .catch((error) => callback(true, error));
        },
      };
    },
  });

  const listenToFriend = (id) => {
    echoInstance.value.private(`live-flight.${id}`).listen(".flight.updated", (e) => {
      const existing = liveFlightsMap.value.get(e.user_id) || { user_id: e.user_id, path: [] };
      existing.lat = e.lat;
      existing.lon = e.lon;
      existing.alt = e.alt;
      existing.gs = e.gs;
      existing.heading = e.heading;
      existing.timestamp = e.timestamp;

      existing.path.push([e.lat, e.lon, e.alt, e.timestamp]);

      liveFlightsMap.value.set(e.user_id, existing);

      if (selectedFlightId.value === `live_${e.user_id}`) {
        updateLiveFlightMapData(existing);
      }
    });
  };

  friendsList.value.forEach((friend) => listenToFriend(friend.id));
  if (authStore.user) listenToFriend(authStore.user.id);
};

const viewLiveFlight = (userId) => {
  selectedFlightId.value = `live_${userId}`;
  const flight = liveFlightsMap.value.get(userId);
  if (flight) {
    updateLiveFlightMapData(flight);
  }
};

const updateLiveFlightMapData = (flight) => {
  const mappedPath = flight.path.map((p) => [
    p[3], // timestamp
    p[0], // lat
    p[1], // lon
    p[2], // alt
    flight.gs, // gs
  ]);

  currentFlightData.value = {
    path: mappedPath,
    landings: [],
  };
};

// --- MODE VÁLTÓ ---
const toggleMode = async (mode) => {
  viewMode.value = mode;
  selectedFlightId.value = null;
  currentFlightData.value = null;
  clearFilters();

  if (mode === "live") {
    await fetchLiveFlights();
    initEcho();
  }
};

// --- ALAP FUNKCIÓK ---
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

const handleFileUpload = async (file) => {
  const formData = new FormData();
  formData.append("flight_file", file);

  isUploading.value = true;

  try {
    await api.post("/api/flights", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    toast.success("Járat sikeresen feltöltve a saját profilodhoz.");
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a járat feltöltésekor.");
  } finally {
    isUploading.value = false;
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

const saveProfile = async (formData) => {
  try {
    const response = await api.put("/api/user/profile", formData);
    authStore.user = response.data;
    toast.success("Profil sikeresen frissítve.");
    isProfileModalOpen.value = false;
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a profil frissítésekor.");
  }
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
  await fetchFriendsList();
  await fetchFlights();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl shrink-0">
      <div class="p-8 pb-4">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">SHAVALE</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <UserProfilePanel :user="authStore.user" :generatedApiKey="generatedApiKey" :isUploading="isUploading" @openProfile="isProfileModalOpen = true" @logout="handleLogout" @generateApiKey="generateApiKey" @uploadFile="handleFileUpload" />
      </div>

      <div class="px-4 pb-2">
        <div class="flex space-x-2 bg-flight-card/50 p-1 rounded-xl border border-flight-border/50">
          <button @click="toggleMode('completed')" :class="viewMode === 'completed' ? 'bg-flight-card border-flight-border shadow-lg text-white' : 'border-transparent text-slate-500 hover:text-slate-300'" class="flex-1 py-2 rounded-lg text-xs font-bold uppercase tracking-wider border transition-all cursor-pointer">Befejezett</button>
          <button @click="toggleMode('live')" :class="viewMode === 'live' ? 'bg-red-500/10 border-red-500/30 text-red-400 shadow-lg' : 'border-transparent text-slate-500 hover:text-slate-300'" class="flex-1 py-2 rounded-lg text-xs font-bold uppercase tracking-wider border transition-all flex items-center justify-center gap-2 cursor-pointer">
            <span v-if="viewMode === 'live'" class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span></span>
            Élő Radar
          </button>
        </div>
      </div>

      <div class="px-4 pb-4" v-show="viewMode === 'completed'">
        <FlightFilters v-model:searchQuery="searchQuery" v-model:selectedAirline="selectedAirline" v-model:selectedRegistration="selectedRegistration" v-model:selectedFriend="selectedFriend" :availableAirlines="availableAirlines" :availableRegistrations="availableRegistrations" :availableFriends="availableFriends" :showFriendFilter="true" :filteredCount="filteredFlights.length" :totalCount="flights.length" @clear="clearFilters" />
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
        <template v-if="viewMode === 'completed'">
          <div v-if="flights.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center">
            <i class="fa-solid fa-satellite-dish text-2xl mb-3 opacity-50"></i>
            <p class="text-sm italic">Még egy barátod sem repült...</p>
          </div>

          <div v-else-if="filteredFlights.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center bg-flight-card/50 rounded-xl border border-flight-border border-dashed">
            <i class="fa-solid fa-plane-slash text-2xl mb-3 opacity-50 text-teal-500"></i>
            <p class="text-sm font-bold text-slate-400">Nincs itt semmi.</p>
            <p class="text-[10px] uppercase tracking-widest mt-1">Nem találtam ilyet muro phral</p>
          </div>

          <FlightCard v-for="flight in filteredFlights" :key="flight.id" :flight="flight" :isSelected="selectedFlightId === flight.id" :isReadonly="true" @click="viewFlight(flight.id)" @share="shareFlight(flight.id)" />
        </template>

        <template v-else>
          <div v-if="liveFlightsArray.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center bg-red-500/5 rounded-xl border border-red-500/10 border-dashed">
            <i class="fa-solid fa-satellite text-2xl mb-3 opacity-50 text-red-500"></i>
            <p class="text-sm font-bold text-slate-400">Nincs élő kapcsolat.</p>
            <p class="text-[10px] uppercase tracking-widest mt-1">Mindenki a földön van</p>
          </div>

          <div v-for="flight in liveFlightsArray" :key="flight.user_id" @click="viewLiveFlight(flight.user_id)" :class="['p-4 rounded-xl cursor-pointer transition-all border group', selectedFlightId === `live_${flight.user_id}` ? 'bg-red-500/10 border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.15)]' : 'bg-flight-card border-flight-border hover:bg-flight-card-hover']">
            <div class="flex justify-between items-center mb-2">
              <span class="font-bold text-white text-base flex items-center gap-2">
                <i class="fa-solid fa-plane text-red-500 text-xs"></i>
                {{ getFriendName(flight.user_id) }}
              </span>
              <span class="text-[9px] bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-1 rounded font-bold uppercase tracking-widest animate-pulse">LIVE</span>
            </div>
            <div class="flex justify-between items-end text-xs font-mono text-slate-400">
              <div class="flex flex-col space-y-1">
                <span
                  >ALT: <span class="text-flight-accent">{{ flight.alt }} ft</span></span
                >
                <span
                  >GS: <span class="text-flight-accent">{{ flight.gs }} kts</span></span
                >
              </div>
              <span>HDG: {{ flight.heading }}°</span>
            </div>
          </div>
        </template>
      </div>
    </aside>

    <FlightMap :flightData="currentFlightData" :liveFlights="viewMode === 'live' ? liveFlightsArray : []" @flight-clicked="viewLiveFlight" />

    <ProfileModal :isOpen="isProfileModalOpen" :initialData="authStore.user" @close="isProfileModalOpen = false" @save="saveProfile" />
  </div>
</template>
