<script setup>
import { computed } from "vue";

const props = defineProps({
  searchQuery: String,
  selectedAirline: String,
  availableAirlines: Array,
  filteredCount: Number,
  totalCount: Number,
});

const emit = defineEmits(["update:searchQuery", "update:selectedAirline", "clear"]);

const localSearch = computed({
  get: () => props.searchQuery,
  set: (val) => emit("update:searchQuery", val),
});

const localAirline = computed({
  get: () => props.selectedAirline,
  set: (val) => emit("update:selectedAirline", val),
});
</script>

<template>
  <div class="bg-flight-card border border-flight-border rounded-xl p-3 space-y-3 shadow-lg">
    <div class="relative">
      <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500 text-xs"></i>
      <input v-model="localSearch" type="text" placeholder="Keresés..." class="w-full bg-flight-bg border border-flight-border rounded-lg pl-8 pr-3 py-2 text-xs text-white focus:outline-none focus:border-flight-accent transition-colors placeholder-slate-600" />
    </div>

    <div class="flex space-x-2">
      <select v-model="localAirline" class="flex-grow bg-flight-bg border border-flight-border rounded-lg px-2 py-2 text-xs text-slate-300 focus:outline-none focus:border-flight-accent transition-colors cursor-pointer">
        <option value="">Összes</option>
        <option v-for="airline in availableAirlines" :key="airline" :value="airline">{{ airline }}</option>
      </select>

      <button v-if="searchQuery || selectedAirline" @click="$emit('clear')" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/20 px-3 rounded-lg text-xs transition-colors flex items-center justify-center cursor-pointer" title="Clear Filters">
        <i class="fa-solid fa-filter-circle-xmark"></i>
      </button>
    </div>

    <div class="flex justify-between items-center text-[9px] text-slate-500 font-bold uppercase tracking-widest pt-1 border-t border-flight-border/50">
      <span
        >Találat: <span class="text-flight-accent">{{ filteredCount }}</span></span
      >
      <span v-if="totalCount > 0">Összesen: {{ totalCount }}</span>
    </div>
  </div>
</template>
