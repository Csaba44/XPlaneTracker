<script setup>
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import api from "../config/api";

const router = useRouter();
const route = useRoute();

const name = ref("");
const password = ref("");
const password_confirmation = ref("");
const errorMessage = ref("");
const isLoading = ref(false);
const isInitializing = ref(true);

const token = route.query.token;

onMounted(async () => {
  if (!token) {
    errorMessage.value = "Invalid registration link. Token is missing.";
    isInitializing.value = false;
    return;
  }

  try {
    const response = await api.get(`/api/invites/${token}`);
    if (response.data.name) {
      name.value = response.data.name;
    }
  } catch (error) {
    errorMessage.value = "Invalid or expired registration link.";
  } finally {
    isInitializing.value = false;
  }
});

const handleRegister = async () => {
  if (password.value !== password_confirmation.value) {
    errorMessage.value = "Passwords do not match.";
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    await api.post("/api/register", {
      token: token,
      name: name.value,
      password: password.value,
      password_confirmation: password_confirmation.value,
    });

    router.push("/login");
  } catch (error) {
    errorMessage.value = error.response?.data?.error || error.response?.data?.message || "Registration failed. Please try again.";
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen bg-flight-bg flex items-center justify-center p-6 font-sans">
    <div class="w-full max-w-md bg-flight-sidebar border border-flight-border p-10 rounded-3xl shadow-2xl relative">
      <div v-if="errorMessage" class="absolute -top-16 left-0 right-0 bg-red-500/10 border border-red-500 text-red-500 p-3 rounded-xl text-center text-xs font-bold uppercase tracking-wider">
        {{ errorMessage }}
      </div>

      <div class="text-center mb-10">
        <h2 class="text-3xl font-black text-white italic tracking-tighter">REGISTER</h2>
        <p class="text-slate-500 text-xs uppercase tracking-widest mt-2">Join Csabolanta</p>
      </div>

      <div v-if="isInitializing" class="text-center text-slate-500 py-10 text-sm font-bold uppercase tracking-widest">
        Loading...
      </div>

      <form v-else @submit.prevent="handleRegister" class="space-y-6">
        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Name</label>
          <input v-model="name" type="text" required class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="Your Name" :disabled="!token" />
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Password</label>
          <input v-model="password" type="password" required minlength="8" class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="••••••••" :disabled="!token" />
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Confirm Password</label>
          <input v-model="password_confirmation" type="password" required minlength="8" class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="••••••••" :disabled="!token" />
        </div>

        <button type="submit" :disabled="isLoading || !token" class="w-full bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-4 rounded-xl transition-all shadow-lg uppercase tracking-widest text-sm mt-4 cursor-pointer disabled:opacity-50">
          {{ isLoading ? "Registering..." : "Create Account" }}
        </button>
      </form>

      <div class="mt-8 text-center">
        <router-link to="/login" class="text-slate-500 hover:text-white text-xs transition-colors"> <i class="fa-solid fa-arrow-left mr-2"></i> Back to Login </router-link>
      </div>
    </div>
  </div>
</template>
