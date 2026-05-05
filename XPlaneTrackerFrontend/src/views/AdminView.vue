<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import { toast } from "vue-sonner";

const router = useRouter();
const authStore = useAuthStore();

const users = ref([]);
const invites = ref([]);
const isModalOpen = ref(false);
const isEditing = ref(false);
const isInviteModalOpen = ref(false);

const formData = ref({
  id: null,
  name: "",
  email: "",
  password: "",
  is_admin: 0,
});

const inviteFormData = ref({
  id: null,
  name: "",
});

const fetchUsers = async () => {
  try {
    const response = await api.get("/api/admin/users");
    users.value = response.data;
  } catch (error) {
    console.error(error);
    toast.error("Failed to load users");
  }
};

const fetchInvites = async () => {
  try {
    const response = await api.get("/api/admin/invites");
    invites.value = response.data;
  } catch (error) {
    console.error(error);
    toast.error("Failed to load invites");
  }
};

const openAddModal = () => {
  isEditing.value = false;
  formData.value = { id: null, name: "", email: "", password: "", is_admin: 0 };
  isModalOpen.value = true;
};

const openEditModal = (user) => {
  isEditing.value = true;
  formData.value = {
    id: user.id,
    name: user.name,
    email: user.email,
    password: "",
    is_admin: user.is_admin,
  };
  isModalOpen.value = true;
};

const openEditInviteModal = (invite) => {
  inviteFormData.value = {
    id: invite.id,
    name: invite.name || "",
  };
  isInviteModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
};

const closeInviteModal = () => {
  isInviteModalOpen.value = false;
};

const saveUser = async () => {
  try {
    if (isEditing.value) {
      await api.put(`/api/admin/users/${formData.value.id}`, formData.value);
      toast.success("User updated successfully");
    } else {
      await api.post("/api/admin/users", formData.value);
      toast.success("User invited successfully");
      fetchInvites(); // Also fetch invites because a new invite is created
    }
    closeModal();
    fetchUsers();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Operation failed");
  }
};

const saveInvite = async () => {
  try {
    await api.put(`/api/admin/invites/${inviteFormData.value.id}`, inviteFormData.value);
    toast.success("Invite updated successfully");
    closeInviteModal();
    fetchInvites();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.message || "Operation failed");
  }
};

const deleteUser = async (id) => {
  if (!confirm("Are you sure you want to delete this user?")) return;

  try {
    await api.delete(`/api/admin/users/${id}`);
    toast.success("User deleted successfully");
    fetchUsers();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.error || "Failed to delete user");
  }
};

const revokeInvite = async (id) => {
  if (!confirm("Are you sure you want to revoke this invite?")) return;

  try {
    await api.delete(`/api/admin/invites/${id}`);
    toast.success("Invite revoked successfully");
    fetchInvites();
  } catch (error) {
    console.error(error);
    toast.error(error.response?.data?.error || "Failed to revoke invite");
  }
};

onMounted(() => {
  if (authStore.user?.is_admin !== 1) {
    router.push("/flights");
    return;
  }
  fetchUsers();
  fetchInvites();
});
</script>

<template>
  <div class="min-h-screen bg-flight-bg text-slate-300 p-8 font-sans">
    <div class="max-w-6xl mx-auto">
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-3xl font-black text-white tracking-tighter italic">ADMINISTRATION</h1>
          <p class="text-xs text-flight-accent uppercase font-bold tracking-widest mt-1">User Management</p>
        </div>

        <div class="flex space-x-4">
          <router-link to="/flights" class="bg-flight-card border border-flight-border hover:border-flight-accent text-white px-4 py-2 rounded-lg transition-colors text-sm font-bold uppercase tracking-wider flex items-center"> <i class="fa-solid fa-arrow-left mr-2"></i> Back to Flights </router-link>
          <button @click="openAddModal" class="bg-flight-accent hover:bg-sky-400 text-flight-bg px-4 py-2 rounded-lg transition-colors text-sm font-black uppercase tracking-wider flex items-center"><i class="fa-solid fa-plus mr-2"></i> Invite User</button>
        </div>
      </div>

      <div class="mb-8">
        <h2 class="text-lg font-bold text-white mb-4 uppercase tracking-wider">Registered Users</h2>
        <div class="bg-flight-sidebar border border-flight-border rounded-xl shadow-2xl overflow-hidden">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-flight-card border-b border-flight-border">
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">ID</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Name</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Email</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Role</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id" class="border-b border-flight-border/50 hover:bg-flight-card-hover transition-colors">
                <td class="p-4 text-sm font-mono text-slate-500">{{ user.id }}</td>
                <td class="p-4 text-sm font-bold text-white">{{ user.name }}</td>
                <td class="p-4 text-sm text-slate-400">{{ user.email }}</td>
                <td class="p-4">
                  <span v-if="user.is_admin" class="bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-widest">Admin</span>
                  <span v-else class="bg-slate-800 text-slate-400 border border-slate-700 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-widest">User</span>
                </td>
                <td class="p-4 flex justify-end space-x-2">
                  <button @click="openEditModal(user)" class="bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white p-2 rounded transition-colors">
                    <i class="fa-solid fa-pen text-xs"></i>
                  </button>
                  <button v-if="user.id !== authStore.user.id" @click="deleteUser(user.id)" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white p-2 rounded transition-colors">
                    <i class="fa-solid fa-trash text-xs"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h2 class="text-lg font-bold text-white mb-4 uppercase tracking-wider">Pending Invites</h2>
        <div class="bg-flight-sidebar border border-flight-border rounded-xl shadow-2xl overflow-hidden">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-flight-card border-b border-flight-border">
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Email</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Name</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Invited By</th>
                <th class="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="invites.length === 0">
                <td colspan="4" class="p-8 text-center text-sm text-slate-500 italic">No pending invites.</td>
              </tr>
              <tr v-for="invite in invites" :key="invite.id" class="border-b border-flight-border/50 hover:bg-flight-card-hover transition-colors">
                <td class="p-4 text-sm text-slate-400">{{ invite.email }}</td>
                <td class="p-4 text-sm font-bold text-white">{{ invite.name || '-' }}</td>
                <td class="p-4 text-sm text-slate-400">{{ invite.inviter ? invite.inviter.name : 'Unknown' }}</td>
                <td class="p-4 flex justify-end space-x-2">
                  <button @click="openEditInviteModal(invite)" class="bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white p-2 rounded transition-colors" title="Edit Invite Name">
                    <i class="fa-solid fa-pen text-xs"></i>
                  </button>
                  <button @click="revokeInvite(invite.id)" class="bg-amber-500/10 hover:bg-amber-500 text-amber-500 hover:text-white p-2 rounded transition-colors" title="Revoke Invite">
                    <i class="fa-solid fa-ban text-xs"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- User Modal -->
    <div v-if="isModalOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm">
      <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">
          {{ isEditing ? "Edit User" : "New User" }}
        </h2>

        <form @submit.prevent="saveUser" class="space-y-4">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Name <span v-if="!isEditing" class="text-slate-600 lowercase normal-case">(optional)</span></label>
            <input v-model="formData.name" type="text" :required="isEditing" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Email</label>
            <input v-model="formData.email" type="email" required class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div v-if="isEditing">
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1"> Password <span class="text-slate-600 lowercase normal-case">(leave blank to keep current)</span> </label>
            <input v-model="formData.password" type="password" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div class="flex space-x-3 pt-6">
            <button type="button" @click="closeModal" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border">Cancel</button>
            <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs">{{ isEditing ? "Save User" : "Send Invite" }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Invite Modal -->
    <div v-if="isInviteModalOpen" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[5000] p-4 backdrop-blur-sm">
      <div class="bg-flight-sidebar border border-flight-border p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <h2 class="text-2xl font-black text-white italic mb-6 uppercase tracking-tighter">
          Edit Invite Name
        </h2>

        <form @submit.prevent="saveInvite" class="space-y-4">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Name <span class="text-slate-600 lowercase normal-case">(optional)</span></label>
            <input v-model="inviteFormData.name" type="text" class="w-full bg-flight-card border border-flight-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-flight-accent transition-colors" />
          </div>

          <div class="flex space-x-3 pt-6">
            <button type="button" @click="closeInviteModal" class="flex-1 bg-flight-card hover:bg-slate-800 text-white font-bold py-3 rounded-lg transition-colors uppercase tracking-widest text-xs border border-flight-border">Cancel</button>
            <button type="submit" class="flex-1 bg-flight-accent hover:bg-sky-400 text-flight-bg font-black py-3 rounded-lg transition-colors shadow-lg uppercase tracking-widest text-xs">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>