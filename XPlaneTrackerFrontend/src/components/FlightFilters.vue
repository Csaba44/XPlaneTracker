<script setup>
import { computed, ref, onMounted, onUnmounted } from "vue";

const props = defineProps({
  searchQuery: String,
  filteredCount: Number,
  totalCount: Number,
});

const emit = defineEmits(["update:searchQuery", "clear"]);

const localSearch = computed({
  get: () => props.searchQuery,
  set: (val) => emit("update:searchQuery", val),
});

const isDropdownOpen = ref(false);
const inputRef = ref(null);
const dropdownRef = ref(null);

// Available tags based on your requirements
const availableTags = [
  { label: "Departure", value: "dep:", icon: "fa-plane-departure" },
  { label: "Arrival", value: "arr:", icon: "fa-plane-arrival" },
  { label: "Callsign", value: "callsign:", icon: "fa-tower-observation" },
  { label: "A/C Type", value: "type:", icon: "fa-plane" },
  { label: "Registration", value: "reg:", icon: "fa-id-card" },
];

const insertTag = (tagValue) => {
  const currentVal = localSearch.value || "";
  const space = currentVal.length > 0 && !currentVal.endsWith(" ") ? " " : "";

  localSearch.value = `${currentVal}${space}${tagValue}`;
  isDropdownOpen.value = false;

  if (inputRef.value) {
    inputRef.value.focus();
  }
};

const clearAll = () => {
  localSearch.value = "";
  emit("clear");
};

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
  <div class="bg-flight-card border border-flight-border rounded-xl p-3 space-y-3 shadow-lg">
    <div class="flex items-center space-x-2">
      <div ref="dropdownRef" class="relative flex-grow flex items-center bg-flight-bg border border-flight-border rounded-lg transition-colors focus-within:border-flight-accent">
        <div class="pl-3 pr-2 text-slate-500">
          <i class="fa-solid fa-magnifying-glass text-xs"></i>
        </div>

        <input ref="inputRef" v-model="localSearch" type="text" placeholder="Search globally or with tags (e.g. dep:LHBP callsign:RYR)..." class="w-full bg-transparent py-2.5 text-xs text-white focus:outline-none placeholder-slate-600" @keydown.esc="isDropdownOpen = false" />

        <button @click.prevent="isDropdownOpen = !isDropdownOpen" class="px-3 text-slate-400 hover:text-flight-accent transition-colors border-l border-flight-border/50 text-xs flex items-center space-x-1 h-full" title="Add filter tag">
          <i class="fa-solid fa-tags"></i>
          <i class="fa-solid fa-chevron-down text-[10px] ml-1"></i>
        </button>

        <div v-if="isDropdownOpen" class="absolute right-0 top-full mt-2 w-56 bg-flight-card border border-flight-border rounded-lg shadow-xl z-50 overflow-hidden">
          <div class="px-3 py-2 border-b border-flight-border/50 bg-black/20">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Available Tags</span>
          </div>
          <div class="flex flex-col py-1">
            <button v-for="tag in availableTags" :key="tag.value" @click.prevent="insertTag(tag.value)" class="flex items-center px-3 py-2 text-xs text-left text-slate-300 hover:bg-flight-accent/10 hover:text-flight-accent transition-colors">
              <i :class="['fa-solid', tag.icon, 'w-5 text-center mr-2 opacity-70']"></i>
              <span class="flex-grow">{{ tag.label }}</span>
              <span class="text-[10px] font-mono bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-slate-400">
                {{ tag.value }}
              </span>
            </button>
          </div>
        </div>
      </div>

      <button v-if="localSearch" @click="clearAll" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/20 px-3 py-2.5 rounded-lg text-xs transition-colors flex items-center justify-center cursor-pointer min-w-[40px]" title="Clear search">
        <i class="fa-solid fa-filter-circle-xmark"></i>
      </button>
    </div>

    <div class="flex justify-between items-center text-[9px] text-slate-500 font-bold uppercase tracking-widest pt-1 border-t border-flight-border/50">
      <span
        >Results: <span class="text-flight-accent">{{ filteredCount }}</span></span
      >
      <span v-if="totalCount > 0">Total: {{ totalCount }}</span>
    </div>
  </div>
</template>
