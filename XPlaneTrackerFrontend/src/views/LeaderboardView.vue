<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";

import UserProfilePanel from "../components/UserProfilePanel.vue";
import ProfileModal from "../components/ProfileModal.vue";

const router = useRouter();
const authStore = useAuthStore();

const airportLeaderboards = ref([]);
const topHours = ref([]);
const isLoading = ref(true);
const generatedApiKey = ref(null);
const isProfileModalOpen = ref(false);

const fetchLeaderboard = async () => {
  try {
    const response = await api.get("/api/leaderboard");
    airportLeaderboards.value = response.data.airports;
    topHours.value = response.data.top_hours;
  } catch (error) {
    console.error(error);
    toast.error("Hiba a ranglista betöltésekor.");
  } finally {
    isLoading.value = false;
  }
};

const openFlight = (id) => {
  window.open(`/flight/${id}`, "_blank");
};

const getFpmColor = (fpm) => {
  const val = Math.abs(fpm);
  if (val <= 150) return "text-emerald-400";
  if (val <= 300) return "text-flight-accent";
  if (val <= 500) return "text-amber-400";
  return "text-red-500";
};

const handleLogout = async () => {
  try {
    await authStore.logout();
    router.push("/login");
  } catch (error) {
    console.error(error);
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
    toast.error("Hiba a profil frissítésekor.");
  }
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
  await fetchLeaderboard();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8 pb-4">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">TOP Pujarok</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">A legkomolyabbak 🏆</p>
          </div>
        </div>

        <router-link to="/flights" class="w-full flex items-center justify-center space-x-2 bg-flight-card hover:bg-flight-card-hover border border-flight-border transition-colors p-3 rounded-xl text-xs font-bold uppercase tracking-wider text-white mb-4">
          <i class="fa-solid fa-plane"></i>
          <span>Vissza a járatokhoz</span>
        </router-link>
      </div>
    </aside>

    <main class="flex-grow overflow-y-auto p-10 relative">
      <div class="max-w-6xl mx-auto">
        <div class="mb-10">
          <h1 class="text-3xl font-black text-white italic uppercase tracking-tighter flex items-center"><i class="fa-solid fa-ranking-star text-flight-accent mr-4 text-4xl"></i> Havi Ranglista</h1>
          <p class="text-slate-500 font-bold uppercase tracking-widest text-[10px] mt-2 ml-14">Az elmúlt 30 nap statisztikái</p>
        </div>

        <div v-if="isLoading" class="text-center py-20 text-slate-500">
          <i class="fa-solid fa-spinner fa-spin text-3xl mb-4 text-flight-accent"></i>
          <p class="text-sm italic">Adatok betöltése...</p>
        </div>

        <div v-else>
          <div v-if="topHours.length > 0" class="mb-12 bg-flight-card border border-flight-border rounded-xl shadow-2xl overflow-hidden">
            <div class="bg-black/20 px-6 py-4 border-b border-flight-border flex items-center">
              <i class="fa-solid fa-stopwatch text-2xl text-teal-400 mr-3"></i>
              <h2 class="text-xl font-black text-white tracking-widest">MOST FLIGHT HOURS</h2>
            </div>

            <div class="p-6">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="text-slate-500 text-[10px] uppercase tracking-widest border-b border-flight-border">
                    <th class="py-3 px-4 w-16 text-center">Rank</th>
                    <th class="py-3 px-4">Pilot</th>
                    <th class="py-3 px-4 text-right">Total Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(pilot, index) in topHours" :key="pilot.user_id" class="border-b border-flight-border/20 last:border-0 hover:bg-flight-sidebar/30 transition-colors">
                    <td class="py-4 px-4 text-xs font-black text-slate-600 text-center">
                      <span>#{{ index + 1 }}</span>
                    </td>
                    <td class="py-4 px-4 text-sm font-bold text-white"><i class="fa-solid fa-user text-[10px] text-teal-400 mr-2 opacity-70"></i>{{ pilot.user_name }}</td>
                    <td class="py-4 px-4 text-sm text-right font-mono font-black text-flight-accent">{{ Number(pilot.hours).toFixed(1) }} <span class="text-[10px] text-slate-500 font-sans tracking-widest">Hours</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 v-if="airportLeaderboards.length > 0" class="text-xl font-black text-white italic mb-6 uppercase tracking-tighter border-b border-flight-border/50 pb-3"><i class="fa-solid fa-plane-arrival text-flight-accent mr-3"></i> Top Landings by Airport</h3>

          <div v-if="airportLeaderboards.length === 0" class="text-center py-20 text-slate-500 bg-flight-card/50 rounded-xl border border-flight-border border-dashed">
            <i class="fa-solid fa-plane-slash text-4xl mb-4 text-flight-accent opacity-50"></i>
            <p class="text-lg font-bold text-slate-400">Nincs elég adat a leszállási ranglistához.</p>
            <p class="text-[10px] uppercase tracking-widest mt-2">Legalább 2 pilóta landolása szükséges egy adott reptéren az elmúlt 30 napban.</p>
          </div>

          <div v-for="airport in airportLeaderboards" :key="airport.icao" class="mb-12 bg-flight-card border border-flight-border rounded-xl shadow-2xl overflow-hidden">
            <div class="bg-black/20 px-6 py-4 border-b border-flight-border flex items-center">
              <i class="fa-solid fa-location-crosshairs text-2xl text-flight-accent mr-3"></i>
              <h2 class="text-2xl font-black text-white tracking-widest">{{ airport.icao }}</h2>
            </div>

            <div class="p-6 overflow-x-auto">
              <table class="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr class="text-slate-500 text-[10px] uppercase tracking-widest border-b border-flight-border">
                    <th class="py-3 px-2 w-16 text-center">Rank</th>
                    <th class="py-3 px-2">Pilot (Best FPM)</th>
                    <th class="py-3 px-2">A/C Type</th>
                    <th class="py-3 px-4 text-right">FPM</th>
                    <th class="py-3 px-4 w-4 border-r border-flight-border/50"></th>
                    <th class="py-3 px-4">Pilot (Best G)</th>
                    <th class="py-3 px-2">A/C Type</th>
                    <th class="py-3 px-4 text-right">G-Force</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="i in 5" :key="i" class="border-b border-flight-border/20 last:border-0 group hover:bg-flight-sidebar/30 transition-colors">
                    <td class="py-4 px-2 text-xs font-black text-slate-600 group-hover:text-flight-accent transition-colors text-center">#{{ i }}</td>

                    <template v-if="airport.top_fpm[i - 1]">
                      <td class="py-4 px-2">
                        <span @click="openFlight(airport.top_fpm[i - 1].flight_id)" class="text-white text-sm cursor-pointer hover:text-flight-accent transition-colors font-bold"> <i class="fa-solid fa-user text-[10px] text-teal-400 mr-2 opacity-70"></i>{{ airport.top_fpm[i - 1].user_name }} </span>
                      </td>
                      <td class="py-4 px-2">
                        <span class="text-[10px] text-slate-400 font-mono uppercase bg-white/5 border border-white/5 rounded px-2 py-1">{{ airport.top_fpm[i - 1].aircraft_type || "N/A" }}</span>
                      </td>
                      <td class="py-4 px-4 text-sm text-right font-mono font-black" :class="getFpmColor(airport.top_fpm[i - 1].fpm)">
                        {{ airport.top_fpm[i - 1].fpm }}
                      </td>
                    </template>
                    <template v-else>
                      <td class="py-4 px-2 text-slate-700 italic text-xs">-</td>
                      <td class="py-4 px-2"></td>
                      <td class="py-4 px-4"></td>
                    </template>

                    <td class="py-4 px-4 border-r border-flight-border/50"></td>

                    <template v-if="airport.top_g[i - 1]">
                      <td class="py-4 px-4">
                        <span @click="openFlight(airport.top_g[i - 1].flight_id)" class="text-white text-sm cursor-pointer hover:text-flight-accent transition-colors font-bold"> <i class="fa-solid fa-user text-[10px] text-teal-400 mr-2 opacity-70"></i>{{ airport.top_g[i - 1].user_name }} </span>
                      </td>
                      <td class="py-4 px-2">
                        <span class="text-[10px] text-slate-400 font-mono uppercase bg-white/5 border border-white/5 rounded px-2 py-1">{{ airport.top_g[i - 1].aircraft_type || "N/A" }}</span>
                      </td>
                      <td class="py-4 px-4 text-sm text-right font-mono font-black text-amber-400">{{ Number(airport.top_g[i - 1].g_force).toFixed(2) }}G</td>
                    </template>
                    <template v-else>
                      <td class="py-4 px-4 text-slate-700 italic text-xs">-</td>
                      <td class="py-4 px-2"></td>
                      <td class="py-4 px-4"></td>
                    </template>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </main>

    <ProfileModal :isOpen="isProfileModalOpen" :initialData="authStore.user" @close="isProfileModalOpen = false" @save="saveProfile" />
  </div>
</template>
