<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  isOpen: Boolean,
  initialData: Object,
});

const emit = defineEmits(["close", "save"]);

const form = ref({
  name: "",
  email: "",
  password: "",
});

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal) {
      form.value = {
        name: props.initialData?.name || "",
        email: props.initialData?.email || "",
        password: "",
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
      <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">Profile</h2>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Username</label>
          <input v-model="form.name" type="text" required class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
        </div>

        <div>
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Email</label>
          <input v-model="form.email" type="email" required class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
        </div>

        <div>
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1"> New Password <span class="text-slate-600 lowercase normal-case">(leave empty to keep current)</span> </label>
          <input v-model="form.password" type="password" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
        </div>

        <div class="flex space-x-3 pt-6">
          <button type="button" @click="$emit('close')" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border cursor-pointer">Cancel</button>
          <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs cursor-pointer">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>
