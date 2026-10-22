import { request } from '../api/catalog';
import { read, write, remove } from './db';
export type Command = { eventId: string; path: string; body: Record<string, unknown> };
export const commandHeaders = { 'Content-Type': 'application/json', 'X-Northstar-Request': 'local-workspace' };
export const pendingCommand = (key: string) => read<Command>('outbox', key);
export async function enqueue(key: string, path: string, payload: Record<string, unknown>) {
  const command: Command = { eventId: crypto.randomUUID(), path, body: { ...payload, clientOccurredAt: new Date().toISOString() } };
  command.body = { ...command.body, eventId: command.eventId };
  await write('outbox', key, command, true); return command;
}
export async function deliver<T>(key: string, command: Command): Promise<T> {
  const response = await request<T>(command.path, { method: 'POST', headers: commandHeaders, body: JSON.stringify(command.body) });
  await remove('outbox', key, command.eventId); return response;
}
