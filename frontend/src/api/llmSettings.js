import { apiClient } from "./client";

export async function getLlmSettings() {
  const { data } = await apiClient.get("/settings/llm");
  return data;
}

export async function updateLlmSettings(update) {
  const { data } = await apiClient.put("/settings/llm", update);
  return data;
}

export async function testLlmSettings({ prompt, system_prompt }) {
  const { data } = await apiClient.post("/settings/llm/test", { prompt, system_prompt });
  return data;
}
