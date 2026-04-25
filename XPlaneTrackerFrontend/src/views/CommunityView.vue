<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";

import FlightMap from "../components/FlightMap.vue";
import UserProfilePanel from "../components/UserProfilePanel.vue";
import FlightFilters from "../components/FlightFilters.vue";
import FlightCard from "../components/FlightCard.vue";
import ProfileModal from "../components/ProfileModal.vue";

const router = useRouter();
const authStore = useAuthStore();

const flights = ref([]);
const selectedFlightId = ref(null);
const currentFlightData = ref(null);
const generatedApiKey = ref(null);

const searchQuery = ref("");

const isProfileModalOpen = ref(false);
const isUploading = ref(false);

const filteredFlights = computed(() => {
  if (!searchQuery.value || searchQuery.value.trim() === "") {
    return flights.value;
  }

  const queryStr = searchQuery.value.toLowerCase();

  const tagRegex = /(dep|arr|callsign|type|reg):([^\s]+)/g;
  const tags = {
    dep: [],
    arr: [],
    callsign: [],
    type: [],
    reg: [],
  };

  let hasTags = false;
  const globalSearchText = queryStr
    .replace(tagRegex, (fullMatch, key, value) => {
      if (tags[key]) {
        tags[key].push(value);
        hasTags = true;
      }
      return "";
    })
    .trim();

  return flights.value.filter((flight) => {
    if (hasTags) {
      if (tags.dep.length > 0 && !tags.dep.some((val) => flight.dep_icao?.toLowerCase() === val)) return false;
      if (tags.arr.length > 0 && !tags.arr.some((val) => flight.arr_icao?.toLowerCase() === val)) return false;
      if (tags.callsign.length > 0 && !tags.callsign.some((val) => flight.callsign?.toLowerCase().includes(val))) return false;
      if (tags.type.length > 0 && !tags.type.some((val) => flight.aircraft_type?.toLowerCase().includes(val))) return false;
      if (tags.reg.length > 0 && !tags.reg.some((val) => flight.aircraft_registration?.toLowerCase().includes(val))) return false;
    }

    if (globalSearchText) {
      const gSearch = globalSearchText;
      const matchesGlobal = flight.callsign?.toLowerCase().includes(gSearch) || flight.flight_number?.toLowerCase().includes(gSearch) || flight.airline?.toLowerCase().includes(gSearch) || flight.dep_icao?.toLowerCase().includes(gSearch) || flight.arr_icao?.toLowerCase().includes(gSearch) || flight.user?.name?.toLowerCase().includes(gSearch);

      if (!matchesGlobal) return false;
    }

    return true;
  });
});

const clearFilters = () => {
  searchQuery.value = "";
};

const fetchFlights = async () => {
  try {
    const response = await api.get("/api/flights/friends");
    flights.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const viewFlight = async (id) => {
  selectedFlightId.value = id;
  try {
    const response = await api.get(`/api/flights/${id}`);
    currentFlightData.value = response.data.data;
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

const handleFileUpload = async (file) => {
  const formData = new FormData();
  formData.append("flight_file", file);

  isUploading.value = true;

  try {
    const response = await api.post("/api/flights", formData, {
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
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">SHAVALE</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <UserProfilePanel :user="authStore.user" :generatedApiKey="generatedApiKey" :isUploading="isUploading" @openProfile="isProfileModalOpen = true" @logout="handleLogout" @generateApiKey="generateApiKey" @uploadFile="handleFileUpload" />
      </div>

      <div class="px-4 pb-4">
        <FlightFilters v-model:searchQuery="searchQuery" :filteredCount="filteredFlights.length" :totalCount="flights.length" @clear="clearFilters" />
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
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
      </div>
    </aside>

    <FlightMap :flightData="currentFlightData" />

    <ProfileModal :isOpen="isProfileModalOpen" :initialData="authStore.user" @close="isProfileModalOpen = false" @save="saveProfile" />
  </div>
</template>
