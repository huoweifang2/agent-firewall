<template>
  <v-container fluid class="approvals-page pa-4">
    <div class="approvals-page__header">
      <div>
        <h1 class="text-h5 font-weight-bold mb-1">Approvals / Audit</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Telegram requests paused by Agent-Firewall.
        </p>
      </div>
      <div class="approvals-page__actions">
        <v-select
          v-model="status"
          :items="statusItems"
          label="Status"
          density="compact"
          variant="outlined"
          hide-details
          style="width: 180px"
        />
        <v-btn
          icon="mdi-refresh"
          variant="text"
          :loading="isLoading || isFetching"
          @click="refetch"
        />
      </div>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" class="mb-4" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <v-sheet border rounded>
      <v-toolbar density="compact" color="transparent">
        <v-toolbar-title class="text-subtitle-1">
          {{ total }} intervention{{ total === 1 ? '' : 's' }}
        </v-toolbar-title>
      </v-toolbar>
      <v-divider />

      <v-table density="comfortable">
        <thead>
          <tr>
            <th class="text-left">Created</th>
            <th class="text-left">Kind</th>
            <th class="text-left">Telegram</th>
            <th class="text-left">Reason</th>
            <th class="text-left">Message</th>
            <th class="text-left">Trace</th>
            <th class="text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="7" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" />
            </td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="7" class="text-center text-medium-emphasis py-8">
              No interventions found.
            </td>
          </tr>
          <tr v-for="item in items" :key="item.id">
            <td class="text-caption text-no-wrap">{{ formatTime(item.created_at) }}</td>
            <td>
              <v-chip :color="kindColor(item.kind)" size="small" variant="tonal">
                {{ item.kind }}
              </v-chip>
              <div class="text-caption text-medium-emphasis mt-1">{{ item.status }}</div>
            </td>
            <td class="text-caption">
              <div>{{ item.account || 'telegram' }}</div>
              <div class="text-medium-emphasis">{{ item.chat_id || 'chat unknown' }}</div>
            </td>
            <td class="approval-text">{{ item.reason || 'No reason recorded' }}</td>
            <td class="approval-text">{{ item.message }}</td>
            <td>
              <code v-if="item.trace_id" class="text-caption">{{ truncate(item.trace_id, 12) }}</code>
              <span v-else class="text-medium-emphasis">-</span>
            </td>
            <td class="text-right">
              <template v-if="item.status === 'pending'">
                <v-btn
                  size="small"
                  color="success"
                  variant="tonal"
                  class="mr-2"
                  :loading="pendingId === item.id && isMutating"
                  @click="decide(item.id, 'approved')"
                >
                  Allow
                </v-btn>
                <v-btn
                  size="small"
                  color="error"
                  variant="tonal"
                  :disabled="isMutating"
                  @click="decide(item.id, 'rejected')"
                >
                  Reject
                </v-btn>
              </template>
              <v-chip v-else size="small" variant="outlined">{{ item.status }}</v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-sheet>
  </v-container>
</template>

<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { api } from '~/services/api'
import type { InterventionListResponse, InterventionStatus } from '~/types/api'

definePageMeta({ title: 'Approvals / Audit' })

const queryClient = useQueryClient()
const status = ref<InterventionStatus>('pending')
const pendingId = ref('')
const errorText = ref('')
const statusItems: InterventionStatus[] = ['pending', 'approved', 'rejected', 'completed', 'failed']

const query = useQuery<InterventionListResponse>({
  queryKey: computed(() => ['interventions', status.value]),
  queryFn: () => api.get<InterventionListResponse>('/v1/interventions', {
    params: { status: status.value, limit: 100 },
  }).then(r => r.data),
  refetchInterval: computed(() => status.value === 'pending' ? 5000 : false),
})

const mutation = useMutation({
  mutationFn: ({ id, decision }: { id: string; decision: InterventionStatus }) =>
    api.patch(`/v1/interventions/${id}`, {
      status: decision,
      decided_by: 'localhost:3000',
    }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['interventions'] })
  },
})

const items = computed(() => query.data.value?.items ?? [])
const total = computed(() => query.data.value?.total ?? 0)
const isLoading = query.isLoading
const isFetching = query.isFetching
const refetch = query.refetch
const isMutating = mutation.isPending

async function decide(id: string, decision: InterventionStatus) {
  pendingId.value = id
  errorText.value = ''
  try {
    await mutation.mutateAsync({ id, decision })
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to update intervention'
  } finally {
    pendingId.value = ''
  }
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function truncate(text: string, len: number) {
  return text.length > len ? `${text.slice(0, len)}...` : text
}

function kindColor(kind: string) {
  if (kind === 'input_block') return 'error'
  if (kind === 'tool_confirmation') return 'warning'
  return 'info'
}
</script>

<style scoped>
.approvals-page {
  max-width: 1280px;
  margin: 0 auto;
}

.approvals-page__header,
.approvals-page__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.approval-text {
  max-width: 340px;
  white-space: normal;
  word-break: break-word;
}

@media (max-width: 820px) {
  .approvals-page__header,
  .approvals-page__actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
