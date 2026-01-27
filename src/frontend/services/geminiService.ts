import { GoogleGenAI, Type } from "@google/genai";
import { BiologicalSpec, ComponentModel } from "../types";

// Helper to get a client instance
const getClient = (apiKey: string) => new GoogleGenAI({ apiKey });

export const generateBiologicalPlan = async (
  apiKey: string, 
  request: string
): Promise<BiologicalSpec> => {
  if (!apiKey) throw new Error("API Key required");
  
  const ai = getClient(apiKey);
  
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: `Create a biological specification for a bond graph model based on this request: "${request}". 
    Return a JSON object with intent_summary, entities (id, entity_label), and mechanisms (library_id).`,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          intent_summary: { type: Type.STRING },
          entities: {
            type: Type.ARRAY,
            items: {
              type: Type.OBJECT,
              properties: {
                id: { type: Type.STRING },
                entity_label: { type: Type.STRING }
              }
            }
          },
          mechanisms: {
            type: Type.ARRAY,
            items: {
              type: Type.OBJECT,
              properties: {
                library_id: { type: Type.STRING }
              }
            }
          }
        }
      }
    }
  });

  const text = response.text;
  if (!text) throw new Error("No response from Gemini");
  return JSON.parse(text) as BiologicalSpec;
};

export const researchParameters = async (
  apiKey: string,
  context: string
): Promise<string> => {
  if (!apiKey) throw new Error("API Key required");

  const ai = getClient(apiKey);
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: `Research parameters for the following biological model context. Provide a brief markdown report with citations if possible. Context: ${context}`
  });

  return response.text || "No research data found.";
};
