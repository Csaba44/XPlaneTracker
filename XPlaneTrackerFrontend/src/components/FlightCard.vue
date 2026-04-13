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
  <div @click="$emit('click')" :class="['p-5 rounded-xl cursor-pointer transition-all duration-300 border group', isSelected ? 'bg-flight-card border-flight-accent shadow-[0_0_20px_rgba(56,189,248,0.1)]' : 'bg-transparent border-transparent hover:bg-flight-card-hover']">
    <div class="flex justify-between items-start mb-3">
      <div class="flex flex-col">
        <span :class="['text-xl font-bold transition-colors', isSelected ? 'text-flight-accent' : 'text-white group-hover:text-flight-accent']">
          {{ flight.callsign }}
        </span>
        <span v-if="flight.user" class="text-[10px] text-teal-400 font-bold uppercase tracking-widest mt-0.5"> <i class="fa-solid fa-user mr-1"></i> {{ flight.user.name }} </span>
        <div class="flex items-center space-x-2 mt-1 bg-black/30 w-fit px-2 py-0.5 rounded border border-white/5">
          <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.dep_icao || "----" }}</span>
          <i class="fa-solid fa-plane text-[9px] text-flight-accent"></i>
          <span class="text-[11px] font-black text-slate-300 tracking-widest">{{ flight.arr_icao || "----" }}</span>
        </div>
      </div>
      <div class="flex flex-col items-end space-y-1">
        <span class="text-[10px] bg-flight-bg text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono">
          {{ flight.flight_number }}
        </span>
        <span v-if="flight.aircraft_registration" class="text-[9px] text-slate-400 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded font-mono uppercase">
          {{ flight.aircraft_registration }}
        </span>
      </div>
    </div>
    <div class="flex justify-between items-end text-xs text-slate-500">
      <div class="flex flex-col">
        <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
        <span class="text-[10px]">{{ new Date(flight.start_time).toLocaleDateString() }}</span>
      </div>

      <div class="flex items-center space-x-2">
        <button v-if="isSelected && !isReadonly" @click.stop="$emit('delete')" class="text-red-500/60 hover:text-red-500 transition-colors bg-red-500/5 hover:bg-red-500/20 p-1.5 rounded-md cursor-pointer" title="Delete Flight">
          <i class="fa-solid fa-trash"></i>
        </button>
        <button v-if="isSelected && !isReadonly" @click.stop="$emit('edit')" class="text-slate-400 hover:text-flight-accent transition-colors bg-white/5 hover:bg-flight-accent/10 p-1.5 rounded-md cursor-pointer" title="Edit Flight">
          <i class="fa-solid fa-pen"></i>
        </button>
        <button v-if="isSelected" @click.stop="$emit('share')" class="text-flight-accent hover:text-white transition-colors bg-flight-accent/10 hover:bg-flight-accent p-1.5 rounded-md cursor-pointer" title="Share Flight">
          <i class="fa-solid fa-share-nodes"></i>
        </button>

        <i class="fa-solid fa-chevron-right text-slate-700 group-hover:text-flight-accent transition-colors ml-1"></i>
      </div>
    </div>
  </div>
</template>
