<template>
  <v-card variant="outlined">
    <div class="pa-4 d-flex align-center justify-space-between ga-3">
      <div>
        <h3 class="text-subtitle-1">Roles & Permissions</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Create roles, manage inheritance, and edit the role-to-tool permission matrix.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreate">Add Role</v-btn>
        <v-btn size="small" variant="text" icon="mdi-refresh" :loading="isLoading" @click="refreshAll" />
      </div>
    </div>
    <v-divider />

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="ma-4" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <v-row class="pa-4">
      <v-col cols="12" lg="4">
        <v-list v-if="roles.length" lines="two" border rounded>
          <v-list-item
            v-for="role in roles"
            :key="role.id"
            :title="role.name"
            :subtitle="role.description || 'No description'"
            :active="selectedRole?.id === role.id"
            @click="selectedRoleId = role.id"
          >
            <template #prepend>
              <v-icon icon="mdi-shield-account" />
            </template>
            <template #append>
              <div class="d-flex align-center ga-1">
                <v-chip size="x-small" variant="tonal">{{ effectivePermCount(role) }}</v-chip>
                <v-btn size="small" variant="text" icon="mdi-pencil" @click.stop="openEdit(role)" />
                <v-btn size="small" variant="text" icon="mdi-delete" color="error" :loading="isDeleting" @click.stop="removeRole(role.id)" />
              </div>
            </template>
          </v-list-item>
        </v-list>
        <div v-else class="text-center py-8 text-medium-emphasis">
          <v-icon icon="mdi-shield-account-outline" size="40" class="mb-2" />
          <div class="text-subtitle-2">No roles defined</div>
          <v-btn size="small" color="primary" class="mt-3" prepend-icon="mdi-plus" @click="openCreate">Add Role</v-btn>
        </div>
      </v-col>

      <v-col cols="12" lg="8">
        <div class="d-flex align-center justify-space-between mb-3">
          <div>
            <div class="text-subtitle-2">Editable Permission Matrix</div>
            <div class="text-caption text-medium-emphasis">
              {{ selectedRole ? `Editing ${selectedRole.name}` : 'Select a role to edit direct permissions' }}
            </div>
          </div>
          <v-btn
            size="small"
            color="primary"
            prepend-icon="mdi-content-save"
            :disabled="!selectedRole"
            :loading="isSavingPermissions"
            @click="savePermissions"
          >
            Save Matrix
          </v-btn>
        </div>

        <v-table v-if="tools.length && selectedRole" density="compact" class="permission-table">
          <thead>
            <tr>
              <th>Tool</th>
              <th class="text-center">Read</th>
              <th class="text-center">Write</th>
              <th class="text-center">Confirm</th>
              <th class="text-center">Inherited</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tool in tools" :key="tool.id">
              <td>
                <div class="font-weight-medium">{{ tool.name }}</div>
                <div class="text-caption text-medium-emphasis">{{ tool.sensitivity }} · {{ tool.access_type }}</div>
              </td>
              <td class="text-center">
                <v-checkbox-btn v-model="permissionDraft[tool.id].read" />
              </td>
              <td class="text-center">
                <v-checkbox-btn v-model="permissionDraft[tool.id].write" />
              </td>
              <td class="text-center">
                <v-checkbox-btn v-model="permissionDraft[tool.id].confirm" />
              </td>
              <td class="text-center">
                <v-icon v-if="isInherited(tool.id)" icon="mdi-check-circle" color="info" size="18" />
                <span v-else class="text-medium-emphasis">—</span>
              </td>
            </tr>
          </tbody>
        </v-table>

        <v-alert v-else-if="selectedRole" type="info" variant="tonal">
          Add tools before assigning permissions.
        </v-alert>
        <v-alert v-else type="info" variant="tonal">
          Select or create a role to edit its permissions.
        </v-alert>
      </v-col>
    </v-row>

    <v-dialog v-model="roleDialog" max-width="560">
      <v-card>
        <v-card-title>{{ editing ? 'Edit Role' : 'Add Role' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="roleForm.name" label="Name" variant="outlined" />
          <v-textarea v-model="roleForm.description" label="Description" variant="outlined" rows="2" />
          <v-select
            v-model="roleForm.inherits_from"
            :items="parentRoleItems"
            label="Inherits From"
            item-title="title"
            item-value="value"
            clearable
            variant="outlined"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="roleDialog = false">Cancel</v-btn>
          <v-btn color="primary" :disabled="!roleForm.name.trim()" :loading="isCreating || isUpdating" @click="saveRole">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useAgentRoles } from '~/composables/useAgentRoles'
import { useAgentTools } from '~/composables/useAgentTools'
import type { RoleRead } from '~/types/agentControl'

const props = defineProps<{ agentId: string }>()

const {
  roles,
  isLoading,
  refetch,
  refetchMatrix,
  createRole,
  updateRole,
  deleteRole,
  setPermissions,
  isCreating,
  isUpdating,
  isDeleting,
} = useAgentRoles(() => props.agentId)
const { tools } = useAgentTools(() => props.agentId)

const selectedRoleId = ref('')
const roleDialog = ref(false)
const editing = ref<RoleRead | null>(null)
const errorText = ref('')
const isSavingPermissions = ref(false)

const roleForm = reactive({
  name: '',
  description: '',
  inherits_from: null as string | null,
})

const permissionDraft = reactive<Record<string, { read: boolean; write: boolean; confirm: boolean }>>({})

const selectedRole = computed(() => roles.value.find(role => role.id === selectedRoleId.value) ?? roles.value[0] ?? null)

const parentRoleItems = computed(() => roles.value
  .filter(role => role.id !== editing.value?.id)
  .map(role => ({ title: role.name, value: role.id })))

watch(roles, (items) => {
  if (!selectedRoleId.value || !items.some(role => role.id === selectedRoleId.value)) {
    selectedRoleId.value = items[0]?.id ?? ''
  }
}, { immediate: true })

watch([selectedRole, tools], () => {
  rebuildPermissionDraft()
}, { immediate: true })

function rebuildPermissionDraft() {
  for (const key of Object.keys(permissionDraft)) delete permissionDraft[key]
  const role = selectedRole.value
  for (const tool of tools.value) {
    const direct = role?.permissions.find(p => p.tool_id === tool.id)
    permissionDraft[tool.id] = {
      read: direct?.scopes.includes('read') ?? false,
      write: direct?.scopes.includes('write') ?? false,
      confirm: direct?.requires_confirmation_override ?? false,
    }
  }
}

function effectivePermCount(role: RoleRead) {
  const ids = new Set(role.permissions.map(p => p.tool_id))
  for (const p of role.inherited_permissions ?? []) ids.add(p.tool_id)
  return ids.size
}

function isInherited(toolId: string) {
  return !!selectedRole.value?.inherited_permissions?.some(p => p.tool_id === toolId)
}

function openCreate() {
  editing.value = null
  roleForm.name = ''
  roleForm.description = ''
  roleForm.inherits_from = null
  roleDialog.value = true
}

function openEdit(role: RoleRead) {
  editing.value = role
  roleForm.name = role.name
  roleForm.description = role.description
  roleForm.inherits_from = role.inherits_from
  roleDialog.value = true
}

async function saveRole() {
  errorText.value = ''
  try {
    const body = {
      name: roleForm.name.trim(),
      description: roleForm.description,
      inherits_from: roleForm.inherits_from,
    }
    if (editing.value) {
      await updateRole({ roleId: editing.value.id, body })
    } else {
      const created = await createRole(body)
      selectedRoleId.value = created.id
    }
    roleDialog.value = false
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to save role'
  }
}

async function removeRole(roleId: string) {
  errorText.value = ''
  try {
    await deleteRole(roleId)
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to delete role'
  }
}

async function savePermissions() {
  if (!selectedRole.value) return
  errorText.value = ''
  isSavingPermissions.value = true
  try {
    const permissions = Object.entries(permissionDraft)
      .map(([toolId, draft]) => ({
        tool_id: toolId,
        scopes: [
          ...(draft.read ? ['read'] : []),
          ...(draft.write ? ['write'] : []),
        ],
        requires_confirmation_override: draft.confirm ? true : null,
      }))
      .filter(entry => entry.scopes.length > 0)
    await setPermissions({ roleId: selectedRole.value.id, body: { permissions } })
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to save permissions'
  } finally {
    isSavingPermissions.value = false
  }
}

function refreshAll() {
  refetch()
  refetchMatrix()
}
</script>

<style scoped>
.permission-table {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 8px;
  overflow: hidden;
}
</style>

