<template>
  <div class="min-h-screen bg-flight-bg flex flex-col items-center justify-center p-6 text-center font-sans">
    <div class="max-w-3xl w-full space-y-8 animate-in fade-in duration-700">
      <div class="flex flex-col items-center">
        <div class="flex items-stretch gap-4">
          <h1 class="text-6xl md:text-8xl font-black text-white tracking-tighter italic leading-none m-0 p-0">X-TRACKER</h1>
        </div>
        <p class="text-flight-accent font-bold tracking-[0.3em] uppercase mt-4 text-sm md:text-base">Volanta Dzsipszi verzió a széptestvéreknek</p>
      </div>

      <p class="text-slate-400 text-xl md:text-2xl font-medium italic">"Gyors, pacek, nem laggoltat, de zoral!"</p>

      <div class="flex justify-center pt-4">
        <router-link to="/login" class="bg-flight-accent hover:bg-sky-400 text-flight-bg font-black px-10 py-4 rounded-full transition-all transform hover:scale-105 shadow-[0_0_25px_rgba(56,189,248,0.3)] uppercase tracking-widest text-sm"> Zha tar aba ando Pilótafülke muro phral </router-link>
      </div>

      <div class="mt-16 bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl text-left max-w-xl mx-auto">
        <div class="flex items-center space-x-3 mb-6">
          <i class="fa-solid fa-hand-holding-heart text-flight-accent text-xl"></i>
          <h2 class="text-white font-bold uppercase tracking-wider">Ha tiszteled, itt tudsz pénzt küldeni (szeretem a pénzt)</h2>
        </div>

        <div class="space-y-4 font-mono text-xs md:text-sm">
          <div class="flex flex-col md:flex-row md:justify-between border-b border-flight-border/50 pb-2">
            <span class="text-slate-500 uppercase">Számlaszám:</span>
            <span class="text-white font-bold">10918001-00000134-79770006 (UniCredit)</span>
          </div>
          <div class="flex flex-col md:flex-row md:justify-between border-b border-flight-border/50 pb-2">
            <span class="text-slate-500 uppercase">IBAN:</span>
            <span class="text-white font-bold">HU21 10918001 00000134 79770006</span>
          </div>
          <div class="flex flex-col md:flex-row md:justify-between border-b border-flight-border/50 pb-2">
            <span class="text-slate-500 uppercase">BIC (SWIFT):</span>
            <span class="text-white font-bold">BACXHUHB</span>
          </div>
          <div class="pt-2">
            <p class="text-[10px] text-slate-500 uppercase mb-1">Számlatulajdonos</p>
            <p class="text-flight-accent font-black text-base uppercase">Tisztesség a bűn helyett alapítvány</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
