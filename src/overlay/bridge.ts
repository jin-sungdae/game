import { invoke } from '@tauri-apps/api/core';
export function action(kind: string) {
  return invoke('action', { kind }).catch(error => console.error('[LUMA] command failed', kind, error));
}
