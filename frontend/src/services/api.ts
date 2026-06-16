const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function getToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("nexus_token");
  }
  return null;
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("nexus_token", token);
  }
}

export function removeToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("nexus_token");
  }
}

function getHeaders(isMultipart = false): HeadersInit {
  const headers: HeadersInit = {};
  if (!isMultipart) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function request(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const isMultipart = options.body instanceof FormData;
  const headers = getHeaders(isMultipart);
  
  const config = {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  };

  const response = await fetch(`${API_BASE}${endpoint}`, config);
  
  if (response.status === 204) {
    return null;
  }
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }
  
  return data;
}

export const auth = {
  login: async (credentials: any) => {
    const data = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    setToken(data.access_token);
    return data;
  },
  register: async (userData: any) => {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },
  getCurrentUser: async () => {
    // We can decode locally or verify by calling documents to see if it succeeds.
    // Let's create a quick verify endpoint or just see if getDocuments works.
    // For local checks we can also check if token exists.
    return getToken() !== null;
  }
};

export const documents = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },
  list: async () => {
    const data = await request("/documents");
    return data.documents || [];
  },
  delete: async (id: string) => {
    return request(`/documents/${id}`, {
      method: "DELETE",
    });
  }
};

export const chat = {
  listConversations: async () => {
    return request("/conversations");
  },
  createConversation: async () => {
    return request("/conversations", {
      method: "POST",
    });
  },
  getConversation: async (id: string) => {
    return request(`/conversations/${id}`);
  },
  sendQuerySync: async (message: string, conversationId?: string) => {
    return request("/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
  },
  // SSE Streaming helper
  streamChat: (
    message: string,
    conversationId: string | null,
    onStep: (stepData: any) => void,
    onFinal: (finalData: any) => void,
    onError: (err: string) => void
  ) => {
    const token = getToken();
    
    // We use standard EventSource or fetch with response reader for custom post body
    // EventSource doesn't natively support POST body and custom headers, so fetch + TextDecoder is better!
    const controller = new AbortController();
    
    fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || "Streaming error");
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) {
          throw new Error("Response body is not readable");
        }
        
        let buffer = "";

        const parseLine = (line: string) => {
          if (!line.trim()) return;
          const eventMatch = line.match(/^event:\s*(.*)$/m);
          const dataMatch = line.match(/^data:\s*(.*)$/m);
          
          if (dataMatch) {
            const eventType = eventMatch ? eventMatch[1].trim() : "message";
            try {
              const eventData = JSON.parse(dataMatch[1].trim());
              if (eventType === "step") {
                onStep(eventData);
              } else if (eventType === "final") {
                onFinal(eventData);
              } else if (eventType === "error") {
                onError(eventData);
              }
            } catch (e) {
              console.error("Failed to parse SSE event data:", e);
            }
          }
        };
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(/\r?\n\r?\n/);
          
          // Keep last incomplete line in buffer
          buffer = lines.pop() || "";
          
          for (const line of lines) {
            parseLine(line);
          }
        }

        // Process any remaining content in the buffer after stream closes
        if (buffer.trim()) {
          parseLine(buffer);
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          onError(err.message || "Failed to establish SSE stream.");
        }
      });
      
    return () => controller.abort();
  }
};

export const analytics = {
  getDashboard: async () => {
    return request("/analytics/dashboard");
  },
  getTrace: async (conversationId: string) => {
    return request(`/analytics/traces/${conversationId}`);
  }
};

export const schema = {
  getTables: async () => {
    const data = await request("/schema/tables");
    return data.tables || {};
  }
};
