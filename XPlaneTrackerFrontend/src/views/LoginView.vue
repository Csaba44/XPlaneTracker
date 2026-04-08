<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const errorMessage = ref("");
const isLoading = ref(false);

const handleLogin = async () => {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    await authStore.login({
      email: email.value,
      password: password.value,
    });

    router.push("/flights");
  } catch (error) {
    if (error.response?.status === 422 || error.response?.status === 401) {
      errorMessage.value = "Hibás felhasználónév vagy jelszó! Tesó, ne próbálkozz...";
    } else {
      errorMessage.value = "Valami megzuhant a szerveren. Próbáld újra!";
    }
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
        <h2 class="text-3xl font-black text-white italic tracking-tighter">BELÉPÉS</h2>
        <p class="text-slate-500 text-xs uppercase tracking-widest mt-2">Csak széptestvéreknek ⛔</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Felhasználónév (Email)</label>
          <input v-model="email" type="email" required class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="dzsipszi@pilota.hu" />
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Jelszó</label>
          <input v-model="password" type="password" required class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="••••••••" />
        </div>

        <button type="submit" :disabled="isLoading" class="w-full bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-4 rounded-xl transition-all shadow-lg uppercase tracking-widest text-sm mt-4 cursor-pointer disabled:opacity-50">
          {{ isLoading ? "Csatlakozás a toronyhoz..." : "Zha tar aba muro phral, megyunk repulozni" }}
        </button>
      </form>

      <div class="mt-8 text-center">
        <router-link to="/" class="text-slate-500 hover:text-white text-xs transition-colors"> <i class="fa-solid fa-arrow-left mr-2"></i> Vissza a főoldalra </router-link>
      </div>
    </div>
  </div>
</template>
