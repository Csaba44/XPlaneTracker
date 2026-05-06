<script setup>
import { ref, watch } from 'vue';
import api from '../config/api';
import { toast } from 'vue-sonner';

const props = defineProps({
  isOpen: Boolean,
  simulator: String,
  aircraft_icao: String,
  flap_index: [String, Number],
  initialLabel: String,
});

const emit = defineEmits(['close', 'submitted']);

const label = ref(props.initialLabel || '');
const isSubmitting = ref(false);

watch(() => props.isOpen, (val) => {
  if (val) label.value = props.initialLabel || '';
});

const submit = async () => {
  if (!label.value) return;
  if (!props.aircraft_icao || props.aircraft_icao === 'unknown' || props.aircraft_icao.length !== 4) {
    toast.error('Invalid aircraft type.');
    return;
  }
  isSubmitting.value = true;
  try {
    await api.post('/api/flap-mappings', {
      simulator: props.simulator,
      aircraft_icao: props.aircraft_icao,
      flap_index: String(props.flap_index),
      label: label.value,
    });
    toast.success('Flap mapping submitted for approval!');
    emit('submitted');
    emit('close');
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || 'Failed to submit mapping');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[6000] p-4 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
      <h2 class="text-2xl font-black text-white italic mb-2 uppercase tracking-tighter">Submit Flap Label</h2>
      <p class="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-6">
        {{ simulator }} · {{ aircraft_icao && aircraft_icao !== 'unknown' ? aircraft_icao : 'All Aircraft' }} · Index: {{ flap_index }}
      </p>

      <div class="space-y-4">
        <div>
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Label (e.g. 1+F, 10°, FULL)</label>
          <input v-model="label" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="Enter label..." autofocus @keyup.enter="submit" />
        </div>

        <div class="flex space-x-3 pt-4">
          <button @click="$emit('close')" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border">Cancel</button>
          <button @click="submit" :disabled="isSubmitting || !label" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs disabled:opacity-50">
            {{ isSubmitting ? 'Submitting...' : 'Submit' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
