// src/composables/useExchangeAccounts.js
import { ref, computed } from 'vue'

const STORAGE_KEY = 'exchange_api_accounts_v1'

const accounts = ref([])

const load = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    accounts.value = raw ? JSON.parse(raw) : []
  } catch (e) {
    console.warn('[useExchangeAccounts] load failed', e)
    accounts.value = []
  }
}

const save = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(accounts.value))
  } catch (e) {
    console.warn('[useExchangeAccounts] save failed', e)
  }
}

const reload = () => load()
const defaultAccount = computed(() => accounts.value.find((a) => a.isDefault) || null)
const getById = (id) => accounts.value.find((a) => a.id === id) || null

load()

export function useExchangeAccounts() {
  return { accounts, defaultAccount, getById, reload, save }   // ★ 加 save
}