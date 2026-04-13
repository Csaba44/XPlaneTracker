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

const isProfileModalOpen = ref(false);
const profileForm = ref({
  name: "",
  email: "",
  password: "",
});

const isEditFlightModalOpen = ref(false);
const editFlightForm = ref({
  id: null,
  callsign: "",
  flight_number: "",
  airline: "",
  dep_icao: "",
  arr_icao: "",
});

const fileInput = ref(null);
const isUploading = ref(false);

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

const triggerFileInput = () => {
  fileInput.value.click();
};

const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("flight_file", file);

  isUploading.value = true;

  try {
    const response = await api.post("/api/flights", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    flights.value.push(response.data);
    toast.success("Járat sikeresen feltöltve.");
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a járat feltöltésekor.");
  } finally {
    isUploading.value = false;
    event.target.value = null;
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

const openProfileModal = () => {
  profileForm.value = {
    name: authStore.user?.name || "",
    email: authStore.user?.email || "",
    password: "",
  };
  isProfileModalOpen.value = true;
};

const closeProfileModal = () => {
  isProfileModalOpen.value = false;
};

const saveProfile = async () => {
  try {
    const response = await api.put("/api/user/profile", profileForm.value);
    authStore.user = response.data;
    toast.success("Profil sikeresen frissítve.");
    closeProfileModal();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a profil frissítésekor.");
  }
};

const openEditFlightModal = (flight) => {
  editFlightForm.value = {
    id: flight.id,
    callsign: flight.callsign || "",
    flight_number: flight.flight_number || "",
    airline: flight.airline || "",
    dep_icao: flight.dep_icao || "",
    arr_icao: flight.arr_icao || "",
  };
  isEditFlightModalOpen.value = true;
};

const closeEditFlightModal = () => {
  isEditFlightModalOpen.value = false;
};

const saveFlight = async () => {
  try {
    const response = await api.put(`/api/flights/${editFlightForm.value.id}`, editFlightForm.value);

    const index = flights.value.findIndex((f) => f.id === editFlightForm.value.id);
    if (index !== -1) {
      flights.value[index] = { ...flights.value[index], ...response.data };
    }

    toast.success("Járat sikeresen frissítve.");
    closeEditFlightModal();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a járat frissítésekor.");
  }
};

const deleteFlight = async (id) => {
  if (!confirm("Biztosan törölni akarod ezt a járatot?")) return;

  try {
    await api.delete(`/api/flights/${id}`);

    flights.value = flights.value.filter((f) => f.id !== id);

    if (selectedFlightId.value === id) {
      selectedFlightId.value = null;
      currentFlightData.value = null;
    }

    toast.success("Járat sikeresen törölve.");
  } catch (error) {
    console.error(error);
    toast.error("Hiba történt a törlés során.");
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
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">CSABOLANTA</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <div class="flex flex-col space-y-2 mb-4">
          <div class="flex items-center justify-between bg-flight-card border border-flight-border p-3 rounded-lg">
            <div class="flex flex-col">
              <span class="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Szia testvér!</span>
              <span class="text-xs text-white font-bold truncate max-w-[120px]">
                {{ authStore.user?.name || authStore.user?.email || "Pilot" }}
              </span>
            </div>
            <div class="flex space-x-1">
              <button @click="openProfileModal" class="bg-flight-bg hover:bg-flight-accent/20 text-slate-400 hover:text-flight-accent transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Edit Profile">
                <i class="fa-solid fa-gear text-xs"></i>
              </button>
              <button @click="handleLogout" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Logout">
                <i class="fa-solid fa-right-from-bracket text-xs"></i>
              </button>
            </div>
          </div>

          <router-link v-if="authStore.user?.is_admin === 1" to="/admin" class="w-full text-center bg-purple-500/10 hover:bg-purple-500 text-purple-500 hover:text-white border border-purple-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider block"> Admin Panel </router-link>

          <button @click="generateApiKey" class="w-full bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">Generate API Key</button>

          <input type="file" accept=".gz" ref="fileInput" @change="handleFileUpload" style="display: none" />
          <button @click="triggerFileInput" :disabled="isUploading" class="w-full bg-green-500/10 hover:bg-green-500 text-green-500 hover:text-white border border-green-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer disabled:opacity-50 mt-2">
            {{ isUploading ? "Töltöm teso..." : "Manual PIREP" }}
          </button>

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
          <div class="flex justify-between items-start mb-3">
            <div class="flex flex-col">
              <span :class="['text-xl font-bold transition-colors', selectedFlightId === flight.id ? 'text-flight-accent' : 'text-white group-hover:text-flight-accent']">
                {{ flight.callsign }}
              </span>
              <div class="flex items-center space-x-2 mt-1 bg-black/30 w-fit px-2 py-0.5 rounded border border-white/5">
                <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.dep_icao || "----" }}</span>
                <i class="fa-solid fa-plane text-[9px] text-flight-accent"></i>
                <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.arr_icao || "----" }}</span>
              </div>
            </div>
            <span class="text-[10px] bg-flight-bg text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono">
              {{ flight.flight_number }}
            </span>
          </div>
          <div class="flex justify-between items-end text-xs text-slate-500">
            <div class="flex flex-col">
              <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
              <span class="text-[10px]">{{ new Date(flight.start_time).toLocaleDateString() }}</span>
            </div>

            <div class="flex items-center space-x-2">
              <button v-if="selectedFlightId === flight.id" @click.stop="deleteFlight(flight.id)" class="text-red-500/60 hover:text-red-500 transition-colors bg-red-500/5 hover:bg-red-500/20 p-1.5 rounded-md cursor-pointer" title="Delete Flight">
                <i class="fa-solid fa-trash"></i>
              </button>
              <button v-if="selectedFlightId === flight.id" @click.stop="openEditFlightModal(flight)" class="text-slate-400 hover:text-flight-accent transition-colors bg-white/5 hover:bg-flight-accent/10 p-1.5 rounded-md cursor-pointer" title="Edit Flight">
                <i class="fa-solid fa-pen"></i>
              </button>

              <button v-if="selectedFlightId === flight.id" @click.stop="shareFlight(flight.id)" class="text-flight-accent hover:text-white transition-colors bg-flight-accent/10 hover:bg-flight-accent p-1.5 rounded-md cursor-pointer" title="Share Flight">
                <i class="fa-solid fa-share-nodes"></i>
              </button>

              <i class="fa-solid fa-chevron-right text-slate-700 group-hover:text-flight-accent transition-colors ml-1"></i>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <FlightMap :flightData="currentFlightData" />

    <div v-if="isProfileModalOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm">
      <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">Profil</h2>

        <form @submit.prevent="saveProfile" class="space-y-4">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Username</label>
            <input v-model="profileForm.name" type="text" required class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Email</label>
            <input v-model="profileForm.email" type="email" required class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1"> Új jelszó <span class="text-slate-600 lowercase normal-case">(hagyd üresen a régihez)</span> </label>
            <input v-model="profileForm.password" type="password" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div class="flex space-x-3 pt-6">
            <button type="button" @click="closeProfileModal" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border cursor-pointer">Mégse</button>
            <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs cursor-pointer">Mentés</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="isEditFlightModalOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm">
      <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">Járat Szerkesztése</h2>

        <form @submit.prevent="saveFlight" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Callsign</label>
              <input v-model="editFlightForm.callsign" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
            </div>
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Flight Number</label>
              <input v-model="editFlightForm.flight_number" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
            </div>
          </div>

          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Airline</label>
            <input v-model="editFlightForm.airline" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">DEP ICAO</label>
              <input v-model="editFlightForm.dep_icao" type="text" pattern="[A-Za-z0-9]+" maxlength="4" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors uppercase" placeholder="E pl. LHBP" />
            </div>
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">ARR ICAO</label>
              <input v-model="editFlightForm.arr_icao" type="text" pattern="[A-Za-z0-9]+" maxlength="4" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors uppercase" placeholder="E pl. EGLL" />
            </div>
          </div>

          <div class="flex space-x-3 pt-6">
            <button type="button" @click="closeEditFlightModal" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border cursor-pointer">Mégse</button>
            <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs cursor-pointer">Mentés</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
