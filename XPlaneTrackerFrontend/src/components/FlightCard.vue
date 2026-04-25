<script setup>
const props = defineProps({
  flight: Object,
  isSelected: Boolean,
  isReadonly: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["click", "delete", "edit", "share"]);
</script>
<template>
  <div @click="$emit('click')" :class="['relative rounded-xl cursor-pointer transition-all duration-300 border group overflow-hidden', isSelected ? 'border-flight-accent shadow-[0_0_20px_rgba(56,189,248,0.1)]' : 'border-transparent hover:border-flight-accent/20']">
    <div v-if="flight.photo?.imageUrl" class="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-105" :style="{ backgroundImage: `url(${flight.photo.imageUrl})` }" />

    <div :class="['absolute inset-0 transition-all duration-500', flight.photo?.imageUrl ? 'bg-gradient-to-b from-black/60 via-black/70 to-black/95 group-hover:from-black/35 group-hover:via-black/55 group-hover:to-black/92' : 'bg-slate-900 bg-gradient-to-br from-slate-800/50 to-black group-hover:from-slate-700/50']" />

    <i v-if="!flight.photo?.imageUrl" class="fa-solid fa-plane absolute -bottom-8 -right-8 text-[140px] text-white/[0.03] -rotate-12 transition-transform duration-700 group-hover:scale-110 group-hover:-translate-y-2 group-hover:translate-x-2 pointer-events-none"></i>

    <div class="relative p-5">
      <div class="flex justify-between items-start mb-3">
        <div class="flex flex-col">
          <span :class="['text-xl font-bold transition-colors', isSelected ? 'text-flight-accent' : 'text-white group-hover:text-flight-accent']">
            {{ flight.callsign }}
          </span>
          <span v-if="flight.user" class="text-[10px] text-teal-400 font-bold uppercase tracking-widest mt-0.5"> <i class="fa-solid fa-user mr-1"></i>{{ flight.user.name }} </span>
          <div class="flex items-center space-x-2 mt-1 bg-black/30 w-fit px-2 py-0.5 rounded border border-white/5 shadow-sm">
            <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.dep_icao || "----" }}</span>
            <i class="fa-solid fa-plane text-[9px] text-flight-accent"></i>
            <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.arr_icao || "----" }}</span>
          </div>
          <span v-if="flight.aircraft_type" class="text-[9px] text-slate-400 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded font-mono uppercase w-fit mt-1.5 shadow-sm">
            {{ flight.aircraft_type }}
          </span>
        </div>
        <div class="flex flex-col items-end space-y-1">
          <span class="text-[10px] bg-black/50 text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono shadow-sm">
            {{ flight.flight_number }}
          </span>
          <span v-if="flight.aircraft_registration" class="text-[9px] text-slate-400 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded font-mono uppercase shadow-sm">
            {{ flight.aircraft_registration }}
          </span>
        </div>
      </div>

      <div class="flex justify-between items-end text-xs text-slate-500 mt-2">
        <div class="flex flex-col">
          <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
          <span class="text-[10px]">{{ new Date(flight.start_time).toLocaleDateString() }}</span>
        </div>
        <div class="flex items-center space-x-2">
          <button v-if="isSelected && !isReadonly" @click.stop="$emit('delete')" class="text-red-500/60 hover:text-red-500 transition-colors bg-red-500/5 hover:bg-red-500/20 p-1.5 rounded-md cursor-pointer">
            <i class="fa-solid fa-trash"></i>
          </button>
          <button v-if="isSelected && !isReadonly" @click.stop="$emit('edit')" class="text-slate-400 hover:text-flight-accent transition-colors bg-white/5 hover:bg-flight-accent/10 p-1.5 rounded-md cursor-pointer">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button v-if="isSelected" @click.stop="$emit('share')" class="text-flight-accent hover:text-white transition-colors bg-flight-accent/10 hover:bg-flight-accent p-1.5 rounded-md cursor-pointer">
            <i class="fa-solid fa-share-nodes"></i>
          </button>
          <i class="fa-solid fa-chevron-right text-slate-700 group-hover:text-flight-accent transition-colors ml-1"></i>
        </div>
      </div>
      <div v-if="!flight.photo.error" class="flex items-center justify-between mt-3 pt-3 border-t border-white/7">
        <div class="flex items-center gap-2">
          <img :src="flight.photo.thumbnailUrl" class="w-7 h-7 rounded object-cover border border-white/10" />
          <div>
            <div class="text-[10px] text-flight-accent font-semibold">{{ flight.photo.aircraftType }}</div>
            <div class="text-[9px] text-slate-500">by {{ flight.photo.photographer }}</div>
          </div>
        </div>
        <a :href="flight.photo.photoPageUrl" target="_blank" @click.stop class="text-[9px] text-slate-500 hover:text-slate-300 border border-white/8 px-1.5 py-0.5 rounded bg-black/30 transition-colors"> jetphotos ↗ </a>
      </div>
    </div>
  </div>
</template>
