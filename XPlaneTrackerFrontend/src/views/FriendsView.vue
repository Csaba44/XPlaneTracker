<script setup>
import { ref, watch, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";

const authStore = useAuthStore();

const friends = ref([]);
const searchQuery = ref("");
const searchResults = ref([]);
const isSearching = ref(false);

const fetchFriends = async () => {
  try {
    const response = await api.get("/api/friends");
    friends.value = response.data;
  } catch (error) {
    console.error(error);
    toast.error("Hiba a barátok betöltésekor.");
  }
};

let searchTimeout = null;

const searchUsers = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = [];
    return;
  }

  isSearching.value = true;
  try {
    const response = await api.get(`/api/friends/search?query=${searchQuery.value}`);
    searchResults.value = response.data;
  } catch (error) {
    console.error(error);
  } finally {
    isSearching.value = false;
  }
};

watch(searchQuery, () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    searchUsers();
  }, 500);
});

const isFriend = (id) => {
  return friends.value.some((friend) => friend.id === id);
};

const addFriend = async (friendId) => {
  try {
    await api.post("/api/friends", { friend_id: friendId });
    toast.success("Testvér sikeresen hozzáadva!");
    await fetchFriends();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Hiba a hozzáadáskor.");
  }
};

const removeFriend = async (friendId) => {
  if (!confirm("Biztosan törlöd ezt a testvért a listádról?")) return;

  try {
    await api.delete(`/api/friends/${friendId}`);
    friends.value = friends.value.filter((f) => f.id !== friendId);
    toast.success("Testvér törölve.");
  } catch (error) {
    console.error(error);
    toast.error("Hiba a törléskor.");
  }
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
  await fetchFriends();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8 pb-4">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">BARÁTOK</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <router-link to="/flights" class="w-full flex items-center justify-center space-x-2 bg-flight-card hover:bg-flight-card-hover border border-flight-border transition-colors p-3 rounded-xl text-xs font-bold uppercase tracking-wider text-white mb-4">
          <i class="fa-solid fa-plane"></i>
          <span>Vissza a járatokhoz</span>
        </router-link>

        <div class="flex justify-between items-center text-[9px] text-slate-500 font-bold uppercase tracking-widest pt-2 border-t border-flight-border/50">
          <span
            >Hozzáadva: <span class="text-flight-accent">{{ friends.length }}</span></span
          >
        </div>
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
        <div v-if="friends.length === 0" class="text-center py-10 text-slate-600 flex flex-col items-center bg-flight-card/50 rounded-xl border border-flight-border border-dashed">
          <i class="fa-solid fa-users-slash text-2xl mb-3 opacity-50 text-flight-accent"></i>
          <p class="text-sm font-bold text-slate-400">Nincsenek barátaid.</p>
          <p class="text-[10px] uppercase tracking-widest mt-1">Adj hozzá egy cigányt!</p>
        </div>

        <div v-for="friend in friends" :key="friend.id" class="p-4 rounded-xl bg-flight-card border border-flight-border flex justify-between items-center group transition-colors hover:border-flight-accent/50">
          <div class="flex flex-col overflow-hidden">
            <span class="text-white font-bold text-sm truncate">{{ friend.name }}</span>
            <span class="text-[10px] text-slate-500 truncate">{{ friend.email }}</span>
          </div>
          <button @click="removeFriend(friend.id)" class="text-red-500/60 hover:text-red-500 transition-colors bg-red-500/5 hover:bg-red-500/20 p-2 rounded-md cursor-pointer opacity-0 group-hover:opacity-100 ml-2 shrink-0" title="Törlés">
            <i class="fa-solid fa-user-xmark"></i>
          </button>
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col bg-flight-bg relative overflow-y-auto">
      <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-10 pointer-events-none"></div>

      <div class="max-w-3xl w-full mx-auto mt-20 px-8 relative z-10">
        <div class="text-center mb-10">
          <h2 class="text-4xl font-black text-white italic tracking-tighter mb-2">Új Testvérek Keresése</h2>
          <p class="text-slate-500">Írd be a nevet vagy email címet a kereséshez.</p>
        </div>

        <div class="relative mb-12">
          <i class="fa-solid fa-magnifying-glass absolute left-5 top-1/2 transform -translate-y-1/2 text-slate-500 text-lg"></i>
          <input v-model="searchQuery" type="text" placeholder="Keresés név vagy email alapján..." class="w-full bg-flight-card border-2 border-flight-border rounded-2xl pl-14 pr-6 py-5 text-white focus:outline-none focus:border-flight-accent transition-all shadow-[0_0_30px_rgba(0,0,0,0.5)] placeholder-slate-600 text-lg" />
          <i v-if="isSearching" class="fa-solid fa-circle-notch fa-spin absolute right-6 top-1/2 transform -translate-y-1/2 text-flight-accent"></i>
        </div>

        <div v-if="searchQuery && searchResults.length === 0 && !isSearching" class="text-center py-10">
          <i class="fa-solid fa-ghost text-4xl mb-4 text-slate-600"></i>
          <p class="text-slate-400 font-bold">Nem találtam testvért ezzel a névvel.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="user in searchResults" :key="user.id" class="p-5 rounded-2xl bg-flight-card border border-flight-border flex justify-between items-center transition-all hover:shadow-[0_0_15px_rgba(56,189,248,0.1)] hover:border-flight-accent/30">
            <div class="flex flex-col overflow-hidden pr-4">
              <span class="text-white font-bold text-lg truncate">{{ user.name }}</span>
              <span class="text-xs text-slate-500 truncate">{{ user.email }}</span>
            </div>

            <button v-if="!isFriend(user.id)" @click="addFriend(user.id)" class="bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer shrink-0">Hozzáadás</button>
            <span v-else class="text-[9px] text-green-500 uppercase font-black tracking-widest border border-green-500/20 bg-green-500/5 px-3 py-2 rounded-lg shrink-0"> <i class="fa-solid fa-check mr-1"></i> Barát </span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
