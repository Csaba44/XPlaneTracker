<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  isOpen: Boolean,
  initialData: Object,
});

const emit = defineEmits(["close", "save"]);

const form = ref({
  id: null,
  callsign: "",
  flight_number: "",
  airline: "",
  dep_icao: "",
  arr_icao: "",
});

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal && props.initialData) {
      form.value = {
        id: props.initialData.id,
        callsign: props.initialData.callsign || "",
        flight_number: props.initialData.flight_number || "",
        airline: props.initialData.airline || "",
        dep_icao: props.initialData.dep_icao || "",
        arr_icao: props.initialData.arr_icao || "",
      };
    }
  },
);

const handleSubmit = () => {
  emit("save", form.value);
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm">
    <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
      <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">Járat Szerkesztése</h2>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Callsign</label>
            <input v-model="form.callsign" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Flight Number</label>
            <input v-model="form.flight_number" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>
        </div>

        <div>
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Airline</label>
          <input v-model="form.airline" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">DEP ICAO</label>
            <input v-model="form.dep_icao" type="text" pattern="[A-Za-z0-9]+" maxlength="4" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors uppercase" placeholder="E pl. LHBP" />
          </div>
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">ARR ICAO</label>
            <input v-model="form.arr_icao" type="text" pattern="[A-Za-z0-9]+" maxlength="4" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors uppercase" placeholder="E pl. EGLL" />
          </div>
        </div>

        <div class="flex space-x-3 pt-6">
          <button type="button" @click="$emit('close')" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border cursor-pointer">Mégse</button>
          <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs cursor-pointer">Mentés</button>
        </div>
      </form>
    </div>
  </div>
</template>
