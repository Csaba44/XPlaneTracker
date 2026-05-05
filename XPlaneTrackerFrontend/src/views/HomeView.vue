<template>
  <div class="min-h-screen bg-flight-bg flex flex-col items-center justify-center p-6 text-center font-sans">
    <div class="max-w-3xl w-full space-y-8 animate-in fade-in duration-700">
      <div class="flex flex-col items-center">
        <div class="flex items-stretch gap-4">
          <h1 class="text-6xl md:text-8xl font-black text-white tracking-tighter italic leading-none m-0 p-0">CSABOLANTA</h1>
        </div>
        <p class="text-flight-accent font-bold tracking-[0.3em] uppercase mt-4 text-sm md:text-base">CSABOLANTA - Flight Tracking Reimagined</p>
      </div>

      <p class="text-slate-400 text-xl md:text-2xl font-medium italic">"Fast, lightweight, and reliable flight tracking."</p>

      <div class="flex justify-center pt-4">
        <router-link to="/login" class="bg-flight-accent hover:bg-sky-400 text-flight-bg font-black px-10 py-4 rounded-full transition-all transform hover:scale-105 shadow-[0_0_25px_rgba(56,189,248,0.3)] uppercase tracking-widest text-sm"> Enter the Cockpit </router-link>
      </div>

      <div class="mt-16 relative bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl max-w-xl mx-auto flex flex-col items-center overflow-hidden group">
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-[#FF5E5B] blur-[100px] opacity-10 group-hover:opacity-20 transition-opacity duration-700 pointer-events-none"></div>

        <div class="flex flex-col items-center mb-6 z-10 text-center">
          <div class="bg-[#FF5E5B]/10 p-4 rounded-full mb-4 border border-[#FF5E5B]/20 shadow-[0_0_15px_rgba(255,94,91,0.1)]">
            <i class="fa-solid fa-hand-holding-dollar text-[#FF5E5B] text-3xl"></i>
          </div>
          <h2 class="text-white font-black uppercase tracking-widest text-lg md:text-xl">Support the Project</h2>
          <p class="text-slate-400 font-medium text-sm mt-2 italic">(Help keep the servers running)</p>
        </div>

        <p class="text-slate-500 text-sm mb-8 z-10 max-w-sm">The server costs 8 euros monthly. Support the project to keep it running and help us grow!</p>

        <a href="https://ko-fi.com/csaba44" target="_blank" rel="noopener noreferrer" class="z-10 w-full sm:w-auto bg-[#FF5E5B] hover:bg-[#ff4744] border border-[#ff8381] text-white font-black px-10 py-4 rounded-xl transition-all transform hover:-translate-y-1 hover:shadow-[0_10px_25px_rgba(255,94,91,0.3)] flex items-center justify-center gap-3">
          <i class="fa-solid fa-mug-hot text-xl group-hover:animate-bounce"></i>
          <span class="uppercase tracking-widest text-sm">Support</span>
        </a>
      </div>
    </div>
  </div>
</template>
