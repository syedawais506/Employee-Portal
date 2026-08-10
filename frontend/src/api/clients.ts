import { apiClient } from "@/api/client";
import type { Client } from "@/types";

export interface ClientInput {
  name: string;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
}

export async function listClients(): Promise<Client[]> {
  const response = await apiClient.get<Client[]>("/clients");
  return response.data;
}

export async function createClient(payload: ClientInput): Promise<Client> {
  const response = await apiClient.post<Client>("/clients", payload);
  return response.data;
}

export async function updateClient(id: string, payload: Partial<ClientInput>): Promise<Client> {
  const response = await apiClient.patch<Client>(`/clients/${id}`, payload);
  return response.data;
}

export async function deleteClient(id: string): Promise<void> {
  await apiClient.delete(`/clients/${id}`);
}
