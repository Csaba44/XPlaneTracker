<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
  user: Object,
  generatedApiKey: String,
  isUploading: Boolean,
});

const emit = defineEmits(["openProfile", "logout", "generateApiKey", "uploadFile"]);
const route = useRoute();
const fileInput = ref(null);

// Dropdown state
const isDropdownOpen = ref(false);
const dropdownRef = ref(null);

const triggerFileInput = () => {
  fileInput.value.click();
};

const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    emit("uploadFile", file);
  }
  event.target.value = null;
};

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    isDropdownOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener("mousedown", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("mousedown", handleClickOutside);
});
</script>

<template>
  <div class="flex flex-col space-y-3 mb-4">
    <div class="flex items-center justify-between bg-flight-card border border-flight-border p-3 rounded-lg shadow-md">
      <div class="flex flex-col">
        <span class="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Szia testvér!</span>
        <span class="text-xs text-white font-bold truncate max-w-[120px]">
          {{ user?.name || user?.email || "Pilot" }}
        </span>
      </div>
      <div class="flex space-x-1">
        <a target="_blank" href="https://github.com/Csaba44/XPlaneTracker/releases" class="bg-flight-bg hover:bg-flight-accent/20 text-slate-400 hover:text-flight-accent transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Download Csabolanta">
          <i class="fa-solid fa-download text-xs"></i>
        </a>
        <button @click="$emit('openProfile')" class="bg-flight-bg hover:bg-flight-accent/20 text-slate-400 hover:text-flight-accent transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Edit Profile">
          <i class="fa-solid fa-gear text-xs"></i>
        </button>
        <button @click="$emit('logout')" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Logout">
          <i class="fa-solid fa-right-from-bracket text-xs"></i>
        </button>
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <router-link v-if="route.name !== 'flights'" to="/flights" class="flex-1 basis-[45%] flex justify-center items-center space-x-2 bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">
        <i class="fa-solid fa-plane"></i>
        <span>Járatok</span>
      </router-link>

      <router-link v-if="route.name !== 'community'" to="/community" class="flex-1 basis-[45%] flex justify-center items-center space-x-2 bg-teal-500/10 hover:bg-teal-500 text-teal-500 hover:text-white border border-teal-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">
        <i class="fa-solid fa-earth-europe"></i>
        <span>Közösség</span>
      </router-link>

      <router-link v-if="route.name !== 'friends'" to="/friends" class="flex-1 basis-[45%] flex justify-center items-center space-x-2 bg-amber-500/10 hover:bg-amber-500 text-amber-500 hover:text-white border border-amber-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">
        <i class="fa-solid fa-users"></i>
        <span>Barátok</span>
      </router-link>

      <router-link v-if="route.name !== 'leaderboard'" to="/leaderboard" class="flex-1 basis-[45%] flex justify-center items-center space-x-2 bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white border border-rose-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">
        <i class="fa-solid fa-trophy"></i>
        <span>Ranglista</span>
      </router-link>
    </div>

    <router-link v-if="user?.is_admin === 1" to="/admin" class="w-full text-center bg-purple-500/10 hover:bg-purple-500 text-purple-500 hover:text-white border border-purple-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider block"> Admin Panel </router-link>

    <div class="relative" ref="dropdownRef">
      <button @click="isDropdownOpen = !isDropdownOpen" class="w-full bg-flight-card hover:bg-slate-800 text-slate-300 hover:text-white border border-flight-border transition-colors p-2.5 rounded-lg text-xs font-bold uppercase tracking-wider flex justify-center items-center gap-2 shadow-sm cursor-pointer">
        <i class="fa-solid fa-toolbox text-slate-400"></i>
        <span>Eszközök</span>
        <i class="fa-solid fa-chevron-down text-[10px] ml-auto transition-transform duration-200" :class="{ 'rotate-180': isDropdownOpen }"></i>
      </button>

      <div v-if="isDropdownOpen" class="absolute top-full left-0 right-0 mt-2 bg-flight-card border border-flight-border rounded-lg shadow-xl z-50 p-2 flex flex-col space-y-2">
        <button
          @click="
            () => {
              $emit('generateApiKey');
              isDropdownOpen = false;
            }
          "
          class="w-full bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer flex items-center justify-center gap-2"
        >
          <i class="fa-solid fa-key"></i> Generate API Key
        </button>

        <input type="file" accept=".gz" ref="fileInput" @change="handleFileChange" style="display: none" />
        <button
          @click="
            () => {
              triggerFileInput();
              isDropdownOpen = false;
            }
          "
          :disabled="isUploading"
          class="w-full bg-green-500/10 hover:bg-green-500 text-green-500 hover:text-white border border-green-500 transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <i class="fa-solid fa-file-arrow-up"></i> {{ isUploading ? "Töltöm teso..." : "Manual PIREP" }}
        </button>
      </div>
    </div>

    <div v-if="generatedApiKey" class="bg-black/50 p-3 rounded-lg border border-flight-border mt-1">
      <p class="text-[10px] text-red-400 font-bold uppercase mb-1">Vigyázz rá testvérem, el ne lopják!</p>
      <code class="text-[10px] text-flight-accent break-all select-all">{{ generatedApiKey }}</code>
    </div>
  </div>
</template>
