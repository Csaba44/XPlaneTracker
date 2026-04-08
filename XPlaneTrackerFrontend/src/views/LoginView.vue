<template>
  <div class="min-h-screen bg-flight-bg flex items-center justify-center p-6 font-sans">
    <div class="w-full max-w-md bg-flight-sidebar border border-flight-border p-10 rounded-3xl shadow-2xl">
      <div class="text-center mb-10">
        <h2 class="text-3xl font-black text-white italic italic tracking-tighter">BELÉPÉS</h2>
        <p class="text-slate-500 text-xs uppercase tracking-widest mt-2">Csak széptestvéreknek ⛔</p>
      </div>

      <form @submit.prevent="$router.push('/api/flights')" class="space-y-6">
        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Felhasználónév</label>
          <input type="text" class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="Nyisztor Roland" />
        </div>

        <div class="space-y-2">
          <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Jelszó</label>
          <input type="password" class="w-full bg-flight-card border border-flight-border rounded-xl px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" placeholder="••••••••" />
        </div>

        <button type="submit" class="w-full bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-4 rounded-xl transition-all shadow-lg uppercase tracking-widest text-sm mt-4 cursor-pointer">Zha tar aba muro phral, megyunk repulozni</button>
      </form>

      <div class="mt-8 text-center">
        <router-link to="/" class="text-slate-500 hover:text-white text-xs transition-colors"> <i class="fa-solid fa-arrow-left mr-2"></i> Vissza a főoldalra </router-link>
      </div>
    </div>
  </div>
</template>
